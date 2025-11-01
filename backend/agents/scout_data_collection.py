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


def _normalize_and_deduplicate_keywords(keywords: List[str]) -> List[str]:
    """
    Normalize and deduplicate pain point keywords to avoid variations like:
    - "price", "Price concerns", "price concerns" -> "price concerns"
    - "availability", "availability in India" -> keep both (different specificity)
    
    Strategy:
    1. Convert to lowercase for comparison
    2. Group keywords that are substrings of each other
    3. Keep the most descriptive version (longest)
    4. Handle exact case-insensitive duplicates
    """
    if not keywords:
        return []
    
    # Create mapping of normalized -> original keywords
    keyword_map = {}
    for kw in keywords:
        normalized = kw.strip().lower()
        if normalized not in keyword_map:
            keyword_map[normalized] = []
        keyword_map[normalized].append(kw)
    
    # Deduplicated result
    deduplicated = []
    processed = set()
    
    # Sort by length (longest first) to prefer more descriptive versions
    sorted_keywords = sorted(keyword_map.keys(), key=len, reverse=True)
    
    for norm_keyword in sorted_keywords:
        if norm_keyword in processed:
            continue
            
        # Check if this keyword is a substring of any already processed keyword
        is_substring = False
        for processed_kw in processed:
            if norm_keyword in processed_kw or processed_kw in norm_keyword:
                # If current is more specific (longer), replace
                if len(norm_keyword) > len(processed_kw):
                    deduplicated.remove(next(k for k in deduplicated if k.lower() == processed_kw))
                    processed.remove(processed_kw)
                    break
                else:
                    is_substring = True
                    break
        
        if not is_substring:
            # Pick the original keyword with best capitalization (prefer Title Case over lowercase)
            original_variants = keyword_map[norm_keyword]
            # Prefer keywords with proper capitalization
            best_variant = max(original_variants, key=lambda x: (x[0].isupper() if x else False, len(x)))
            deduplicated.append(best_variant)
            processed.add(norm_keyword)
    
    logger.debug(f"   Deduplicated {len(keywords)} keywords to {len(deduplicated)}")
    return sorted(deduplicated)


def calculate_mention_counts_for_keywords(threads: List[Dict], keywords: List[str]) -> Tuple[Dict[Tuple[str, str], int], Dict[Tuple[str, str, str], int]]:
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
    
    logger.debug(f"   Analyzing {len(threads)} threads for {len(keywords)} pain point keywords...")
    
    for thread in threads:
        month_year = thread.get('month_year')
        community = thread.get('community', 'Unknown')
        thread_text = f"{thread.get('title', '')} {thread.get('content', '')}".lower()
        pain_points_mentioned = thread.get('pain_points_mentioned', [])
        
        # Count mentions for each keyword
        for keyword in keywords:
            key = (month_year, keyword)
            community_key = (month_year, keyword, community)
            keyword_lower = keyword.lower()
            
            # Check if this keyword was explicitly mentioned in the thread's pain_points_mentioned field
            # OR check if keyword appears in the thread text (flexible matching)
            is_mentioned = (
                keyword in pain_points_mentioned or
                keyword_lower in thread_text or
                # Check for partial word matches (e.g., "quality" matches "Quality Issues")
                any(word.lower() in thread_text for word in keyword.split() if len(word) > 3)
            )
            
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
            max_results=10
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
    identified_keywords = _normalize_and_deduplicate_keywords(list(raw_keywords))
    
    logger.info(f"✨ After normalization: {len(identified_keywords)} unique pain point keywords: {list(identified_keywords)[:5]}...")
    
    # Calculate mention counts from threads for the identified keywords
    logger.info(f"🔢 Calculating mention counts from {len(all_threads)} threads...")
    pain_point_mention_counts, community_mention_counts = calculate_mention_counts_for_keywords(all_threads, list(identified_keywords))
    logger.info(f"   Found {len(pain_point_mention_counts)} pain point-month combinations with mentions")
    logger.info(f"   Found {len(community_mention_counts)} pain point-community combinations")
    
    # Create complete pain point records (one per keyword per month per community) with calculated mentions
    complete_pain_points = []
    
    # Get unique communities from threads
    thread_communities = set(t.get('community', 'Unknown') for t in all_threads)
    logger.info(f"   Creating pain points for {len(identified_keywords)} keywords × {len(months)} months × {len(thread_communities)} communities...")
    
    for month_info in months:
        month_year = month_info['month_year']
        for keyword in identified_keywords:
            # Create one pain point per community that mentioned this keyword
            for community in thread_communities:
                community_key = (month_year, keyword, community)
                mention_count = community_mention_counts.get(community_key, 0)
                
                # Only create pain point if this community mentioned this keyword (skip zero mentions)
                if mention_count > 0:
                    # Try to find existing pain point data from LLM for this keyword/month
                    existing_pp = next((pp for pp in all_pain_points 
                                      if pp.get('keyword') == keyword and pp.get('month_year') == month_year), None)
                    
                    if existing_pp:
                        # Use LLM data but override mention_count with community-specific value
                        pp_copy = existing_pp.copy()
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
    
    logger.info(f"✅ Created {len(complete_pain_points)} complete pain point records (with community associations)")
    logger.info(f"   Total mentions counted: {sum(community_mention_counts.values())}")

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
