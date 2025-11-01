"""
LLM-Driven Scout for Brand Intelligence Collection

This module uses Tavily Search + GPT-4 for intelligent data collection.
Handles both:
- Automatic Brand Analytics campaigns (continuous monitoring)
- Custom campaigns (user-defined objectives)

Replaces web scraping with LLM-driven search and analysis.
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dateutil.relativedelta import relativedelta

from tavily import TavilyClient
from langchain_openai import ChatOpenAI
from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)


# Standard pain point keywords for zero-filling
STANDARD_PAIN_POINT_KEYWORDS = [
    'Quality Issues',
    'Sizing Problems',
    'Durability',
    'Comfort',
    'Price Value',
    'Customer Service',
    'Shipping',
    'Material Problems'
]


def _normalize_and_deduplicate_keywords(keywords: List[str]) -> Tuple[List[str], Dict[str, List[str]]]:
    """
    Use LLM to semantically deduplicate pain point keywords.
    
    Returns:
        Tuple of (deduplicated_keywords, keyword_mapping)
        - deduplicated_keywords: List of unique keywords
        - keyword_mapping: Dict mapping each deduplicated keyword to its original variants
            Example: {"Price concerns": ["price", "pricing", "Price concerns"]}
    
    This handles cases like:
    - "price", "Price concerns", "pricing" -> "Price concerns"
    - "availability in India" (duplicate) -> single entry
    - "engine performance", "Engine performance" -> "Engine performance"
    """
    if not keywords:
        return [], {}
    
    # Quick dedup for exact matches (case-insensitive)
    seen = {}
    for kw in keywords:
        normalized = kw.strip().lower()
        if normalized not in seen:
            seen[normalized] = []
        seen[normalized].append(kw)
    
    # Track original keywords for each normalized version
    original_variants = {}
    unique_keywords = []
    for normalized, variants in seen.items():
        # Pick best variant (prefer proper capitalization)
        best = max(variants, key=lambda x: (x[0].isupper() if x else False, len(x)))
        unique_keywords.append(best)
        original_variants[best] = variants
    
    # If only a few keywords, no need for LLM deduplication
    if len(unique_keywords) <= 3:
        logger.info(f"   Only {len(unique_keywords)} keywords, skipping LLM deduplication")
        # Return simple mapping
        keyword_mapping = {k: original_variants[k] for k in unique_keywords}
        return sorted(unique_keywords, key=lambda x: x.lower()), keyword_mapping
    
    logger.info(f"   Using LLM to deduplicate {len(unique_keywords)} keywords...")
    
    try:
        from langchain_openai import ChatOpenAI
        
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            max_tokens=1500
        )
        
        prompt = f"""You are a data cleaning expert. Review this list of pain point keywords and merge semantically similar ones.

CRITICAL RULES:
1. Merge exact duplicates with different capitalization (e.g., "Engine performance" + "engine performance" → "Engine performance")
2. Merge semantically similar keywords (e.g., "price", "pricing", "Pricing concerns" → "Pricing concerns")
3. Keep the most descriptive/specific version when merging
4. If two keywords are completely different concepts, keep both (e.g., "price" and "availability")
5. Preserve proper capitalization for the canonical version
6. BE AGGRESSIVE - merge anything that refers to the same concept

INPUT KEYWORDS:
{json.dumps(unique_keywords, indent=2)}

OUTPUT FORMAT - JSON ONLY (no markdown, no explanations):
{{
  "merged": [
    {{
      "canonical": "Engine performance",
      "variants": ["Engine performance", "engine performance"]
    }},
    {{
      "canonical": "Pricing concerns", 
      "variants": ["price", "pricing", "Pricing concerns"]
    }}
  ]
}}

IMPORTANT: Every keyword from the input MUST appear in at least one variants list. Return ONLY valid JSON."""
        
        response = llm.invoke(prompt)
        content = response.content.strip()
        
        logger.info(f"   LLM response length: {len(content)} chars")
        
        # Parse JSON response
        if content.startswith('```'):
            # Remove markdown code blocks
            parts = content.split('```')
            for part in parts:
                part = part.strip()
                if part.startswith('json'):
                    content = part[4:].strip()
                elif part.startswith('{'):
                    content = part
                    break
        
        content = content.strip()
        
        try:
            result = json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"   Failed to parse LLM JSON response: {e}")
            logger.error(f"   Response was: {content[:500]}")
            raise
        
        if 'merged' not in result:
            logger.error(f"   LLM response missing 'merged' key: {result}")
            raise ValueError("LLM response missing 'merged' key")
        
        deduplicated = []
        keyword_mapping = {}
        all_mapped_keywords = set()
        
        for item in result['merged']:
            canonical = str(item['canonical']).strip()
            variants = [str(v).strip() for v in item.get('variants', [canonical])]
            
            # Make sure all original variants are included
            all_variants = []
            for variant in variants:
                if variant in original_variants:
                    all_variants.extend(original_variants[variant])
                else:
                    all_variants.append(variant)
                all_mapped_keywords.add(variant.lower())
            
            deduplicated.append(canonical)
            keyword_mapping[canonical] = list(set(all_variants))  # Remove duplicates
        
        # Verify all input keywords were mapped
        input_keywords_lower = set(k.lower() for k in unique_keywords)
        if all_mapped_keywords != input_keywords_lower:
            missing = input_keywords_lower - all_mapped_keywords
            logger.warning(f"   LLM didn't map all keywords. Missing: {missing}")
            # Add missing keywords as-is
            for kw in unique_keywords:
                if kw.lower() in missing:
                    deduplicated.append(kw)
                    keyword_mapping[kw] = original_variants.get(kw, [kw])
        
        logger.info(f"   ✨ LLM deduplicated {len(unique_keywords)} → {len(deduplicated)} keywords")
        if len(unique_keywords) != len(deduplicated):
            removed = len(unique_keywords) - len(deduplicated)
            logger.info(f"   Merged {removed} similar/duplicate keywords")
            # Log merge examples
            merge_examples = []
            for canonical, variants in keyword_mapping.items():
                if len(variants) > 1:
                    merge_examples.append(f"{canonical} ← {variants}")
            if merge_examples:
                logger.info(f"   Merge examples:")
                for ex in merge_examples[:5]:  # Show first 5
                    logger.info(f"      {ex}")
        
        return sorted(deduplicated, key=lambda x: x.lower()), keyword_mapping
        
    except Exception as e:
        logger.warning(f"   LLM deduplication failed: {e}, falling back to basic dedup")
        logger.exception(e)  # Full traceback
        # Fallback: just use the case-insensitive dedup
        keyword_mapping = {k: original_variants[k] for k in unique_keywords}
        return sorted(unique_keywords, key=lambda x: x.lower()), keyword_mapping


def calculate_mention_counts_for_keywords(
    threads: List[Dict], 
    keywords: List[str],
    keyword_mapping: Dict[str, List[str]] = None
) -> Tuple[Dict[Tuple[str, str], int], Dict[Tuple[str, str, str], int]]:
    """
    Calculate mention counts for pain point keywords based on actual thread content.
    
    Args:
        threads: List of thread dicts with month_year, title, content, pain_points_mentioned, community
        keywords: List of pain point keywords to count (dynamically identified by LLM)
    
    Returns:
        Tuple of:
        - Dict mapping (month_year, keyword) -> mention_count (aggregated across all communities)
        - Dict mapping (month_year, keyword, community) -> mention_count (per community)
    """
    mention_counts = {}
    community_mention_counts = {}
    
    # If no mapping provided, create identity mapping
    if keyword_mapping is None:
        keyword_mapping = {k: [k] for k in keywords}
    
    logger.debug(f"   Analyzing {len(threads)} threads for {len(keywords)} pain point keywords...")
    
    for thread in threads:
        month_year = thread.get('month_year')
        community = thread.get('community', 'Unknown')
        thread_text = f"{thread.get('title', '')} {thread.get('content', '')}".lower()
        pain_points_mentioned = thread.get('pain_points_mentioned', [])
        
        # Count mentions for each deduplicated keyword
        for keyword in keywords:
            key = (month_year, keyword)
            community_key = (month_year, keyword, community)
            
            # Get all variants for this keyword (e.g., "Price concerns" includes "price", "pricing")
            variants = keyword_mapping.get(keyword, [keyword])
            
            # Check if ANY variant is mentioned in the thread
            is_mentioned = False
            
            for variant in variants:
                variant_lower = variant.lower()
                
                # Check multiple ways a keyword might be mentioned
                if (
                    variant in pain_points_mentioned or  # Explicitly tagged by LLM
                    variant_lower in pain_points_mentioned or
                    variant_lower in thread_text or  # Appears in text
                    # Check for partial word matches (e.g., "quality" matches "Quality Issues")
                    any(word.lower() in thread_text for word in variant.split() if len(word) > 3)
                ):
                    is_mentioned = True
                    break
            
            if is_mentioned:
                mention_counts[key] = mention_counts.get(key, 0) + 1
                community_mention_counts[community_key] = community_mention_counts.get(community_key, 0) + 1
    
    logger.debug(f"   Counted mentions for {len(set(k[1] for k in mention_counts.keys()))} keywords across months")
    logger.debug(f"   Found {len(community_mention_counts)} keyword-community combinations")
    
    return mention_counts, community_mention_counts


def get_past_complete_months(num_months: int = 6) -> List[Dict[str, str]]:
    """
    Get list of past N complete months (excluding current month).

    Returns:
        List of dicts with month_year, month_label, date_from, date_to
    """
    now = timezone.now()
    months = []

    for offset in range(1, num_months + 1):  # Start from 1 to skip current month
        target_date = now - relativedelta(months=offset)

        # First day of the month
        first_day = target_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # Last day of the month
        if target_date.month == 12:
            last_day = target_date.replace(day=31, hour=23, minute=59, second=59)
        else:
            next_month = target_date.replace(day=28) + timedelta(days=4)
            last_day = (next_month - timedelta(days=next_month.day)).replace(
                hour=23, minute=59, second=59
            )

        months.append({
            'month_year': target_date.strftime('%Y-%m'),
            'month_label': target_date.strftime('%b %Y'),
            'date_from': first_day.strftime('%Y-%m-%d'),
            'date_to': last_day.strftime('%Y-%m-%d'),
            'timestamp_from': first_day,
            'timestamp_to': last_day
        })

    return months


async def search_month_with_tavily_and_llm(
    brand_name: str,
    brand_context: str,
    brand_website: str,
    month_info: Dict[str, str],
    keywords: List[str],
    industry: str = "general",
    campaign_objectives: str = None,
    max_results: int = 10
) -> Dict[str, Any]:
    """
    Search for brand discussions for a specific month using Tavily + LLM.

    Args:
        brand_name: Brand name only (e.g., "Nike")
        brand_context: Brand with description (e.g., "Nike Sport Shoes")
        brand_website: Official website for filtering
        month_info: Dict with month_year, date_from, date_to
        keywords: Campaign-specific keywords
        industry: Industry context
        campaign_objectives: Custom campaign objectives (for custom campaigns)
        max_results: Max search results to analyze

    Returns:
        Dict with threads, pain_points, communities for the month
    """
    tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

    logger.info(f"🔍 Searching for {brand_context} in {month_info['month_label']}...")

    # Construct search queries based on campaign type
    if campaign_objectives:
        # Custom campaign - use objectives to guide search
        search_queries = [
            f'"{brand_context}" {campaign_objectives[:50]} site:reddit.com {month_info["month_label"]}',
            f'"{brand_context}" ' + ' '.join(keywords[:3]) + f' {month_info["month_label"]}'
        ]
    else:
        # Automatic brand monitoring - use brand context for specificity
        search_queries = [
            f'"{brand_context}" review problems site:reddit.com {month_info["month_label"]}',
            f'"{brand_context}" quality complaints {industry} {month_info["month_label"]}'
        ]
    
    # Add website-specific search if available
    if brand_website:
        domain = brand_website.replace('https://', '').replace('http://', '').split('/')[0]
        search_queries.append(f'"{brand_name}" site:{domain} OR site:reddit.com {month_info["month_label"]}')

    # Add keyword-specific searches
    if keywords:
        for keyword in keywords[:2]:
            search_queries.append(f'"{brand_name}" {keyword} {month_info["month_label"]}')

    # Collect search results
    all_search_results = []

    for query in search_queries[:3]:  # Limit to 3 queries per month
        try:
            response = tavily_client.search(
                query=query,
                search_depth="basic",  # Changed from "advanced" to reduce tokens
                max_results=max_results // 3,
                include_raw_content=False  # Changed to False - don't need full HTML
            )

            # Truncate content to reduce token usage
            results = response.get('results', [])
            for result in results:
                # Truncate content to 500 chars max
                if 'content' in result:
                    result['content'] = result['content'][:500]

            all_search_results.extend(results)
            logger.info(f"   Found {len(results)} results")

        except Exception as e:
            logger.error(f"   Tavily search failed: {e}")
            continue

    if not all_search_results:
        logger.warning(f"⚠️  No results found for {month_info['month_label']}")
        return {
            'month_year': month_info['month_year'],
            'month_label': month_info['month_label'],
            'threads': [],
            'pain_points_found': [],
            'communities': [],
            'search_success': False
        }

    logger.info(f"   Total results: {len(all_search_results)}")

    # ✅ Create multiple mappings from search results (Tavily already provides URLs)
    url_by_title = {}
    url_by_content = {}
    all_result_urls = []
    
    for result in all_search_results:
        if 'url' in result:
            url = result['url']
            all_result_urls.append(url)
            
            # Map by title
            if 'title' in result:
                url_by_title[result['title'].lower()] = url
            
            # Map by content keywords (first 100 chars)
            if 'content' in result:
                content_snippet = result['content'][:100].lower()
                url_by_content[content_snippet] = url
    
    logger.info(f"   Mapped {len(all_result_urls)} URLs from search results")

    # Use LLM to analyze results
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)

    objectives_context = f"\nCampaign Objectives: {campaign_objectives}" if campaign_objectives else ""
    brand_details = f"""
Brand: {brand_name}
Product/Service: {brand_context}
Industry: {industry}
Website: {brand_website if brand_website else 'Not specified'}
"""

    analysis_prompt = f"""Analyze these search results about "{brand_context}" from {month_info['month_label']}.

BRAND CONTEXT:
{brand_details}{objectives_context}

SEARCH RESULTS:
{json.dumps(all_search_results[:8], indent=2)}

Extract structured brand intelligence. Focus on discussions specifically about "{brand_context}" in the {industry} industry.
Filter out any irrelevant results about different products/companies with similar names.

Return JSON:

{{
  "threads": [
    {{
      "thread_id": "unique_id_from_url",
      "title": "actual title",
      "content": "content excerpt",
      "author": "author or unknown",
      "community": "r/subreddit or forum name from URL",
      "platform": "reddit/forum/review_site",
      "url": "actual URL",
      "published_date": "YYYY-MM-DD in {month_info['month_label']}",
      "upvotes": estimated_number,
      "comment_count": estimated_number,
      "sentiment_score": float_-1_to_1,
      "pain_points_mentioned": ["list"]
    }}
  ],

  "pain_points_found": [
    {{
      "keyword": "pain point name",
      "mention_count": count,
      "sentiment_score": float,
      "example": "short quote showing this pain point",
      "severity": "high/medium/low"
    }}
  ],

  "communities_discovered": [
    {{
      "name": "r/subreddit",
      "platform": "reddit/forum",
      "thread_count": count,
      "member_count": 100000,
      "key_influencer": "username_of_most_active_author",
      "influencer_post_count": 5,
      "influencer_engagement": 1200
    }}
  ]
}}

Rules:
- Only include REAL data from search results
- Extract actual URLs, titles, content
- Identify pain points intelligently (no keyword matching)
- Estimate dates within {month_info['month_label']}
- Extract community names from URLs
- For each community, identify the KEY INFLUENCER:
  * Find the author who appears most frequently in threads/comments
  * OR the author with highest total engagement (upvotes + replies)
  * Return username as "key_influencer"
  * Count posts: "influencer_post_count"
  * Sum engagement: "influencer_engagement"

Output valid JSON only:"""

    try:
        response = await llm.ainvoke(analysis_prompt)
        response_text = response.content.strip()

        # Clean markdown
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
            response_text = response_text.strip()

        month_data = json.loads(response_text)
        month_data['month_year'] = month_info['month_year']
        month_data['month_label'] = month_info['month_label']
        month_data['search_success'] = True

        # ✅ Enrich threads with actual URLs from Tavily search results
        threads = month_data.get('threads', [])
        url_match_count = 0
        
        for i, thread in enumerate(threads):
            thread_title = thread.get('title', '').lower()
            thread_content = thread.get('content', '')[:100].lower()
            
            # Strategy 1: Exact title match
            if thread_title in url_by_title:
                thread['url'] = url_by_title[thread_title]
                url_match_count += 1
                continue
            
            # Strategy 2: Fuzzy title matching (50% word overlap)
            if not thread.get('url') and len(thread_title) > 10:
                best_match_score = 0
                best_match_url = None
                thread_words = set(thread_title.split())
                
                for result_title, result_url in url_by_title.items():
                    result_words = set(result_title.split())
                    if thread_words and result_words:
                        overlap = len(thread_words & result_words) / len(thread_words)
                        if overlap > best_match_score and overlap >= 0.4:  # Lower threshold to 40%
                            best_match_score = overlap
                            best_match_url = result_url
                
                if best_match_url:
                    thread['url'] = best_match_url
                    url_match_count += 1
                    continue
            
            # Strategy 3: If still no match, use URLs in sequence (fallback)
            if not thread.get('url') and i < len(all_result_urls):
                thread['url'] = all_result_urls[i]
                url_match_count += 1
        
        logger.info(f"   Enriched {url_match_count}/{len(threads)} threads with URLs from search results")

        logger.info(f"✅ Extracted: {len(month_data.get('threads', []))} threads, "
                   f"{len(month_data.get('pain_points_found', []))} pain points")

        return month_data

    except Exception as e:
        logger.error(f"❌ LLM analysis failed: {e}")
        return {
            'month_year': month_info['month_year'],
            'month_label': month_info['month_label'],
            'threads': [],
            'pain_points_found': [],
            'communities': [],
            'search_success': False,
            'error': str(e)
        }


async def collect_real_brand_data(
    brand_name: str,
    keywords: List[str],
    config: dict = None
) -> Dict[str, Any]:
    """
    Main entry point for scout data collection.

    Handles both campaign types:
    - Automatic Brand Analytics (config['focus'] == 'brand_monitoring')
    - Custom Campaigns (config['focus'] == 'custom_campaign')

    Uses LLM-driven Tavily search to collect 6 months of data.

    Args:
        brand_name: Brand name
        keywords: Campaign keywords
        config: Configuration dict with:
            - focus: brand_monitoring or custom_campaign
            - brand_description: Product/service description (e.g., "Sport Shoes")
            - brand_website: Official website
            - industry: Industry category (e.g., "Sportwear")
            - campaign_objectives: Custom campaign goals

    Returns:
        Dict with threads, pain_points, communities
    """
    logger.info(f"🤖 LLM-driven scout starting for: {brand_name}")

    # Extract config
    config = config or {}
    focus = config.get('focus', 'brand_monitoring')
    campaign_objectives = config.get('campaign_objectives')
    brand_description = config.get('brand_description', '')
    brand_website = config.get('brand_website', '')
    industry = config.get('industry', 'general')
    num_months = config.get('collection_months', 6)

    # Build brand context for more accurate searches
    brand_context = brand_name
    if brand_description:
        brand_context = f"{brand_name} {brand_description}"
    
    logger.info(f"   Focus: {focus}")
    logger.info(f"   Brand Context: {brand_context}")
    logger.info(f"   Industry: {industry}")
    logger.info(f"   Website: {brand_website}")
    logger.info(f"   Keywords: {keywords}")
    if campaign_objectives:
        logger.info(f"   Objectives: {campaign_objectives[:100]}")

    # Get past complete months
    months = get_past_complete_months(num_months)
    logger.info(f"📅 Collecting data for: {[m['month_label'] for m in months]}")

    # Collect data for each month
    monthly_results = []

    for month_info in months:
        month_data = await search_month_with_tavily_and_llm(
            brand_name=brand_name,
            brand_context=brand_context,
            brand_website=brand_website,
            month_info=month_info,
            keywords=keywords,
            industry=industry,
            campaign_objectives=campaign_objectives,
            max_results=30  # Increased from 10 to 30 (10 results per query × 3 queries)
        )
        monthly_results.append(month_data)

    # Aggregate all data
    all_threads = []
    all_pain_points = []
    all_communities = {}

    for month_data in monthly_results:
        # Add month_year to threads
        for thread in month_data.get('threads', []):
            thread['month_year'] = month_data['month_year']
            all_threads.append(thread)

        # Add month_year to pain points
        for pp in month_data.get('pain_points_found', []):
            pp['month_year'] = month_data['month_year']
            all_pain_points.append(pp)

        # Aggregate communities
        for comm in month_data.get('communities_discovered', []):
            comm_key = comm['name']
            if comm_key not in all_communities:
                all_communities[comm_key] = comm
            else:
                all_communities[comm_key]['thread_count'] = all_communities[comm_key].get('thread_count', 0) + comm.get('thread_count', 0)

    # Extract unique pain point keywords identified by LLM across all months
    # Apply normalization and deduplication to merge similar keywords
    raw_keywords = set()
    for pp in all_pain_points:
        if pp.get('keyword'):
            raw_keywords.add(pp['keyword'])
    
    logger.info(f"🔍 LLM identified {len(raw_keywords)} raw pain point keywords")
    
    # Normalize and deduplicate keywords (case-insensitive, merge similar phrases)
    # Returns: (deduplicated_keywords, keyword_mapping)
    # keyword_mapping maps each deduplicated keyword to ALL its original variants
    identified_keywords, keyword_mapping = _normalize_and_deduplicate_keywords(list(raw_keywords))
    
    logger.info(f"✨ After normalization: {len(identified_keywords)} unique pain point keywords: {list(identified_keywords)[:5]}...")
    
    # Calculate mention counts from threads for the identified keywords
    # Pass keyword_mapping so it can search for all variants when counting
    logger.info(f"🔢 Calculating mention counts from {len(all_threads)} threads...")
    pain_point_mention_counts, community_mention_counts = calculate_mention_counts_for_keywords(
        all_threads, 
        list(identified_keywords),
        keyword_mapping
    )
    logger.info(f"   Found {len(pain_point_mention_counts)} pain point-month combinations with mentions")
    logger.info(f"   Found {len(community_mention_counts)} pain point-community combinations")
    
    # Create complete pain point records (one per keyword per month per community) with calculated mentions
    complete_pain_points = []
    
    # Use a set to track what we've already created (prevent duplicates)
    created_pain_points = set()
    
    # Get unique communities from threads
    thread_communities = set(t.get('community', 'Unknown') for t in all_threads)
    logger.info(f"   Creating pain points for {len(identified_keywords)} keywords × {len(months)} months × {len(thread_communities)} communities...")
    
    for month_info in months:
        month_year = month_info['month_year']
        for keyword in identified_keywords:
            # Create one pain point per community that mentioned this keyword
            for community in thread_communities:
                community_key = (month_year, keyword, community)
                
                # Skip if we've already created this exact pain point
                if community_key in created_pain_points:
                    continue
                
                mention_count = community_mention_counts.get(community_key, 0)
                
                # Only create pain point if this community mentioned this keyword (skip zero mentions)
                if mention_count > 0:
                    # Try to find existing pain point data from LLM for this keyword/month
                    # Check both the canonical keyword and any of its variants
                    variants = keyword_mapping.get(keyword, [keyword])
                    existing_pp = None
                    for variant in variants:
                        existing_pp = next((pp for pp in all_pain_points 
                                          if pp.get('keyword', '').lower() == variant.lower() 
                                          and pp.get('month_year') == month_year), None)
                        if existing_pp:
                            break
                    
                    if existing_pp:
                        # Use LLM data but override mention_count with community-specific value
                        pp_copy = existing_pp.copy()
                        pp_copy['keyword'] = keyword  # Use canonical keyword
                        pp_copy['mention_count'] = mention_count
                        pp_copy['community'] = community
                        complete_pain_points.append(pp_copy)
                    else:
                        # Create zero-filled record for missing month
                        complete_pain_points.append({
                            'keyword': keyword,
                            'month_year': month_year,
                            'mention_count': mention_count,
                            'community': community,
                            'sentiment_score': 0.0,
                            'example_quotes': [],
                            'severity': 'none',
                            'heat_level': 0,
                            'growth_percentage': 0.0
                        })
                    
                    # Mark this combination as created
                    created_pain_points.add(community_key)
    
    logger.info(f"✅ Created {len(complete_pain_points)} complete pain point records (with community associations)")
    logger.info(f"   Total mentions counted: {sum(community_mention_counts.values())}")
    
    # Debug: Check for duplicates in complete_pain_points
    seen_combinations = {}
    duplicate_count = 0
    for idx, pp in enumerate(complete_pain_points):
        key = (pp['month_year'], pp['keyword'], pp.get('community', 'Unknown'))
        if key in seen_combinations:
            duplicate_count += 1
            logger.warning(f"   ⚠️  DUPLICATE #{duplicate_count} at index {idx}: {pp['keyword']} in '{pp.get('community')}' for {pp['month_year']}")
            logger.warning(f"      First occurrence (index {seen_combinations[key]['idx']}): mentions={seen_combinations[key]['mentions']}")
            logger.warning(f"      This occurrence: mentions={pp.get('mention_count', 0)}")
        else:
            seen_combinations[key] = {'idx': idx, 'mentions': pp.get('mention_count', 0)}
    
    if duplicate_count > 0:
        logger.error(f"   ❌ Found {duplicate_count} DUPLICATES in complete_pain_points list!")
    else:
        logger.info(f"   ✅ No duplicates found in complete_pain_points list")

    result = {
        'brand_name': brand_name,
        'communities': list(all_communities.values()),
        'threads': all_threads,
        'pain_points': complete_pain_points,
        'raw_content': [],  # For compatibility
        'brand_mentions': [],
        'discussions': [],
        'data_sources': ['tavily_llm'],
        'collection_timestamp': timezone.now().isoformat(),
        'is_real_data': True,
        'config_used': config,
        'keywords_used': keywords,
        'search_parameters': {
            'search_depth': 'llm_driven',
            'focus': focus,
            'num_months': num_months
        }
    }

    logger.info(f"✅ Collection complete:")
    logger.info(f"   Threads: {len(all_threads)}")
    logger.info(f"   Pain points: {len(complete_pain_points)}")
    logger.info(f"   Communities: {len(all_communities)}")

    # Debug: Log sample pain points to verify month_year format
    if complete_pain_points:
        logger.info(f"📊 Sample pain points (first 3):")
        for pp in complete_pain_points[:3]:
            logger.info(f"   - {pp.get('keyword')}: month_year={pp.get('month_year')}, mentions={pp.get('mention_count')}")

    return result


def ensure_complete_pain_point_coverage(
    pain_points: List[Dict],
    months: List[Dict],
    standard_keywords: List[str]
) -> List[Dict]:
    """
    Ensure every keyword has a record for every month (zero-filling).

    Guarantees dashboard shows all 6 months.
    """
    logger.info("🔧 Zero-filling pain points for complete coverage...")

    # Group existing by (month, keyword)
    existing = {}
    for pp in pain_points:
        key = (pp['month_year'], pp['keyword'])
        existing[key] = pp

    # Create complete set
    complete_pain_points = []

    for month_info in months:
        month_year = month_info['month_year']

        for keyword in standard_keywords:
            key = (month_year, keyword)

            if key in existing:
                complete_pain_points.append(existing[key])
            else:
                # Zero record
                complete_pain_points.append({
                    'keyword': keyword,
                    'month_year': month_year,
                    'mention_count': 0,
                    'sentiment_score': 0.0,
                    'example_quotes': [],
                    'severity': 'none',
                    'heat_level': 0,
                    'growth_percentage': 0.0
                })

    logger.info(f"   Total records: {len(complete_pain_points)}")
    logger.info(f"   Zero-filled: {len(complete_pain_points) - len(pain_points)}")

    return complete_pain_points


# Legacy compatibility functions (kept for nodes.py)
def calculate_month_year(published_at: datetime) -> Optional[str]:
    """Calculate month_year for a thread. Returns None if current month."""
    now = timezone.now()
    if published_at.year == now.year and published_at.month == now.month:
        return None
    return published_at.strftime('%Y-%m')
