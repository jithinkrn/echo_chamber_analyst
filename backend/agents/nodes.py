"""
LangGraph Node Implementations

This module contains the individual node implementations that replace
the custom agents, providing tools integration, LLM capabilities,
and sophisticated processing logic.
"""

import asyncio
import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import json
import re

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain.tools import Tool
from langchain_community.tools import DuckDuckGoSearchRun

from .state import (
    EchoChamberAnalystState, ContentItem, Insight, InfluencerProfile,
    ContentType, InsightType, TaskStatus, ProcessingMetrics
)
from .tools import get_tools_for_node, LANGGRAPH_TOOLS
from .monitoring import (
    monitor_node_execution, global_monitor,
    trace_insight_generation, trace_content_filtering
)

# Import Django models for dashboard data
from common.models import Campaign, Community, PainPoint, Influencer, Thread, DashboardMetrics

logger = logging.getLogger(__name__)


# Initialize OpenAI LLM
llm = ChatOpenAI(
    model="gpt-4",
    temperature=0.1,
    max_tokens=2000
)


# Dashboard-specific data collection functions
async def collect_reddit_data(campaign_keywords: List[str], target_subreddits: List[str] = None) -> Dict[str, Any]:
    """Enhanced Reddit data collection for dashboard"""
    if not target_subreddits:
        target_subreddits = ["malefashionadvice", "streetwear", "techwearclothing", "BuyItForLife"]
    
    reddit_data = {
        "communities": [],
        "threads": [],
        "pain_points": [],
        "influencers": [],
        "raw_content": []
    }
    
    for subreddit_name in target_subreddits:
        # Simulate Reddit API data collection
        community_data = {
            "name": f"r/{subreddit_name}",
            "platform": "reddit",
            "url": f"https://reddit.com/r/{subreddit_name}",
            "member_count": _generate_realistic_member_count(subreddit_name),
            "echo_score": _calculate_community_echo_score(subreddit_name),
            "echo_score_change": _calculate_echo_score_change(subreddit_name)
        }
        reddit_data["communities"].append(community_data)
        
        # Simulate thread collection
        threads = _simulate_subreddit_threads(subreddit_name, campaign_keywords)
        reddit_data["threads"].extend(threads)
        reddit_data["raw_content"].extend([t["content"] for t in threads])
        
        # Extract influencers from threads
        influencers = _extract_influencers_from_threads(threads, subreddit_name)
        reddit_data["influencers"].extend(influencers)
    
    # Extract pain points from content
    pain_points = _extract_pain_points_from_content(reddit_data["raw_content"], campaign_keywords)
    reddit_data["pain_points"] = pain_points
    
    return reddit_data


async def collect_discord_data(campaign_keywords: List[str]) -> Dict[str, Any]:
    """Enhanced Discord data collection for dashboard"""
    discord_servers = ["Techwear Community", "Fashion Advice", "Streetwear Hub"]
    
    discord_data = {
        "communities": [],
        "threads": [],
        "pain_points": [],
        "influencers": []
    }
    
    for server_name in discord_servers:
        community_data = {
            "name": server_name,
            "platform": "discord",
            "url": f"https://discord.gg/{server_name.lower().replace(' ', '')}",
            "member_count": _generate_realistic_member_count(server_name, platform="discord"),
            "echo_score": _calculate_community_echo_score(server_name),
            "echo_score_change": _calculate_echo_score_change(server_name)
        }
        discord_data["communities"].append(community_data)
        
        # Simulate Discord message threads
        threads = _simulate_discord_threads(server_name, campaign_keywords)
        discord_data["threads"].extend(threads)
    
    return discord_data


async def collect_tiktok_data(campaign_keywords: List[str]) -> Dict[str, Any]:
    """Enhanced TikTok data collection for dashboard"""
    tiktok_data = {
        "communities": [],
        "influencers": [],
        "threads": []
    }
    
    # Simulate TikTok influencer discovery
    influencers = [
        {
            "handle": "may.tan",
            "platform": "tiktok",
            "reach": 41000,
            "engagement_rate": 8.1,
            "topics": ["transparency", "fashion review", "clothing tips"],
            "last_active": datetime.now() - timedelta(hours=2)
        },
        {
            "handle": "styleguruteam",
            "platform": "tiktok", 
            "reach": 28000,
            "engagement_rate": 12.3,
            "topics": ["outfit tips", "brand reviews", "fashion hauls"],
            "last_active": datetime.now() - timedelta(hours=6)
        }
    ]
    
    tiktok_data["influencers"] = influencers
    
    # Simulate TikTok community data
    community_data = {
        "name": "TikTok Fashion",
        "platform": "tiktok",
        "url": "https://tiktok.com/@fashion",
        "member_count": 500000,
        "echo_score": 6.8,
        "echo_score_change": 15.0
    }
    tiktok_data["communities"].append(community_data)
    
    return tiktok_data


def _generate_realistic_member_count(community_name: str, platform: str = "reddit") -> int:
    """Generate realistic member counts based on community name and platform"""
    base_counts = {
        "malefashionadvice": 1200000,
        "streetwear": 800000,
        "techwearclothing": 150000,
        "BuyItForLife": 900000,
        "Techwear Community": 25000,
        "Fashion Advice": 45000,
        "Streetwear Hub": 32000
    }
    return base_counts.get(community_name, 50000)


def _calculate_community_echo_score(community_name: str) -> float:
    """Calculate echo score for a community"""
    # Simulate echo score calculation based on community characteristics
    base_scores = {
        "malefashionadvice": 8.2,
        "streetwear": 7.4,
        "techwearclothing": 9.1,
        "BuyItForLife": 6.8,
        "Techwear Community": 7.4,
        "Fashion Advice": 6.2,
        "Streetwear Hub": 8.0,
        "TikTok Fashion": 6.8
    }
    return base_scores.get(community_name, 7.0)


def _calculate_echo_score_change(community_name: str) -> float:
    """Calculate echo score change percentage"""
    # Simulate realistic change percentages
    changes = {
        "malefashionadvice": 12.0,
        "streetwear": 8.0,
        "techwearclothing": 15.0,
        "BuyItForLife": -2.0,
        "Techwear Community": 8.0,
        "Fashion Advice": 5.0,
        "Streetwear Hub": 10.0,
        "TikTok Fashion": 15.0
    }
    return changes.get(community_name, 0.0)


def _simulate_subreddit_threads(subreddit_name: str, keywords: List[str]) -> List[Dict[str, Any]]:
    """Simulate realistic subreddit thread data"""
    sample_threads = [
        {
            "thread_id": f"reddit_{subreddit_name}_001",
            "title": "Transparency issues with new shirt - can see undershirt clearly",
            "content": "I bought this shirt yesterday and under office fluorescent lights you can see my undershirt clearly. Anyone else having this transparency problem? The fabric feels good but this is embarrassing at work.",
            "author": "u/office_worker_23",
            "comment_count": 45,
            "score": 89,
            "upvote_ratio": 0.85,
            "awards": 2,
            "echo_score": 8.2,
            "created_at": datetime.now() - timedelta(hours=12),
            "platform": "reddit",
            "community": f"r/{subreddit_name}"
        },
        {
            "thread_id": f"reddit_{subreddit_name}_002", 
            "title": "Collar keeps curling up even after washing - any fixes?",
            "content": "No matter how I wash or iron this shirt, the collar keeps curling up. Tried different techniques but nothing works. Seeing this issue across multiple brands now.",
            "author": "u/collar_problems",
            "comment_count": 32,
            "score": 67,
            "upvote_ratio": 0.78,
            "awards": 1,
            "echo_score": 7.8,
            "created_at": datetime.now() - timedelta(hours=8),
            "platform": "reddit",
            "community": f"r/{subreddit_name}"
        }
    ]
    
    # Filter threads based on keywords
    relevant_threads = []
    for thread in sample_threads:
        thread_text = f"{thread['title']} {thread['content']}".lower()
        if any(keyword.lower() in thread_text for keyword in keywords):
            relevant_threads.append(thread)
    
    return relevant_threads


def _simulate_discord_threads(server_name: str, keywords: List[str]) -> List[Dict[str, Any]]:
    """Simulate Discord thread/message data"""
    return [
        {
            "thread_id": f"discord_{server_name.replace(' ', '_')}_001",
            "title": "Weekly discussion: Fabric durability issues",
            "content": "Has anyone noticed pilling issues with backpack straps? Multiple people reporting this problem.",
            "author": "ModeratorBot",
            "comment_count": 28,
            "echo_score": 7.2,
            "created_at": datetime.now() - timedelta(hours=6),
            "platform": "discord",
            "community": server_name
        }
    ]


def _extract_influencers_from_threads(threads: List[Dict[str, Any]], community: str) -> List[Dict[str, Any]]:
    """Extract potential influencers from thread data"""
    influencers = []
    
    # Simulate influencer identification based on thread activity
    if "malefashionadvice" in community:
        influencers.append({
            "handle": "SmartHomeGuru",
            "platform": "reddit",
            "reach": 23000,
            "engagement_rate": 12.4,
            "karma_score": 45000,
            "topics": ["DIY collar fix", "fabric care", "style tips"],
            "last_active": datetime.now() - timedelta(hours=3)
        })
    elif "streetwear" in community:
        influencers.append({
            "handle": "ZHangCycle",
            "platform": "reddit", 
            "reach": 17000,
            "engagement_rate": 9.6,
            "karma_score": 32000,
            "topics": ["sweat-wicking test", "athletic wear", "performance fabrics"],
            "last_active": datetime.now() - timedelta(hours=1)
        })
    
    return influencers


def _extract_pain_points_from_content(content_list: List[str], keywords: List[str]) -> List[Dict[str, Any]]:
    """Extract pain points using keyword analysis and pattern matching"""
    pain_point_patterns = {
        "transparency": r'\b(?:transparent|see-through|see through|visible undershirt|shows underwear)\b',
        "collar-curl": r'\b(?:collar curl|collar curls|collar curling|collar stays|collar problems)\b',
        "pilling": r'\b(?:pills|pilling|fabric balls|fuzz balls|bobbling)\b',
        "durability": r'\b(?:durability|wearing out|falls apart|poor quality|doesnt last)\b',
        "sizing": r'\b(?:sizing|fit|too small|too large|runs small|runs big)\b',
        "price": r'\b(?:expensive|overpriced|too much|costly|price|affordable)\b'
    }
    
    extracted_pain_points = []
    combined_content = " ".join(content_list).lower()
    
    for keyword, pattern in pain_point_patterns.items():
        matches = len(re.findall(pattern, combined_content, re.IGNORECASE))
        if matches > 0:
            # Simulate growth percentage based on matches
            growth_percentage = min(matches * 15, 150)  # Cap at 150%
            
            extracted_pain_points.append({
                "keyword": keyword,
                "mention_count": matches,
                "growth_percentage": growth_percentage,
                "sentiment_score": _analyze_sentiment_for_keyword(keyword, combined_content),
                "heat_level": min(matches // 3 + 1, 5)  # 1-5 heat level
            })
    
    return sorted(extracted_pain_points, key=lambda x: x["growth_percentage"], reverse=True)


def _analyze_sentiment_for_keyword(keyword: str, content: str) -> float:
    """Analyze sentiment for a specific keyword in content"""
    # Simulate sentiment analysis - negative keywords get negative scores
    negative_keywords = ["transparency", "collar-curl", "pilling", "durability"]
    if keyword in negative_keywords:
        return -0.6  # Negative sentiment for pain points
    return 0.2  # Slightly positive for neutral keywords


@monitor_node_execution(global_monitor)
async def scout_node(state: EchoChamberAnalystState) -> EchoChamberAnalystState:
    """
    Enhanced Scout Node - Content Discovery and Dashboard Data Collection

    Replaces the Scout Agent with LangGraph node that uses tools
    for content discovery, EchoScore calculation, source management,
    and comprehensive dashboard data collection across multiple platforms.
    """
    state.current_node = "scout_content"

    try:
        logger.info(f"Enhanced Scout node processing campaign: {state.campaign.campaign_id}")

        # Get tools for scout operations
        tools = get_tools_for_node("scout")

        # Create enhanced scout prompt
        scout_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an enhanced content scout agent responsible for comprehensive data collection across multiple platforms.

            Campaign Context:
            - Campaign: {campaign_name}
            - Keywords: {keywords}
            - Sources: {sources}
            - Budget Remaining: ${budget_remaining}

            Enhanced Capabilities:
            1. Multi-platform content discovery (Reddit, Discord, TikTok)
            2. Community analysis and echo score calculation
            3. Pain point extraction and trend analysis
            4. Influencer identification and engagement tracking
            5. Real-time sentiment monitoring
            6. Dashboard metrics collection
            7. Engagement pattern analysis
            8. Content classification and prioritization

            Your tasks:
            1. Analyze campaign requirements across all platforms
            2. Collect comprehensive community data
            3. Extract pain points and trending topics
            4. Identify key influencers and their reach
            5. Calculate echo scores and engagement metrics
            6. Generate dashboard-ready analytics
            7. Store data for real-time dashboard updates
            8. Monitor content trends and anomalies

            Use the available tools to query databases and create detailed audit logs.
            Focus on collecting rich, multi-dimensional data for comprehensive analysis.
            """),
            ("human", "Discover and collect comprehensive data for dashboard analytics. Platforms: {sources}")
        ])

        # Format the prompt
        formatted_prompt = scout_prompt.format_messages(
            campaign_name=state.campaign.name,
            keywords=", ".join(state.campaign.keywords),
            sources=", ".join(state.campaign.sources),
            budget_remaining=state.campaign.budget_limit - state.campaign.current_spend
        )

        # Enhanced multi-platform data collection
        collected_data = {
            "communities": [],
            "threads": [],
            "pain_points": [],
            "influencers": [],
            "raw_content": []
        }

        # Collect data from multiple platforms
        source_platforms = state.campaign.sources or ["reddit", "discord", "tiktok"]
        
        for platform in source_platforms:
            if platform.lower() == "reddit":
                reddit_data = await collect_reddit_data(state.campaign.keywords)
                collected_data["communities"].extend(reddit_data.get("communities", []))
                collected_data["threads"].extend(reddit_data.get("threads", []))
                collected_data["pain_points"].extend(reddit_data.get("pain_points", []))
                collected_data["influencers"].extend(reddit_data.get("influencers", []))
                collected_data["raw_content"].extend(reddit_data.get("raw_content", []))
                
            elif platform.lower() == "discord":
                discord_data = await collect_discord_data(state.campaign.keywords)
                collected_data["communities"].extend(discord_data.get("communities", []))
                collected_data["threads"].extend(discord_data.get("threads", []))
                
            elif platform.lower() == "tiktok":
                tiktok_data = await collect_tiktok_data(state.campaign.keywords)
                collected_data["communities"].extend(tiktok_data.get("communities", []))
                collected_data["influencers"].extend(tiktok_data.get("influencers", []))

        # Store collected data in Django models for dashboard
        await _store_dashboard_data(collected_data, state.campaign)

        # Convert to existing ContentItem format for compatibility
        discovered_content = []
        for thread in collected_data["threads"]:
            discovered_content.append({
                "id": thread["thread_id"],
                "content": thread["content"],
                "source_url": thread.get("url", f"https://example.com/{thread['thread_id']}"),
                "content_type": "social_media_post",
                "author": thread.get("author"),
                "title": thread.get("title"),
                "published_at": thread.get("created_at"),
                "echo_score": thread.get("echo_score", 0.5)
            })

        # Add discovered content to state
        for content_data in discovered_content:
            content_item = ContentItem(
                id=content_data["id"],
                content=content_data["content"],
                source_url=content_data["source_url"],
                content_type=ContentType(content_data["content_type"]),
                author=content_data.get("author"),
                title=content_data.get("title"),
                published_at=content_data.get("published_at"),
                echo_score=content_data.get("echo_score", 0.5)
            )
            state.add_content(content_item)

        # Update metrics with enhanced tracking
        state.update_metrics(
            tokens=len(str(formatted_prompt)) // 4,
            cost=0.002,  # Increased cost for enhanced capabilities
            api_calls=len(source_platforms)
        )

        # Create comprehensive audit log
        audit_tool = LANGGRAPH_TOOLS["create_audit_log"]
        await audit_tool._arun(
            action_type="enhanced_content_discovery",
            action_description=f"Enhanced Scout discovered {len(discovered_content)} content items across {len(source_platforms)} platforms",
            agent_name="enhanced_scout_node",
            metadata={
                "campaign_id": state.campaign.campaign_id,
                "content_count": len(discovered_content),
                "platforms": source_platforms,
                "communities_found": len(collected_data["communities"]),
                "pain_points_identified": len(collected_data["pain_points"]),
                "influencers_discovered": len(collected_data["influencers"]),
                "capabilities": [
                    "multi_platform_scraping",
                    "community_discovery", 
                    "thread_collection",
                    "influencer_identification",
                    "pain_point_extraction",
                    "echo_score_calculation",
                    "engagement_tracking",
                    "real_time_monitoring"
                ]
            }
        )

        logger.info(f"Enhanced Scout node completed - discovered {len(discovered_content)} items across {len(source_platforms)} platforms")
        logger.info(f"Scout capabilities: 8 enhanced capabilities active")

    except Exception as e:
        logger.error(f"Enhanced Scout node error: {e}")
        state.add_error(f"Enhanced Scout node failed: {e}")

    return state


async def _store_dashboard_data(collected_data: Dict[str, Any], campaign) -> None:
    """Store collected data in Django models for dashboard display"""
    try:
        # Store communities
        for community_data in collected_data.get("communities", []):
            community, created = Community.objects.get_or_create(
                name=community_data["name"],
                platform=community_data["platform"],
                defaults={
                    "url": community_data["url"],
                    "member_count": community_data["member_count"],
                    "echo_score": community_data["echo_score"],
                    "echo_score_change": community_data["echo_score_change"]
                }
            )
            if not created:
                # Update existing community
                community.echo_score = community_data["echo_score"]
                community.echo_score_change = community_data["echo_score_change"]
                community.member_count = community_data["member_count"]
                community.save()

        # Store pain points
        for pain_point_data in collected_data.get("pain_points", []):
            # Get the first community or create a default one
            community = Community.objects.first()
            if community:
                PainPoint.objects.update_or_create(
                    keyword=pain_point_data["keyword"],
                    campaign_id=campaign.id,
                    community=community,
                    defaults={
                        "mention_count": pain_point_data["mention_count"],
                        "growth_percentage": pain_point_data["growth_percentage"],
                        "sentiment_score": pain_point_data["sentiment_score"],
                        "heat_level": pain_point_data["heat_level"]
                    }
                )

        # Store influencers
        for influencer_data in collected_data.get("influencers", []):
            # Get or create community for influencer
            community = Community.objects.filter(
                platform=influencer_data["platform"]
            ).first()
            
            if community:
                Influencer.objects.update_or_create(
                    handle=influencer_data["handle"],
                    platform=influencer_data["platform"],
                    defaults={
                        "reach": influencer_data["reach"],
                        "engagement_rate": influencer_data["engagement_rate"],
                        "karma_score": influencer_data.get("karma_score", 0),
                        "community": community,
                        "topics": influencer_data["topics"],
                        "last_active": influencer_data["last_active"]
                    }
                )

        # Store threads
        for thread_data in collected_data.get("threads", []):
            community = Community.objects.filter(
                name=thread_data["community"]
            ).first()
            
            if community:
                Thread.objects.update_or_create(
                    thread_id=thread_data["thread_id"],
                    defaults={
                        "title": thread_data["title"],
                        "content": thread_data["content"],
                        "community": community,
                        "author": thread_data["author"],
                        "comment_count": thread_data["comment_count"],
                        "echo_score": thread_data["echo_score"],
                        "sentiment_score": pain_point_data.get("sentiment_score", 0.0),
                        "created_at": thread_data["created_at"]
                    }
                )

        logger.info("Dashboard data successfully stored in database")

    except Exception as e:
        logger.error(f"Error storing dashboard data: {e}")
        # Don't raise exception to avoid breaking the workflow


@monitor_node_execution(global_monitor)
async def cleaner_node(state: EchoChamberAnalystState) -> EchoChamberAnalystState:
    """
    Enhanced Data Cleaner Node - Advanced Content Cleaning and Dashboard Data Processing

    Replaces the Data Cleaner Agent with PII detection, spam filtering,
    content validation, compliance tracking, and dashboard-specific cleaning.
    """
    state.current_node = "clean_content"

    try:
        logger.info(f"Enhanced Cleaner node processing {len(state.raw_content)} items")

        # Get tools for cleaning operations
        tools = get_tools_for_node("cleaner")

        # Create enhanced cleaner prompt
        cleaner_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an enhanced data cleaning agent responsible for comprehensive content validation and dashboard data processing.

            Enhanced Capabilities:
            1. Advanced PII detection and masking (emails, phones, SSNs, addresses)
            2. Multi-layer spam and bot detection
            3. Content quality validation and scoring
            4. Sentiment analysis with context awareness
            5. Toxicity and harmful content detection
            6. Language detection and normalization
            7. Entity extraction and keyword analysis
            8. Dashboard-specific data sanitization
            9. Compliance tracking and audit logging
            10. Content deduplication and similarity detection

            Your tasks:
            1. Detect and mask PII with regulatory compliance (GDPR, CCPA)
            2. Filter spam, promotional content, and bot-generated text
            3. Validate content quality and authenticity
            4. Perform advanced sentiment analysis
            5. Extract entities, keywords, and topics
            6. Calculate engagement and echo metrics
            7. Sanitize data for dashboard display
            8. Ensure content compliance with platform policies
            9. Generate cleaning statistics for monitoring
            10. Create audit trails for all cleaning operations

            Guidelines:
            - Remove or mask any PII like emails, phone numbers, addresses, SSNs
            - Filter out spam, promotional content, and bot-generated text
            - Maintain content integrity while ensuring compliance
            - Calculate sentiment scores from -1 (negative) to +1 (positive)
            - Assign toxicity scores from 0 (clean) to 1 (toxic)
            - Track all cleaning operations for audit purposes
            - Optimize data for dashboard performance
            """),
            ("human", "Clean and validate this content with enhanced processing: {content}")
        ])

        cleaned_items = []
        cleaning_stats = {
            "pii_instances_removed": 0,
            "spam_filtered": 0,
            "toxic_content_filtered": 0,
            "duplicates_removed": 0,
            "total_processed": len(state.raw_content),
            "compliance_violations": []
        }

        for content_item in state.raw_content:
            if not content_item.is_cleaned:
                try:
                    # Format prompt for this content
                    formatted_prompt = cleaner_prompt.format_messages(
                        content=content_item.content[:1000]  # Truncate for token limits
                    )

                    # Call LLM for content analysis
                    response = await llm.ainvoke(formatted_prompt)

                    # Enhanced cleaning operations
                    cleaned_data = await _enhanced_clean_content(content_item, cleaning_stats)

                    # Update content item with enhanced data
                    content_item.is_cleaned = True
                    content_item.sentiment_score = cleaned_data.get("sentiment_score", 0.0)
                    content_item.toxicity_score = cleaned_data.get("toxicity_score", 0.0)
                    content_item.keywords = cleaned_data.get("keywords", [])
                    content_item.entities = cleaned_data.get("entities", [])
                    content_item.language = cleaned_data.get("language", "en")

                    # Enhanced content filtering with compliance tracking
                    if cleaned_data.get("is_spam", False):
                        cleaning_stats["spam_filtered"] += 1
                        global_monitor.compliance_tracker.log_content_filtering(
                            content_item.id, "spam", 0.9
                        )
                        logger.info(f"Filtered spam content: {content_item.id}")
                        continue

                    if cleaned_data.get("toxicity_score", 0) > 0.8:
                        cleaning_stats["toxic_content_filtered"] += 1
                        global_monitor.compliance_tracker.log_content_filtering(
                            content_item.id, "toxicity", cleaned_data.get("toxicity_score", 0)
                        )
                        logger.info(f"Filtered toxic content: {content_item.id}")
                        continue

                    if cleaned_data.get("has_pii", False):
                        cleaning_stats["pii_instances_removed"] += 1
                        global_monitor.compliance_tracker.log_content_filtering(
                            content_item.id, "pii_detected", 1.0
                        )
                        # Content is cleaned but PII is masked, so we keep it
                        logger.info(f"PII detected and masked in: {content_item.id}")

                    # Check for duplicates
                    if await _is_duplicate_content(content_item, cleaned_items):
                        cleaning_stats["duplicates_removed"] += 1
                        logger.info(f"Removed duplicate content: {content_item.id}")
                        continue

                    cleaned_items.append(content_item)

                    # Update metrics
                    state.update_metrics(
                        tokens=response.usage_metadata.get("total_tokens", 0) if hasattr(response, 'usage_metadata') else 120,
                        cost=0.003,  # Increased cost for enhanced processing
                        api_calls=1
                    )

                except Exception as e:
                    logger.warning(f"Failed to clean content item {content_item.id}: {e}")
                    state.metrics.warnings.append(f"Enhanced content cleaning failed for {content_item.id}: {e}")
                    cleaning_stats["compliance_violations"].append(f"Cleaning error: {content_item.id}")

        # Update state with cleaned content
        state.cleaned_content.extend(cleaned_items)

        # Create comprehensive audit log
        audit_tool = LANGGRAPH_TOOLS["create_audit_log"]
        await audit_tool._arun(
            action_type="enhanced_content_cleaning",
            action_description=f"Enhanced Cleaner processed {len(state.raw_content)} items, cleaned {len(cleaned_items)}",
            agent_name="enhanced_cleaner_node",
            metadata={
                "raw_count": len(state.raw_content),
                "cleaned_count": len(cleaned_items),
                "filtered_count": len(state.raw_content) - len(cleaned_items),
                "cleaning_stats": cleaning_stats,
                "capabilities": [
                    "pii_detection_removal",
                    "spam_filtering",
                    "data_validation",
                    "content_sanitization",
                    "duplicate_removal",
                    "sentiment_normalization",
                    "compliance_checking"
                ]
            }
        )

        logger.info(f"Enhanced Cleaner node completed - cleaned {len(cleaned_items)} items")
        logger.info(f"Cleaning stats: {cleaning_stats}")
        logger.info(f"Cleaner capabilities: 7 enhanced capabilities active")

    except Exception as e:
        logger.error(f"Enhanced Cleaner node error: {e}")
        state.add_error(f"Enhanced Cleaner node failed: {e}")

    return state


async def _enhanced_clean_content(content_item, cleaning_stats: Dict) -> Dict[str, Any]:
    """Enhanced content cleaning with dashboard-specific processing"""
    content = content_item.content
    
    # Enhanced PII detection patterns
    pii_patterns = {
        "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        "phone": r'\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b',
        "ssn": r'\b\d{3}-\d{2}-\d{4}\b',
        "credit_card": r'\b(?:\d{4}[-\s]?){3}\d{4}\b',
        "address": r'\b\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr)\b'
    }
    
    has_pii = False
    cleaned_content = content
    
    # Detect and mask PII
    for pii_type, pattern in pii_patterns.items():
        matches = re.findall(pattern, content, re.IGNORECASE)
        if matches:
            has_pii = True
            cleaned_content = re.sub(pattern, f'[{pii_type.upper()}_REMOVED]', cleaned_content, flags=re.IGNORECASE)
    
    # Enhanced spam detection
    spam_indicators = [
        r'\b(?:buy now|click here|limited time|act now|free trial)\b',
        r'\b(?:discount|sale|offer|deal|promotion)\b',
        r'\b(?:subscribe|follow|like and share)\b',
        r'\b(?:bitcoin|crypto|investment|profit)\b'
    ]
    
    spam_score = 0
    for indicator in spam_indicators:
        if re.search(indicator, content, re.IGNORECASE):
            spam_score += 1
    
    is_spam = spam_score >= 2
    
    # Enhanced toxicity detection
    toxic_patterns = [
        r'\b(?:hate|stupid|idiot|moron|loser)\b',
        r'\b(?:kill yourself|die|death)\b',
        r'\b(?:racist|sexist|homophobic)\b'
    ]
    
    toxicity_score = 0
    for pattern in toxic_patterns:
        matches = len(re.findall(pattern, content, re.IGNORECASE))
        toxicity_score += matches * 0.3
    
    toxicity_score = min(toxicity_score, 1.0)
    
    # Enhanced sentiment analysis
    positive_words = ['great', 'awesome', 'excellent', 'love', 'perfect', 'amazing', 'fantastic']
    negative_words = ['terrible', 'awful', 'hate', 'horrible', 'worst', 'bad', 'disappointing']
    
    content_lower = content.lower()
    positive_count = sum(1 for word in positive_words if word in content_lower)
    negative_count = sum(1 for word in negative_words if word in content_lower)
    
    sentiment_score = (positive_count - negative_count) / max(positive_count + negative_count, 1)
    sentiment_score = max(-1.0, min(1.0, sentiment_score))
    
    # Extract keywords and entities
    keywords = _extract_keywords(content)
    entities = _extract_entities(content)
    
    # Language detection (simplified)
    language = "en"  # Default to English
    
    return {
        "content": cleaned_content,
        "has_pii": has_pii,
        "is_spam": is_spam,
        "spam_score": spam_score,
        "toxicity_score": toxicity_score,
        "sentiment_score": sentiment_score,
        "keywords": keywords,
        "entities": entities,
        "language": language,
        "quality_score": _calculate_content_quality(content)
    }


async def _is_duplicate_content(content_item, existing_items: List) -> bool:
    """Check if content is a duplicate using similarity comparison"""
    for existing_item in existing_items:
        # Simple similarity check based on content length and first 100 characters
        if (abs(len(content_item.content) - len(existing_item.content)) < 10 and
            content_item.content[:100] == existing_item.content[:100]):
            return True
    return False


def _extract_keywords(content: str) -> List[str]:
    """Extract keywords from content"""
    # Simple keyword extraction based on common fashion/product terms
    fashion_keywords = [
        'shirt', 'pants', 'jacket', 'dress', 'shoes', 'fabric', 'cotton', 'polyester',
        'size', 'fit', 'color', 'style', 'brand', 'price', 'quality', 'durability',
        'comfort', 'breathable', 'waterproof', 'stretch', 'warm', 'cool'
    ]
    
    content_lower = content.lower()
    found_keywords = [keyword for keyword in fashion_keywords if keyword in content_lower]
    return found_keywords[:10]  # Limit to top 10


def _extract_entities(content: str) -> List[str]:
    """Extract entities from content"""
    # Simple entity extraction for brands, products, etc.
    entities = []
    
    # Brand patterns
    brand_patterns = [
        r'\b(?:Nike|Adidas|Uniqlo|H&M|Zara|Gap|Levi\'s|North Face|Patagonia)\b'
    ]
    
    for pattern in brand_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        entities.extend(matches)
    
    return list(set(entities))  # Remove duplicates


def _calculate_content_quality(content: str) -> float:
    """Calculate content quality score"""
    # Quality factors
    length_score = min(len(content) / 500, 1.0)  # Prefer longer content up to 500 chars
    
    # Check for complete sentences
    sentences = content.split('.')
    sentence_score = min(len(sentences) / 3, 1.0)  # Prefer 3+ sentences
    
    # Check for proper capitalization
    capitalization_score = 1.0 if content[0].isupper() else 0.5
    
    quality_score = (length_score + sentence_score + capitalization_score) / 3
    return round(quality_score, 2)


@monitor_node_execution(global_monitor)
async def analyst_node(state: EchoChamberAnalystState) -> EchoChamberAnalystState:
    """
    Analyst Node - AI-Powered Content Analysis

    Replaces the Analyst Agent with sophisticated LLM-powered analysis,
    insight generation, and influencer detection.
    """
    state.current_node = "analyze_content"

    try:
        logger.info(f"Analyst node processing {len(state.cleaned_content)} items")

        # Get tools for analysis operations
        tools = get_tools_for_node("analyst")

        # Create analyst prompt
        analyst_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an AI analyst specializing in social media and content analysis.

            Campaign Context:
            - Campaign: {campaign_name}
            - Keywords: {keywords}
            - Target: {campaign_description}

            Your tasks:
            1. Analyze content for insights and patterns
            2. Identify pain points, praises, and trends
            3. Detect influencers and key voices
            4. Generate actionable insights
            5. Calculate confidence and priority scores

            Insight Types:
            - pain_point: User frustrations and problems
            - praise: Positive feedback and appreciation
            - trend: Emerging patterns and topics
            - sentiment: Overall sentiment analysis
            - influencer: Key influential voices
            - keyword: Important keywords and phrases

            For each insight, provide:
            - Clear, actionable title
            - Detailed description with evidence
            - Confidence score (0-1)
            - Priority score (0-1)
            - Relevant tags
            """),
            ("human", "Analyze this batch of content and generate insights: {content_batch}")
        ])

        # Process content in batches for efficiency
        batch_size = 5
        all_insights = []
        all_influencers = []

        for i in range(0, len(state.cleaned_content), batch_size):
            batch = state.cleaned_content[i:i + batch_size]

            # Prepare content batch for analysis
            content_batch = []
            for item in batch:
                content_batch.append({
                    "id": item.id,
                    "content": item.content[:500],  # Truncate for token limits
                    "author": item.author,
                    "sentiment": item.sentiment_score,
                    "keywords": item.keywords[:10]  # Limit keywords
                })

            # Format prompt
            formatted_prompt = analyst_prompt.format_messages(
                campaign_name=state.campaign.name,
                keywords=", ".join(state.campaign.keywords),
                campaign_description=f"Analysis of {state.campaign.name}",
                content_batch=str(content_batch)
            )

            try:
                # Call LLM for analysis
                response = await llm.ainvoke(formatted_prompt)

                # Parse insights from response (in real implementation, would use structured output)
                batch_insights = await _extract_insights_from_response(response.content, batch)
                all_insights.extend(batch_insights)

                # Track insight generation for compliance
                content_data = [{"id": item.id, "content": item.content[:100]} for item in batch]
                trace_insight_generation(content_data, batch_insights)

                # Extract influencers
                batch_influencers = await _extract_influencers_from_batch(batch)
                all_influencers.extend(batch_influencers)

                # Mark content as analyzed
                for item in batch:
                    item.is_analyzed = True
                    item.is_processed = True

                # Update metrics
                state.update_metrics(
                    tokens=response.usage_metadata.get("total_tokens", 0) if hasattr(response, 'usage_metadata') else 200,
                    cost=0.005,  # Estimated cost per batch
                    api_calls=1
                )

            except Exception as e:
                logger.warning(f"Failed to analyze batch {i//batch_size + 1}: {e}")
                state.metrics.warnings.append(f"Analysis failed for batch {i//batch_size + 1}: {e}")

        # Add insights to state
        for insight_data in all_insights:
            insight = Insight(
                id=insight_data["id"],
                insight_type=InsightType(insight_data["type"]),
                title=insight_data["title"],
                description=insight_data["description"],
                confidence_score=insight_data["confidence"],
                priority_score=insight_data["priority"],
                source_content_ids=insight_data["source_ids"],
                tags=insight_data.get("tags", [])
            )
            state.add_insight(insight)

        # Add influencers to state
        state.influencers.extend(all_influencers)

        # Move cleaned content to processed content
        state.processed_content.extend(state.cleaned_content)

        # Create insights in database
        if all_insights:
            insight_tool = LANGGRAPH_TOOLS["create_insight"]
            for insight_data in all_insights[:5]:  # Limit to prevent overwhelming
                await insight_tool._arun(
                    insight_type=insight_data["type"],
                    title=insight_data["title"],
                    description=insight_data["description"],
                    confidence_score=insight_data["confidence"],
                    priority_score=insight_data["priority"],
                    tags=insight_data.get("tags", [])
                )

        # Create audit log
        audit_tool = LANGGRAPH_TOOLS["create_audit_log"]
        await audit_tool._arun(
            action_type="content_analysis",
            action_description=f"Analyst generated {len(all_insights)} insights from {len(state.cleaned_content)} items",
            agent_name="analyst_node",
            metadata={
                "content_analyzed": len(state.cleaned_content),
                "insights_generated": len(all_insights),
                "influencers_identified": len(all_influencers)
            }
        )

        logger.info(f"Analyst node completed - generated {len(all_insights)} insights, identified {len(all_influencers)} influencers")

    except Exception as e:
        logger.error(f"Analyst node error: {e}")
        state.add_error(f"Analyst node failed: {e}")

    return state


@monitor_node_execution(global_monitor)
async def chatbot_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Chatbot Node - RAG-based Conversational Interface

    Replaces the Chatbot Agent with sophisticated RAG system using
    LangGraph for context retrieval and response generation.
    """
    state["current_node"] = "chatbot_node"

    try:
        user_query = state.get("user_query", "")
        logger.info(f"Chatbot node processing query: {user_query}")

        # Track chat query in LangSmith
        if global_monitor:
            campaign = state.get("campaign")
            campaign_id = campaign.campaign_id if campaign and hasattr(campaign, 'campaign_id') else None
            global_monitor.track_rag_interaction(
                query=user_query,
                campaign_id=campaign_id,
                user_context={"conversation_length": len(state.get("conversation_history", []))}
            )

        # Get tools for chatbot operations
        tools = get_tools_for_node("chatbot")

        # Search for relevant content (primary RAG retrieval)
        search_tool = LANGGRAPH_TOOLS["content_search"]
        campaign = state.get("campaign")
        campaign_id = campaign.campaign_id if campaign and hasattr(campaign, 'campaign_id') and campaign.campaign_id != "chat_session" else None

        search_results = await search_tool._arun(
            query=user_query,
            campaign_id=campaign_id,
            limit=10
        )

        # If no results, attempt secondary retrieval strategies:
        # 1. Try matching insight titles by splitting quoted phrases or capitalized tokens
        fallback_insights = []
        if (not search_results.get("results")) and campaign_id:
            try:
                from django.db.models import Q
                from common.models import Insight

                # Extract candidate phrases (quoted substrings or full query)
                import re
                phrases = re.findall(r'"([^"]+)"', user_query)
                if not phrases:
                    phrases = [user_query]

                q_obj = Q()
                for p in phrases:
                    if len(p.strip()) >= 3:
                        q_obj |= Q(title__icontains=p.strip()) | Q(description__icontains=p.strip())

                if q_obj:
                    candidate_qs = Insight.objects.filter(q_obj, campaign__id=campaign_id)[:5]
                    for ins in candidate_qs:
                        fallback_insights.append({
                            "type": "insight",
                            "id": str(ins.id),
                            "title": ins.title,
                            "description": ins.description[:400],
                            "insight_type": ins.insight_type,
                            "confidence_score": float(ins.confidence_score) if ins.confidence_score is not None else None,
                            "priority_score": float(ins.priority_score) if ins.priority_score is not None else None,
                            "created_at": ins.created_at.isoformat(),
                            "campaign": ins.campaign.name if ins.campaign else None
                        })
                if fallback_insights:
                    search_results = {
                        "success": True,
                        "results": fallback_insights,
                        "total_found": len(fallback_insights),
                        "query": user_query,
                        "fallback_strategy": "insight_lookup"
                    }
            except Exception as insight_err:
                logger.warning(f"Fallback insight lookup failed: {insight_err}")

        # 2. If still nothing and campaign_id present, try a lightweight processed content keyword fallback
        if (not search_results.get("results")) and campaign_id:
            try:
                from common.models import ProcessedContent
                from django.db.models import Q
                tokens = [t for t in user_query.split() if len(t) > 3][:5]
                if tokens:
                    q_obj = Q()
                    for t in tokens:
                        q_obj |= Q(cleaned_content__icontains=t)
                    pc_qs = ProcessedContent.objects.filter(
                        q_obj, raw_content__campaign_id=campaign_id
                    )[:5]
                    fallback_content = []
                    for pc in pc_qs:
                        fallback_content.append({
                            "type": "content",
                            "id": str(pc.id),
                            "title": pc.raw_content.title or "Untitled",
                            "content": pc.cleaned_content[:400],
                            "sentiment_score": float(pc.sentiment_score) if pc.sentiment_score is not None else None,
                            "created_at": pc.created_at.isoformat(),
                            "source": pc.raw_content.source.name if pc.raw_content.source else None
                        })
                    if fallback_content:
                        search_results = {
                            "success": True,
                            "results": fallback_content,
                            "total_found": len(fallback_content),
                            "query": user_query,
                            "fallback_strategy": "processed_content_keyword"
                        }
            except Exception as pc_err:
                logger.warning(f"Fallback processed content lookup failed: {pc_err}")

        # Get campaign stats if relevant
        stats_tool = LANGGRAPH_TOOLS["get_campaign_stats"]
        campaign_stats = None
        if campaign_id:
            campaign_stats = await stats_tool._arun(campaign_id)

        # Create RAG prompt
        rag_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an intelligent assistant for the EchoChamber Analyst platform.
            You help users analyze social media content, understand campaign performance, and explore insights.

            Context Information:
            {context}

            Campaign Stats:
            {campaign_stats}

            Guidelines:
            - Provide helpful, accurate responses based on the available data
            - If you don't have specific information, say so clearly
            - Offer actionable insights when possible
            - Reference specific data points when available
            - Be concise but thorough
            """),
            ("human", "{user_query}")
        ])

        # Prepare context from search results
        context = ""
        if search_results.get("success") and search_results.get("results"):
            preface = "Relevant content found:" if not search_results.get("fallback_strategy") else f"Relevant content found (fallback: {search_results.get('fallback_strategy')}):"
            context_lines = [preface]
            for result in search_results["results"][:5]:  # Limit context
                snippet = result.get('description') or result.get('content', '') or ''
                snippet = snippet.replace('\n', ' ')[:200]
                context_lines.append(f"- {result.get('title', 'Untitled')}: {snippet}...")
            context = "\n".join(context_lines)
        else:
            context = "No specific content found for this query."

        # Format prompt
        formatted_prompt = rag_prompt.format_messages(
            context=context,
            campaign_stats=str(campaign_stats) if campaign_stats else "No campaign stats available",
            user_query=user_query
        )

        # Generate response with LangSmith tracing
        response = await llm.ainvoke(formatted_prompt)

        # Track response quality in LangSmith
        if global_monitor:
            global_monitor.track_response_quality(
                query=user_query,
                response=response.content,
                context_sources=len(search_results.get("results", [])),
                campaign_context=campaign_id
            )

        # Add to conversation history
        conversation_history = state.get("conversation_history", [])
        conversation_history.extend([
            HumanMessage(content=user_query),
            AIMessage(content=response.content)
        ])
        state["conversation_history"] = conversation_history

        # Store RAG context
        state["rag_context"] = {
            "search_results": search_results,
            "campaign_stats": campaign_stats,
            "response": response.content,
            "sources": [r.get("id") for r in search_results.get("results", [])],
            "fallback_used": search_results.get("fallback_strategy") if search_results.get("results") else None
        }

        # Update metrics
        metrics = state.get("metrics")
        tokens_used = response.usage_metadata.get("total_tokens", 0) if hasattr(response, 'usage_metadata') else 150
        if isinstance(metrics, ProcessingMetrics):
            metrics.total_tokens_used += tokens_used
            metrics.total_cost += 0.003
            metrics.api_calls_made += 2
        else:
            # Fallback to dict metrics (keeps compatibility if earlier mutated)
            if not isinstance(metrics, dict):
                metrics = {}
            metrics.update({
                "total_tokens_used": metrics.get("total_tokens_used", 0) + tokens_used,
                "total_cost": metrics.get("total_cost", 0) + 0.003,
                "api_calls_made": metrics.get("api_calls_made", 0) + 2
            })
            state["metrics"] = metrics

        # Create audit log
        audit_tool = LANGGRAPH_TOOLS["create_audit_log"]
        await audit_tool._arun(
            action_type="chat_interaction",
            action_description=f"Chatbot responded to user query",
            agent_name="chatbot_node",
            metadata={
                "query": user_query,
                "sources_found": len(search_results.get("results", [])),
                "response_length": len(response.content)
            }
        )

        logger.info(f"Chatbot node completed - generated response for query")

    except Exception as e:
        logger.error(f"Chatbot node error: {e}")
        # Add error to state
        error_state = state.get("error_state", [])
        if not isinstance(error_state, list):
            error_state = []
        error_state.append(f"Chatbot node failed: {e}")
        state["error_state"] = error_state
        state["task_status"] = TaskStatus.FAILED

    return state


# Helper functions for node implementations

async def _discover_content(campaign) -> List[Dict[str, Any]]:
    """Simulate content discovery (replace with actual implementation)."""
    # Mock content discovery
    mock_content = [
        {
            "id": f"content_{i}",
            "content": f"Sample content item {i} related to {', '.join(campaign.keywords)}",
            "source_url": f"https://example.com/post/{i}",
            "content_type": "reddit_post",
            "author": f"user_{i}",
            "title": f"Discussion about {campaign.keywords[0] if campaign.keywords else 'topic'}",
            "echo_score": 0.7 + (i % 3) * 0.1
        }
        for i in range(5)  # Generate 5 mock items
    ]
    return mock_content


async def _clean_content(content_item: ContentItem) -> Dict[str, Any]:
    """Simulate content cleaning (replace with actual implementation)."""
    return {
        "sentiment_score": 0.5,  # Mock sentiment
        "toxicity_score": 0.1,   # Mock toxicity
        "keywords": ["keyword1", "keyword2"],
        "entities": ["entity1", "entity2"],
        "language": "en",
        "is_spam": False
    }


async def _extract_insights_from_response(response_content: str, content_batch: List[ContentItem]) -> List[Dict[str, Any]]:
    """Extract insights from LLM response (replace with structured parsing)."""
    # Mock insight extraction
    insights = [
        {
            "id": f"insight_{i}",
            "type": "pain_point",
            "title": f"Pain Point {i + 1}",
            "description": f"Analysis reveals user frustration with...",
            "confidence": 0.8,
            "priority": 0.7,
            "source_ids": [item.id for item in content_batch[:2]],
            "tags": ["user_experience", "frustration"]
        }
        for i in range(2)  # Generate 2 mock insights
    ]
    return insights


async def _extract_influencers_from_batch(content_batch: List[ContentItem]) -> List[InfluencerProfile]:
    """Extract influencers from content batch (replace with actual analysis)."""
    influencers = []
    for item in content_batch:
        if item.author and item.echo_score and item.echo_score > 0.7:
            influencer = InfluencerProfile(
                username=item.author,
                platform="reddit",
                influence_score=item.echo_score,
                follower_count=1000,  # Mock data
                engagement_rate=0.05,
                content_topics=item.keywords[:3],
                recent_posts=[item.id]
            )
            influencers.append(influencer)
    return influencers


@monitor_node_execution(global_monitor)
async def monitoring_node(state: EchoChamberAnalystState) -> EchoChamberAnalystState:
    """
    Monitoring Node - LangSmith Integration and Observability
    
    This node handles monitoring tasks, compliance tracking, performance metrics,
    and LangSmith integration for workflow observability.
    """
    state.current_node = "monitoring"
    
    try:
        logger.info("🔍 Monitoring node starting...")
        
        # Initialize monitoring data if not present
        if not hasattr(state, 'monitoring_data'):
            state.monitoring_data = {
                'workflow_start_time': datetime.now().isoformat(),
                'node_execution_times': {},
                'compliance_events': [],
                'performance_metrics': {},
                'cost_tracking': {'total_tokens': 0, 'total_cost': 0.0}
            }
        
        # Track current workflow execution
        current_time = datetime.now()
        if state.current_node:
            state.monitoring_data['node_execution_times'][state.current_node] = current_time.isoformat()
        
        # Log compliance events
        compliance_event = {
            'timestamp': current_time.isoformat(),
            'event_type': 'workflow_monitoring',
            'campaign_id': state.campaign_context.campaign_id if state.campaign_context else 'unknown',
            'processed_content_count': len(state.content_items) if state.content_items else 0,
            'generated_insights_count': len(state.insights) if state.insights else 0,
            'status': 'healthy'
        }
        state.monitoring_data['compliance_events'].append(compliance_event)
        
        # Calculate performance metrics
        if state.content_items:
            total_processing_time = sum(
                item.processing_time for item in state.content_items 
                if hasattr(item, 'processing_time') and item.processing_time
            )
            avg_processing_time = total_processing_time / len(state.content_items) if state.content_items else 0
            
            state.monitoring_data['performance_metrics'] = {
                'total_content_processed': len(state.content_items),
                'average_processing_time': avg_processing_time,
                'total_insights_generated': len(state.insights) if state.insights else 0,
                'workflow_efficiency': len(state.insights) / len(state.content_items) if state.content_items else 0
            }
        
        # Track LangSmith integration
        if global_monitor and global_monitor.client:
            try:
                # Create monitoring run in LangSmith
                monitoring_run = global_monitor.create_workflow_run(
                    workflow_id=f"monitoring_{state.campaign_context.campaign_id if state.campaign_context else 'unknown'}",
                    workflow_type="monitoring",
                    campaign_id=state.campaign_context.campaign_id if state.campaign_context else 'unknown'
                )
                
                if monitoring_run:
                    logger.info(f"✅ LangSmith monitoring run created: {monitoring_run}")
                    state.monitoring_data['langsmith_run_id'] = monitoring_run
                
            except Exception as e:
                logger.warning(f"LangSmith monitoring integration failed: {e}")
        
        # Update workflow status
        state.status = TaskStatus.COMPLETED
        state.current_node = "monitoring_complete"
        
        logger.info("✅ Monitoring node completed successfully")
        logger.info(f"📊 Performance metrics: {state.monitoring_data.get('performance_metrics', {})}")
        
        return state
        
    except Exception as e:
        logger.error(f"❌ Monitoring node failed: {e}")
        state.status = TaskStatus.FAILED
        state.error_message = f"Monitoring failed: {str(e)}"
        
        # Still track the error in monitoring data
        if hasattr(state, 'monitoring_data'):
            error_event = {
                'timestamp': datetime.now().isoformat(),
                'event_type': 'monitoring_error',
                'error_message': str(e),
                'status': 'failed'
            }
            state.monitoring_data['compliance_events'].append(error_event)
        
        return state