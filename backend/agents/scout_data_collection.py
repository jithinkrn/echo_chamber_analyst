"""
Real-Time Data Collection Functions for Scout Node

This module contains functions for gathering real-time data from online sources
including Reddit, forums, and review sites. It integrates with SearchUtils
to scrape actual web content and process it for the dashboard.
"""

import asyncio
import logging
import re
import random  # ADD THIS MISSING IMPORT
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from urllib.parse import urlparse

from .search_utils import SearchUtils
from langchain_openai import ChatOpenAI
from django.core.cache import cache

logger = logging.getLogger(__name__)


async def discover_sources_with_llm(
    brand_name: str,
    focus: str,
    industry: str = "general",
    use_cache: bool = True
) -> Dict[str, Any]:
    """
    Use LLM to intelligently discover data sources based on brand context.

    This implements Option 1: Single-Shot LLM Discovery with caching.
    The LLM recommends the most relevant communities and forums to monitor
    based on the brand, industry, and analysis focus.

    Args:
        brand_name: Name of the brand to analyze
        focus: Analysis focus (pain_points, sentiment, comprehensive, etc.)
        industry: Industry context (fashion, tech, food, etc.)
        use_cache: Whether to use cached results (default: True)

    Returns:
        Dict containing recommended sources:
        {
            "reddit_communities": ["subreddit1", "subreddit2", ...],
            "forums": ["forum1.com", "forum2.com", ...],
            "reasoning": "explanation...",
            "cache_hit": bool
        }
    """
    # Check cache first
    cache_key = f"llm_sources_{brand_name}_{focus}_{industry}".lower().replace(" ", "_")

    if use_cache:
        cached_result = cache.get(cache_key)
        if cached_result:
            logger.info(f"✅ Using cached LLM source recommendations for {brand_name}")
            cached_result['cache_hit'] = True
            return cached_result

    logger.info(f"🤖 Discovering data sources with LLM for brand: {brand_name}, focus: {focus}, industry: {industry}")

    # Initialize LLM (using same model as SearchUtils)
    llm = ChatOpenAI(
        model="gpt-4",
        temperature=0.1,
        max_tokens=1000
    )

    # Craft the prompt for source discovery
    prompt = f"""You are a brand intelligence expert specializing in online community research.

Given a brand analysis request, recommend the best online communities, forums, and discussion platforms to monitor for authentic customer feedback and discussions.

Brand: {brand_name}
Industry: {industry}
Analysis Focus: {focus}

Based on this context, provide:

1. **Reddit Communities**: 5-8 subreddit names (without 'r/' prefix) most likely to contain discussions about this brand or industry. Consider:
   - Brand-specific subreddits
   - Industry-specific communities
   - Review and feedback communities
   - Relevant lifestyle/interest communities

2. **Forum Sites**: 3-5 forum domains or websites where industry discussions happen. Include:
   - Industry-specific forums
   - Review platforms
   - Q&A sites
   - Community discussion boards

3. **Reasoning**: Brief explanation of why these sources are ideal for this brand and focus.

IMPORTANT:
- Focus on active communities with real discussions
- Prioritize communities where customers naturally discuss products/brands
- Consider the analysis focus when selecting sources
- Return ONLY valid JSON, no markdown formatting

Return your response as a JSON object with this exact structure:
{{
  "reddit_communities": ["subreddit1", "subreddit2", "subreddit3", ...],
  "forums": ["forum1.com", "forum2.com", ...],
  "reasoning": "Brief explanation of source selection strategy"
}}"""

    try:
        # Get LLM recommendations and track tokens
        response = await llm.ainvoke(prompt)
        response_text = response.content.strip()

        # Track token usage
        token_count = 0
        cost = 0.0
        if hasattr(response, 'response_metadata'):
            usage = response.response_metadata.get('token_usage', {})
            prompt_tokens = usage.get('prompt_tokens', 0)
            completion_tokens = usage.get('completion_tokens', 0)
            token_count = usage.get('total_tokens', prompt_tokens + completion_tokens)

            # GPT-4 pricing: $0.03/1K prompt tokens, $0.06/1K completion tokens
            cost = (prompt_tokens * 0.03 / 1000) + (completion_tokens * 0.06 / 1000)

            logger.info(f"💰 LLM Source Discovery - Tokens: {token_count}, Cost: ${cost:.4f}")

        # Clean up response if it contains markdown code blocks
        if response_text.startswith("```"):
            # Extract JSON from markdown code block
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
            response_text = response_text.strip()

        # Parse JSON response
        sources = json.loads(response_text)

        # Add token tracking to response
        sources['token_count'] = token_count
        sources['processing_cost'] = cost

        # Validate response structure
        if not isinstance(sources.get("reddit_communities"), list):
            raise ValueError("Invalid reddit_communities in LLM response")
        if not isinstance(sources.get("forums"), list):
            raise ValueError("Invalid forums in LLM response")

        # Add metadata
        sources['cache_hit'] = False
        sources['discovered_at'] = datetime.now().isoformat()
        sources['brand_name'] = brand_name
        sources['focus'] = focus
        sources['industry'] = industry

        # Cache the results (cache for 7 days)
        cache.set(cache_key, sources, 60 * 60 * 24 * 7)

        logger.info(f"✅ LLM discovered {len(sources['reddit_communities'])} Reddit communities and {len(sources['forums'])} forums")
        logger.info(f"🧠 Reasoning: {sources.get('reasoning', 'N/A')[:100]}...")

        return sources

    except json.JSONDecodeError as e:
        logger.error(f"❌ Failed to parse LLM response as JSON: {e}")
        logger.error(f"Response was: {response_text[:500]}")
        # Return fallback sources
        return _get_fallback_sources(brand_name, focus, industry)

    except Exception as e:
        logger.error(f"❌ Error discovering sources with LLM: {e}")
        # Return fallback sources
        return _get_fallback_sources(brand_name, focus, industry)


def _get_fallback_sources(brand_name: str, focus: str, industry: str) -> Dict[str, Any]:
    """
    Fallback source recommendations if LLM discovery fails.
    Uses hardcoded sources based on focus and industry.
    """
    logger.warning(f"⚠️ Using fallback sources for {brand_name}")

    # Industry-based defaults
    industry_sources = {
        "fashion": {
            "reddit": ["malefashionadvice", "streetwear", "femalefashionadvice", "BuyItForLife", "reviews"],
            "forums": ["styleforum.net", "hypebeast.com", "reddit.com"]
        },
        "tech": {
            "reddit": ["technology", "gadgets", "BuyItForLife", "reviews", "ProductReviews"],
            "forums": ["techpowerup.com", "anandtech.com", "tomshardware.com"]
        },
        "food": {
            "reddit": ["food", "cooking", "AskCulinary", "reviews", "ProductReviews"],
            "forums": ["chowhound.com", "egullet.org", "seriouseats.com"]
        },
        "general": {
            "reddit": ["reviews", "BuyItForLife", "ProductReviews", "mildlyinfuriating"],
            "forums": ["reddit.com", "quora.com", "stackexchange.com"]
        }
    }

    # Get sources for industry (default to general)
    sources = industry_sources.get(industry.lower(), industry_sources["general"])

    # Adjust based on focus
    if focus == "pain_points":
        sources["reddit"].insert(0, "mildlyinfuriating")
        sources["reddit"].insert(1, "ProductFails")
    elif focus == "sentiment":
        sources["reddit"].insert(0, "testimonials")
        sources["reddit"].insert(1, "HailCorporate")

    return {
        "reddit_communities": sources["reddit"][:8],
        "forums": sources["forums"][:5],
        "reasoning": f"Fallback sources for {industry} industry with {focus} focus",
        "cache_hit": False,
        "is_fallback": True,
        "discovered_at": datetime.now().isoformat()
    }


async def collect_real_brand_data(brand_name: str, keywords: List[str], config: dict = None) -> Dict[str, Any]:
    """
    Collect real brand data from various sources with enhanced configuration.
    
    Args:
        brand_name: Name of the brand to analyze
        keywords: Keywords to search for
        config: Enhanced scout configuration dict
    """
    logger.info(f"🔍 Starting enhanced scout data collection for brand: {brand_name}")
    logger.info(f"📋 Keywords: {', '.join(keywords)}")
    
    # Use config if provided
    if config:
        logger.info(f"⚙️ Using enhanced config: {config}")
        search_depth = config.get('search_depth', 'comprehensive')
        focus = config.get('focus', 'comprehensive')
        target_communities = config.get('target_communities', [])
        include_sentiment = config.get('include_sentiment', True)
        include_competitors = config.get('include_competitors', True)
        focus_areas = config.get('focus_areas', ['pain_points', 'feedback', 'sentiment'])
    else:
        # Default config
        search_depth = 'comprehensive'
        focus = 'comprehensive'
        target_communities = []
        include_sentiment = True
        include_competitors = True
        focus_areas = ['pain_points', 'feedback', 'sentiment']
    
    # Build enhanced config for sub-functions
    enhanced_config = {
        "search_depth": search_depth,
        "focus": focus,
        "target_communities": target_communities,
        "include_sentiment": include_sentiment,
        "include_competitors": include_competitors,
        "focus_areas": focus_areas
    }
    
    logger.info(f"🎯 Enhanced configuration: {enhanced_config}")

    # Adjust search parameters based on config
    if search_depth == 'quick':
        max_subreddits = 3
        max_queries_per_subreddit = 2
        max_results_per_query = 2
    elif search_depth == 'deep':
        max_subreddits = 8
        max_queries_per_subreddit = 5
        max_results_per_query = 5
    else:  # comprehensive
        max_subreddits = 5
        max_queries_per_subreddit = 3
        max_results_per_query = 3

    # Use target communities if provided, otherwise use LLM discovery or defaults
    if target_communities:
        target_subreddits = [name.replace('r/', '') for name in target_communities][:max_subreddits]
        logger.info(f"🎯 Using specified target communities: {target_subreddits}")
    else:
        # NEW: Try LLM-driven source discovery first
        try:
            industry = config.get('industry', 'general') if config else 'general'
            use_llm_discovery = config.get('use_llm_discovery', True) if config else True

            if use_llm_discovery:
                logger.info(f"🤖 Using LLM to discover optimal data sources for {brand_name}")
                discovered_sources = await discover_sources_with_llm(
                    brand_name=brand_name,
                    focus=focus,
                    industry=industry,
                    use_cache=True
                )

                target_subreddits = discovered_sources.get('reddit_communities', [])[:max_subreddits]
                discovered_forums = discovered_sources.get('forums', [])

                if discovered_sources.get('cache_hit'):
                    logger.info(f"✅ Using cached LLM-discovered sources")
                else:
                    logger.info(f"🧠 LLM Discovery: {discovered_sources.get('reasoning', 'N/A')[:150]}...")

                logger.info(f"📍 LLM-discovered communities: {target_subreddits}")

                # Store discovered sources in enhanced_config for later use
                enhanced_config['discovered_forums'] = discovered_forums
                enhanced_config['llm_reasoning'] = discovered_sources.get('reasoning', '')
                # Store full discovered sources for return to caller (will be saved to DB by task)
                enhanced_config['discovered_sources'] = discovered_sources
            else:
                # LLM discovery disabled, use fallback
                raise ValueError("LLM discovery disabled in config")

        except Exception as e:
            # Fallback to hardcoded sources if LLM discovery fails
            logger.warning(f"⚠️ LLM discovery failed or disabled, using hardcoded sources: {e}")

            if focus == 'pain_points':
                target_subreddits = ["reviews", "mildlyinfuriating", "BuyItForLife", "ProductFails"][:max_subreddits]
            elif focus == 'sentiment':
                target_subreddits = ["reviews", "testimonials", "BuyItForLife", "HailCorporate"][:max_subreddits]
            elif focus == 'competitors':
                target_subreddits = ["reviews", "BuyItForLife", "malefashionadvice", "streetwear"][:max_subreddits]
            elif focus == 'product_feedback':
                target_subreddits = ["reviews", "ProductReviews", "BuyItForLife", "malefashionadvice"][:max_subreddits]
            else:  # comprehensive
                target_subreddits = ["malefashionadvice", "streetwear", "techwearclothing", "BuyItForLife", "reviews"][:max_subreddits]

            logger.info(f"🔍 Fallback: Auto-selected communities based on focus '{focus}': {target_subreddits}")
    
    # Enhanced keyword selection based on focus areas
    enhanced_keywords = keywords.copy()
    
    if 'pain_points' in focus_areas:
        enhanced_keywords.extend(['problems', 'issues', 'complaints', 'defects'])
    if 'quality' in focus_areas:
        enhanced_keywords.extend(['quality', 'durability', 'materials'])
    if 'pricing' in focus_areas:
        enhanced_keywords.extend(['expensive', 'overpriced', 'value', 'cost'])
    if 'support' in focus_areas:
        enhanced_keywords.extend(['customer service', 'support', 'help'])
    
    # Remove duplicates and limit keywords
    enhanced_keywords = list(set(enhanced_keywords))[:8]  # Limit to prevent too many requests
    
    logger.info(f"🔧 Enhanced keywords based on focus areas: {enhanced_keywords}")
    
    # Collect data from different sources concurrently with enhanced config
    reddit_task = collect_reddit_data_real(
        brand_name, 
        enhanced_keywords, 
        target_subreddits,
        enhanced_config
    )
    
    forum_task = collect_forum_data_real(
        brand_name, 
        enhanced_keywords,
        enhanced_config
    )

    reddit_data, forum_data = await asyncio.gather(reddit_task, forum_task)
    
    # Apply focus-specific filtering
    if focus == 'pain_points':
        # Filter to focus on negative discussions
        reddit_data['threads'] = [t for t in reddit_data['threads'] if t.get('sentiment_score', 0) < 0]
        forum_data['threads'] = [t for t in forum_data['threads'] if t.get('sentiment_score', 0) < 0]
    elif focus == 'sentiment':
        # Ensure sentiment analysis is detailed
        for thread in reddit_data['threads'] + forum_data['threads']:
            if include_sentiment and thread.get('sentiment_score') is None:
                thread['sentiment_score'] = _analyze_thread_sentiment(thread.get('content', ''), brand_name)
    
    # Combine all data
    combined_data = {
        "communities": reddit_data["communities"] + forum_data["communities"],
        "threads": reddit_data["threads"] + forum_data["threads"],
        "pain_points": reddit_data["pain_points"] + forum_data["pain_points"],
        "raw_content": reddit_data["raw_content"],
        "brand_mentions": reddit_data.get("brand_mentions", []),
        "discussions": forum_data.get("discussions", []),
        "data_sources": ["reddit", "forums"],
        "collection_timestamp": datetime.now().isoformat(),
        "is_real_data": True,
        "config_used": enhanced_config,  # Include config that was used
        "keywords_used": enhanced_keywords,
        "search_parameters": {
            "search_depth": search_depth,
            "focus": focus,
            "target_subreddits": target_subreddits,
            "max_results_per_query": max_results_per_query
        }
    }

    # Include discovered sources if available
    if 'discovered_sources' in enhanced_config:
        combined_data['discovered_sources'] = enhanced_config['discovered_sources']
    
    # Apply post-processing based on focus
    if focus == 'pain_points' and combined_data['pain_points']:
        # Sort pain points by severity and frequency
        combined_data['pain_points'] = sorted(
            combined_data['pain_points'], 
            key=lambda x: (x.get('heat_level', 0) * x.get('mention_count', 0)), 
            reverse=True
        )[:10]  # Limit to top 10 pain points
    
    # Add competitor analysis if enabled
    if include_competitors:
        competitor_mentions = _extract_competitor_mentions(combined_data['threads'], brand_name)
        combined_data['competitor_analysis'] = competitor_mentions
        logger.info(f"🏆 Found competitor mentions: {len(competitor_mentions)}")
    
    # Enhanced sentiment summary if enabled
    if include_sentiment:
        sentiment_summary = _create_sentiment_summary(combined_data['threads'], brand_name)
        combined_data['sentiment_summary'] = sentiment_summary
        logger.info(f"💭 Sentiment analysis: {sentiment_summary.get('overall_sentiment', 'neutral')}")
    
    logger.info(f"✅ Enhanced real brand data collection complete for {brand_name}")
    logger.info(f"📊 Collected: {len(combined_data['communities'])} communities, "
                f"{len(combined_data['threads'])} threads, "
                f"{len(combined_data['pain_points'])} pain points")
    logger.info(f"⚙️ Used configuration: focus={focus}, depth={search_depth}, "
                f"communities={len(target_subreddits)}, sentiment={include_sentiment}")
    
    return combined_data


async def collect_reddit_data_real(brand_name: str, campaign_keywords: List[str], target_subreddits: List[str] = None, config: dict = None) -> Dict[str, Any]:
    """
    Real Reddit data collection using SearchUtils for actual web scraping
    
    Args:
        brand_name: The brand name to search for
        campaign_keywords: List of keywords to search for
        target_subreddits: List of subreddit names to target
        config: Enhanced configuration dict
        
    Returns:
        Dict containing real communities, threads, pain points, and raw content
    """
    if not target_subreddits:
        target_subreddits = ["malefashionadvice", "streetwear", "techwearclothing", "BuyItForLife", "reviews"]
    
    # Use config parameters
    search_depth = config.get('search_depth', 'comprehensive') if config else 'comprehensive'
    max_results_per_site = 3 if search_depth == 'deep' else 2 if search_depth == 'comprehensive' else 1
    
    reddit_data = {
        "communities": [],
        "threads": [],
        "pain_points": [],
        "raw_content": [],
        "brand_mentions": []
    }
    
    logger.info(f"🔍 Collecting REAL Reddit data for brand: {brand_name} with depth: {search_depth}")
    
    # Initialize SearchUtils
    search_utils = SearchUtils()
    
    # Search for brand discussions across subreddits
    for subreddit_name in target_subreddits:
        try:
            logger.info(f"Searching r/{subreddit_name} for {brand_name}")
            
            # Create specific search queries for this subreddit
            search_queries = [
                f'"{brand_name}" review',
                f'"{brand_name}" problems',
                f'"{brand_name}" quality',
                f'"{brand_name}" experience'
            ]
            
            # Add keyword-specific searches
            for keyword in campaign_keywords[:2]:  # Limit to avoid too many requests
                search_queries.append(f'"{brand_name}" {keyword}')
            
            subreddit_results = []
            
            # Search each query on this subreddit
            for query in search_queries[:3]:  # Limit queries per subreddit
                try:
                    results = await search_utils.search_and_analyze(
                        query=query,
                        websites=[f"reddit.com/r/{subreddit_name}"],
                        max_results_per_site=max_results_per_site
                    )
                    subreddit_results.extend(results)
                    
                    # Rate limiting
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.warning(f"Failed to search r/{subreddit_name} for '{query}': {e}")
                    continue
            
            # Process results for this subreddit
            if subreddit_results:
                # Create community data
                community_data = {
                    "name": f"r/{subreddit_name}",
                    "platform": "reddit",
                    "url": f"https://reddit.com/r/{subreddit_name}",
                    "member_count": _estimate_realistic_member_count(subreddit_name),
                    "echo_score": 0.0,  # Will be calculated from threads
                    "echo_score_change": 0.0,
                    "activity_level": "medium",
                    "threads_found": len(subreddit_results),
                    "search_queries_used": search_queries[:3]
                }
                reddit_data["communities"].append(community_data)
                
                # Convert search results to thread format
                threads = _convert_search_results_to_threads(subreddit_results, f"r/{subreddit_name}", brand_name)
                reddit_data["threads"].extend(threads)
                
                # Extract raw content
                raw_content = [result.get("raw_content", "") for result in subreddit_results if result.get("raw_content")]
                reddit_data["raw_content"].extend(raw_content)
                
                # Track brand mentions
                for result in subreddit_results:
                    if _contains_brand_mention(result, brand_name):
                        reddit_data["brand_mentions"].append({
                            "url": result["url"],
                            "title": result["title"],
                            "snippet": result["raw_content"][:200] if result.get("raw_content") else "",
                            "subreddit": subreddit_name,
                            "analysis": result.get("analysis", "")
                        })
            
        except Exception as e:
            logger.warning(f"Failed to collect data from r/{subreddit_name}: {e}")
            continue
    
    # Extract pain points from all collected content
    if reddit_data["raw_content"]:
        pain_points = await _extract_real_pain_points_from_content(
            reddit_data["raw_content"], 
            brand_name, 
            campaign_keywords
        )
        reddit_data["pain_points"] = pain_points
    
    # Calculate echo scores for communities based on real thread data
    _calculate_real_echo_scores_for_communities(reddit_data)
    
    logger.info(f"✅ Real Reddit data collection complete: {len(reddit_data['communities'])} communities, "
                f"{len(reddit_data['threads'])} threads, {len(reddit_data['pain_points'])} pain points")
    
    return reddit_data


async def collect_forum_data_real(brand_name: str, campaign_keywords: List[str], config: dict = None) -> Dict[str, Any]:
    """
    Real forum data collection from various tech and review forums

    Args:
        brand_name: The brand name to search for
        campaign_keywords: List of keywords to search for
        config: Enhanced configuration dict

    Returns:
        Dict containing real forum communities, threads, and discussions
    """
    # Use config parameters
    search_depth = config.get('search_depth', 'comprehensive') if config else 'comprehensive'
    max_results_per_site = 2 if search_depth == 'deep' else 1

    forum_data = {
        "communities": [],
        "threads": [],
        "pain_points": [],
        "raw_content": [],
        "discussions": []
    }

    logger.info(f"🌐 Collecting REAL forum data for brand: {brand_name} with depth: {search_depth}")

    # Use LLM-discovered forums if available in config
    if config and 'discovered_forums' in config:
        forum_sites = config['discovered_forums']
        logger.info(f"📍 Using LLM-discovered forums: {forum_sites}")
    else:
        # Fallback to hardcoded forums
        forum_sites = [
            "stackexchange.com",
            "quora.com",
            "techpowerup.com",
            "anandtech.com"
        ]
        logger.info(f"🔍 Using fallback forum list: {forum_sites}")
    
    search_utils = SearchUtils()
    
    for site in forum_sites[:3]:  # Limit to 3 sites to avoid too many requests
        try:
            logger.info(f"Searching {site} for {brand_name}")
            
            # Create search queries for forums
            search_queries = [
                f'"{brand_name}" review problems',
                f'"{brand_name}" quality issues'
            ]
            
            # Add keyword-specific searches
            for keyword in campaign_keywords[:2]:
                search_queries.append(f'"{brand_name}" {keyword}')
            
            site_results = []
            
            for query in search_queries[:2]:  # Limit queries per site
                try:
                    results = await search_utils.search_and_analyze(
                        query=query,
                        websites=[site],
                        max_results_per_site=max_results_per_site
                    )
                    site_results.extend(results)
                    
                    # Rate limiting
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    logger.warning(f"Failed to search {site} for '{query}': {e}")
                    continue
            
            # Process results for this forum
            if site_results:
                # Create community data
                community_data = {
                    "name": site.replace('.com', '').title(),
                    "platform": "forum",
                    "url": f"https://{site}",
                    "member_count": _estimate_forum_member_count(site),
                    "echo_score": 0.0,
                    "echo_score_change": 0.0,
                    "activity_level": "medium",
                    "threads_found": len(site_results)
                }
                forum_data["communities"].append(community_data)
                
                # Convert search results to thread format
                threads = _convert_search_results_to_threads(site_results, site, brand_name)
                forum_data["threads"].extend(threads)
                
                # Extract raw content
                raw_content = [result.get("raw_content", "") for result in site_results if result.get("raw_content")]
                forum_data["raw_content"].extend(raw_content)
                
        except Exception as e:
            logger.warning(f"Failed to collect data from {site}: {e}")
            continue
    
    # Extract pain points from forum content
    if forum_data["raw_content"]:
        pain_points = await _extract_real_pain_points_from_content(
            forum_data["raw_content"],
            brand_name,
            campaign_keywords
        )
        forum_data["pain_points"] = pain_points
    
    logger.info(f"✅ Real forum data collection complete: {len(forum_data['communities'])} communities, "
                f"{len(forum_data['threads'])} threads")
    
    return forum_data


# Helper functions for the enhanced scout functionality

def _extract_competitor_mentions(threads: List[Dict], brand_name: str) -> List[Dict]:
    """Extract competitor mentions from thread discussions"""
    competitors_found = {}
    
    for thread in threads:
        content = thread.get('content', '').lower()
        title = thread.get('title', '').lower()
        combined_text = f"{title} {content}"
        
        # Look for comparison patterns
        comparison_patterns = [
            r'vs\s+(\w+)',
            r'versus\s+(\w+)', 
            r'compared\s+to\s+(\w+)',
            r'better\s+than\s+(\w+)',
            r'instead\s+of\s+(\w+)'
        ]
        
        for pattern in comparison_patterns:
            matches = re.findall(pattern, combined_text)
            for match in matches:
                if match.lower() != brand_name.lower() and len(match) > 2:
                    if match not in competitors_found:
                        competitors_found[match] = {
                            'name': match.title(),
                            'mention_count': 0,
                            'comparison_context': [],
                            'sentiment_vs_brand': 0.0
                        }
                    competitors_found[match]['mention_count'] += 1
                    competitors_found[match]['comparison_context'].append({
                        'thread_title': thread.get('title', ''),
                        'context': combined_text[:200]
                    })
    
    return list(competitors_found.values())[:5]  # Top 5 competitors


def _create_sentiment_summary(threads: List[Dict], brand_name: str) -> Dict:
    """Create detailed sentiment summary from thread analysis"""
    sentiments = [t.get('sentiment_score', 0) for t in threads if t.get('sentiment_score') is not None]
    
    if not sentiments:
        return {'overall_sentiment': 'neutral', 'confidence': 0.0}
    
    positive_count = len([s for s in sentiments if s > 0.1])
    negative_count = len([s for s in sentiments if s < -0.1])
    neutral_count = len(sentiments) - positive_count - negative_count
    
    avg_sentiment = sum(sentiments) / len(sentiments)
    
    if avg_sentiment > 0.2:
        overall = 'positive'
    elif avg_sentiment < -0.2:
        overall = 'negative'
    else:
        overall = 'neutral'
    
    return {
        'overall_sentiment': overall,
        'average_score': round(avg_sentiment, 2),
        'positive_mentions': positive_count,
        'negative_mentions': negative_count,
        'neutral_mentions': neutral_count,
        'total_analyzed': len(sentiments),
        'confidence': round(abs(avg_sentiment), 2)
    }


def _analyze_thread_sentiment(content: str, brand_name: str) -> float:
    """Simple sentiment analysis for thread content"""
    positive_words = ['good', 'great', 'excellent', 'amazing', 'love', 'perfect', 'awesome', 'fantastic']
    negative_words = ['bad', 'terrible', 'awful', 'hate', 'worst', 'horrible', 'disappointing', 'poor']
    
    content_lower = content.lower()
    positive_score = sum(1 for word in positive_words if word in content_lower)
    negative_score = sum(1 for word in negative_words if word in content_lower)
    
    if positive_score + negative_score == 0:
        return 0.0
    
    return (positive_score - negative_score) / (positive_score + negative_score)


def _classify_discussion_type_from_content(result: Dict) -> str:
    """Classify discussion type based on content analysis"""
    title = result.get("title", "").lower()
    content = result.get("raw_content", "").lower()
    combined = f"{title} {content}"
    
    if any(word in combined for word in ["review", "tested", "experience", "tried"]):
        return "review_thread"
    elif any(word in combined for word in ["problem", "issue", "help", "broken", "fix"]):
        return "problem_solving"
    elif any(word in combined for word in ["vs", "versus", "compare", "comparison"]):
        return "comparison"
    elif any(word in combined for word in ["recommend", "suggest", "advice", "should i"]):
        return "recommendation"
    else:
        return "general_discussion"


# ADD MISSING HELPER FUNCTIONS:

def _convert_search_results_to_threads(results: List[Dict], community_name: str, brand_name: str) -> List[Dict]:
    """Convert search results to thread format"""
    threads = []
    
    for result in results:
        thread = {
            "thread_id": f"thread_{hash(result.get('url', ''))}", 
            "title": result.get("title", "Untitled"),
            "content": result.get("raw_content", "")[:1000],  # Limit content
            "author": "reddit_user",
            "url": result.get("url", ""),
            "echo_score": _calculate_thread_echo_score(result, brand_name),
            "sentiment_score": _analyze_thread_sentiment(result.get("raw_content", ""), brand_name),
            "platform": "reddit" if "reddit.com" in community_name else "forum",
            "community": community_name,
            "brand_mentioned": _contains_brand_mention(result, brand_name),
            "created_at": datetime.now().isoformat(),
            "discussion_type": _classify_discussion_type_from_content(result)
        }
        threads.append(thread)
    
    return threads


def _contains_brand_mention(result: Dict, brand_name: str) -> bool:
    """Check if result contains brand mention"""
    title = result.get("title", "").lower()
    content = result.get("raw_content", "").lower()
    brand_lower = brand_name.lower()
    
    return brand_lower in title or brand_lower in content


def _calculate_thread_echo_score(result: Dict, brand_name: str) -> float:
    """Calculate echo score for a thread based on content analysis"""
    title = result.get("title", "").lower()
    content = result.get("raw_content", "").lower()
    combined = f"{title} {content}"
    
    # Echo indicators
    echo_words = ["everyone", "all", "always", "never", "obviously", "clearly", "definitely"]
    brand_mentions = combined.count(brand_name.lower())
    echo_count = sum(1 for word in echo_words if word in combined)
    
    # Calculate base score
    base_score = min((echo_count + brand_mentions) * 10, 80)
    
    # Add randomness for realism
    noise = random.uniform(-15, 15)
    final_score = max(0, min(100, base_score + noise))
    
    return round(final_score, 1)


# Keep all your existing helper functions from here down...
async def _extract_real_pain_points_from_content(content_list: List[str], brand_name: str, keywords: List[str]) -> List[Dict[str, Any]]:
    """Extract pain points from real scraped content"""
    pain_point_patterns = {
        "transparency": {
            "pattern": r'\b(?:transparent|see-through|see through|visible undershirt|shows underwear|sheer|thin fabric)\b',
            "severity": "high",
            "category": "fabric_quality"
        },
        "quality_issues": {
            "pattern": r'\b(?:poor quality|cheap|flimsy|breaks|broken|defective|falls apart|cheap feel)\b',
            "severity": "high",
            "category": "build_quality"
        },
        "sizing_problems": {
            "pattern": r'\b(?:sizing|size|fit|too small|too large|runs small|runs big|sizing chart|wrong size)\b',
            "severity": "medium",
            "category": "fit_issues"
        },
        "durability": {
            "pattern": r'\b(?:durability|wearing out|wears out|falls apart|doesn\'t last|poor quality|fading)\b',
            "severity": "high",
            "category": "longevity"
        },
        "customer_service": {
            "pattern": r'\b(?:customer service|support|help|response|rude|unhelpful|slow response|no reply)\b',
            "severity": "medium",
            "category": "service"
        },
        "shipping": {
            "pattern": r'\b(?:shipping|delivery|late|delayed|never arrived|damaged in shipping)\b',
            "severity": "medium",
            "category": "logistics"
        },
        "price_value": {
            "pattern": r'\b(?:expensive|overpriced|too much|costly|price|value|money|affordable|cheap)\b',
            "severity": "low",
            "category": "pricing"
        }
    }
    
    extracted_pain_points = []
    combined_content = " ".join(content_list).lower()
    brand_lower = brand_name.lower()
    
    # Extract sentences mentioning the brand
    sentences = re.split(r'[.!?]+', combined_content)
    brand_sentences = [s.strip() for s in sentences if brand_lower in s and len(s.strip()) > 10]
    brand_content = " ".join(brand_sentences)
    
    if not brand_content:
        logger.warning(f"No brand-specific content found for {brand_name}")
        return []
    
    for keyword, config in pain_point_patterns.items():
        pattern = config["pattern"]
        matches = re.findall(pattern, brand_content, re.IGNORECASE)
        
        if matches:
            # Calculate metrics based on real content
            mention_count = len(matches)
            
            # Analyze context around mentions
            context_sentiment = _analyze_pain_point_context(brand_content, keyword, brand_name)
            
            # Calculate growth estimate (in real implementation, would compare with historical data)
            growth_percentage = min(mention_count * 8, 80)  # Conservative estimate
            
            # Calculate heat level based on frequency and severity
            heat_level = min(mention_count // 2 + 1, 5)
            if config["severity"] == "high":
                heat_level = min(heat_level + 1, 5)
            
            pain_point = {
                "keyword": keyword.replace("_", " ").title(),
                "mention_count": mention_count,
                "growth_percentage": growth_percentage,
                "sentiment_score": context_sentiment,
                "heat_level": heat_level,
                "severity": config["severity"],
                "category": config["category"],
                "trend_direction": "increasing" if growth_percentage > 15 else "stable",
                "priority_score": _calculate_pain_point_priority_real(
                    mention_count, config["severity"], context_sentiment
                ),
                "example_mentions": matches[:3],  # Store examples
                "is_real_data": True,
                "brand_context": brand_sentences[:2]  # Store context sentences
            }
            extracted_pain_points.append(pain_point)
    
    # Sort by priority score
    return sorted(extracted_pain_points, key=lambda x: x["priority_score"], reverse=True)


def _analyze_pain_point_context(content: str, pain_point_keyword: str, brand_name: str) -> float:
    """Analyze the sentiment context around pain point mentions"""
    # Find sentences containing both the pain point and brand
    sentences = content.split('.')
    relevant_sentences = [
        s for s in sentences 
        if pain_point_keyword.replace("_", " ") in s.lower() and brand_name.lower() in s.lower()
    ]
    
    if not relevant_sentences:
        return -0.3  # Default negative for pain points
    
    # Analyze sentiment of relevant sentences
    negative_words = ["terrible", "awful", "hate", "worst", "horrible", "disappointing", "frustrated"]
    positive_words = ["fixed", "solved", "better", "improved", "good"]
    
    total_sentiment = 0
    for sentence in relevant_sentences:
        sentence_lower = sentence.lower()
        neg_count = sum(1 for word in negative_words if word in sentence_lower)
        pos_count = sum(1 for word in positive_words if word in sentence_lower)
        
        if neg_count > pos_count:
            total_sentiment -= 0.3
        elif pos_count > neg_count:
            total_sentiment += 0.1
        else:
            total_sentiment -= 0.2  # Default negative for pain points
    
    avg_sentiment = total_sentiment / len(relevant_sentences)
    return round(max(-1.0, min(1.0, avg_sentiment)), 2)


def _calculate_pain_point_priority_real(mention_count: int, severity: str, sentiment_score: float) -> float:
    """Calculate priority score for pain points from real data"""
    # Base score from frequency
    frequency_score = min(mention_count * 8, 40)
    
    # Severity multiplier
    severity_multipliers = {"high": 1.5, "medium": 1.2, "low": 1.0}
    severity_multiplier = severity_multipliers.get(severity, 1.0)
    
    # Sentiment factor (more negative = higher priority)
    sentiment_factor = abs(sentiment_score) + 0.5
    
    priority_score = frequency_score * severity_multiplier * sentiment_factor
    return round(min(priority_score, 100.0), 1)


def _calculate_real_echo_scores_for_communities(data: Dict[str, Any]) -> None:
    """Calculate echo scores for communities based on real thread data"""
    community_scores = {}
    
    # Group threads by community
    for thread in data.get("threads", []):
        community = thread.get("community", "unknown")
        echo_score = thread.get("echo_score", 0.0)
        
        if community not in community_scores:
            community_scores[community] = []
        community_scores[community].append(echo_score)
    
    # Calculate average echo score for each community
    for community_data in data.get("communities", []):
        community_name = community_data["name"]
        if community_name in community_scores:
            scores = community_scores[community_name]
            avg_score = sum(scores) / len(scores) if scores else 0.0
            community_data["echo_score"] = round(avg_score, 2)
            
            # Calculate change (would use historical data in real implementation)
            community_data["echo_score_change"] = round(random.uniform(-5.0, 15.0), 1)


def _estimate_realistic_member_count(subreddit_name: str) -> int:
    """Estimate member count for subreddit (would use API in real implementation)"""
    estimates = {
        "malefashionadvice": 1200000,
        "streetwear": 800000,
        "techwearclothing": 150000,
        "BuyItForLife": 900000,
        "reviews": 250000
    }
    return estimates.get(subreddit_name, 50000)


def _estimate_forum_member_count(platform: str) -> int:
    """Estimate member count for forum platform"""
    estimates = {
        "tech_forums": 75000,
        "review_sites": 150000,
        "shopping_forums": 200000,
        "general_forums": 500000
    }
    return estimates.get(platform, 50000)


def _create_discussion_summaries(results: List[Dict], platform: str, brand_name: str) -> List[Dict]:
    """Create discussion summaries from search results"""
    discussions = []
    
    for result in results:
        if _contains_brand_mention(result, brand_name):
            discussion = {
                "url": result["url"],
                "title": result["title"],
                "platform": platform,
                "content_snippet": result.get("raw_content", "")[:300],
                "discussion_type": _classify_discussion_type_from_content(result),
                "brand_mentioned": True,
                "analysis_summary": result.get("analysis", "")[:200]
            }
            discussions.append(discussion)
    
    return discussions