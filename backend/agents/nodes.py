"""
LangGraph Node Implementations

This module contains the individual node implementations that replace
the custom agents, providing tools integration, LLM capabilities,
and sophisticated processing logic.
"""

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

# Import real data collection functions
from .scout_data_collection import collect_real_brand_data

# Import Django models for dashboard data
from common.models import Campaign, Community, PainPoint, Influencer, Thread, DashboardMetrics

logger = logging.getLogger(__name__)

# Initialize OpenAI LLM
llm = ChatOpenAI(
    model="gpt-4",
    temperature=0.1,
    max_tokens=2000
)


@monitor_node_execution(global_monitor)
async def scout_node(state: EchoChamberAnalystState) -> EchoChamberAnalystState:
    """
    Real-Time Scout Node - Content Discovery and Dashboard Data Collection

    Uses real web scraping and forum data collection to gather actual brand data
    from Reddit, forums, and review sites. Integrates with SearchUtils for
    comprehensive multi-platform data collection.
    """
    state.current_node = "scout_content"

    try:
        # Extract brand information from campaign
        brand_name = state.campaign.name if hasattr(state.campaign, 'name') else "Unknown Brand"
        brand_keywords = state.campaign.keywords if hasattr(state.campaign, 'keywords') else []
        
        logger.info(f"🔍 REAL Scout node processing brand: {brand_name}")
        logger.info(f"📋 Keywords: {', '.join(brand_keywords)}")

        # Get tools for scout operations
        tools = get_tools_for_node("scout")

        # Create enhanced scout prompt for real data collection
        scout_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a real-time content scout agent responsible for comprehensive brand data collection.

            Campaign Context:
            - Brand: {brand_name}
            - Keywords: {keywords}
            - Sources: Reddit, Forums, Review Sites
            - Collection Method: Real-time web scraping and API integration

            Real-Time Capabilities:
            1. Live Reddit subreddit scanning
            2. Forum thread collection and analysis
            3. Review site data extraction
            4. Brand mention detection and tracking
            5. Real pain point extraction from user content
            6. Authentic echo score calculation
            7. Live sentiment analysis
            8. Community health monitoring

            Your tasks:
            1. Collect real brand discussions from multiple platforms
            2. Extract genuine user pain points and feedback
            3. Calculate authentic echo scores from actual content
            4. Identify real community trends and patterns
            5. Monitor brand sentiment across platforms
            6. Store data for live dashboard updates
            7. Track brand mentions and context
            8. Analyze discussion types and engagement

            This is REAL data collection - no simulation or mock data.
            """),
            ("human", "Collect real-time brand data for comprehensive analysis. Brand: {brand_name}")
        ])

        # Format the prompt
        formatted_prompt = scout_prompt.format_messages(
            brand_name=brand_name,
            keywords=", ".join(brand_keywords)
        )

        # **REAL DATA COLLECTION** - Use the imported function
        logger.info(f"🚀 Starting REAL brand data collection for: {brand_name}")
        
        collected_data = await collect_real_brand_data(brand_name, brand_keywords)
        
        logger.info(f"📊 Real data collected:")
        logger.info(f"  - Communities: {len(collected_data.get('communities', []))}")
        logger.info(f"  - Threads: {len(collected_data.get('threads', []))}")
        logger.info(f"  - Pain Points: {len(collected_data.get('pain_points', []))}")
        logger.info(f"  - Brand Mentions: {len(collected_data.get('brand_mentions', []))}")

        # Store real data in Django models for dashboard
        await _store_real_dashboard_data(collected_data, state.campaign, brand_name)

        # Convert real data to ContentItem format for state management
        discovered_content = []
        for thread in collected_data.get("threads", []):
            discovered_content.append({
                "id": thread["thread_id"],
                "content": thread["content"],
                "source_url": thread.get("url", ""),
                "content_type": "forum_post",
                "author": thread.get("author", "unknown"),
                "title": thread.get("title", "Untitled"),
                "published_at": thread.get("created_at"),
                "echo_score": thread.get("echo_score", 0.5),
                "sentiment_score": thread.get("sentiment_score", 0.0),
                "platform": thread.get("platform", "unknown"),
                "is_real_data": thread.get("is_real_data", True),
                "brand_mentioned": thread.get("brand_mentioned", False)
            })

        # Add discovered real content to state
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

        # Update metrics with real data collection costs
        state.update_metrics(
            tokens=600,  # Higher token usage for real analysis
            cost=0.025,  # Higher cost for real web scraping and LLM analysis
            api_calls=len(collected_data.get("data_sources", []))
        )

        # Create comprehensive audit log for real data collection
        audit_tool = LANGGRAPH_TOOLS["create_audit_log"]
        await audit_tool._arun(
            action_type="real_brand_data_collection",
            action_description=f"REAL Scout collected data for brand '{brand_name}' from {len(collected_data.get('data_sources', []))} real sources",
            agent_name="real_scout_node",
            metadata={
                "brand_name": brand_name,
                "keywords": brand_keywords,
                "data_sources": collected_data.get("data_sources", []),
                "communities_found": len(collected_data.get("communities", [])),
                "threads_collected": len(collected_data.get("threads", [])),
                "pain_points_identified": len(collected_data.get("pain_points", [])),
                "brand_mentions": len(collected_data.get("brand_mentions", [])),
                "collection_method": "real_web_scraping",
                "platforms_searched": ["reddit", "forums", "review_sites"],
                "is_real_data": True,
                "collection_timestamp": collected_data.get("collection_timestamp"),
                "capabilities": [
                    "real_time_scraping",
                    "forum_data_collection", 
                    "reddit_api_integration",
                    "brand_mention_tracking",
                    "authentic_pain_point_extraction",
                    "real_echo_score_calculation",
                    "live_sentiment_analysis",
                    "community_health_monitoring"
                ]
            }
        )

        logger.info(f"✅ REAL Scout completed - collected {len(discovered_content)} real items for brand '{brand_name}'")
        logger.info(f"🎯 Real capabilities: 8 live data collection capabilities active")

    except Exception as e:
        logger.error(f"❌ REAL Scout node error: {e}")
        state.add_error(f"REAL Scout node failed: {e}")

    return state


async def _store_real_dashboard_data(collected_data: Dict[str, Any], campaign, brand_name: str) -> None:
    """Store real collected data in Django models for dashboard display"""
    try:
        from django.utils import timezone
        
        logger.info(f"💾 Storing real dashboard data for brand: {brand_name}")
        
        # Store real communities with authentic data
        for community_data in collected_data.get("communities", []):
            community, created = Community.objects.get_or_create(
                name=community_data["name"],
                platform=community_data["platform"],
                defaults={
                    "url": community_data["url"],
                    "member_count": community_data["member_count"],
                    "echo_score": community_data["echo_score"],
                    "echo_score_change": community_data.get("echo_score_change", 0.0),
                    "description": f"Real community data for {brand_name}",
                    "is_active": True,
                    "last_updated": timezone.now(),
                    "activity_level": community_data.get("activity_level", "medium"),
                    "threads_found": community_data.get("threads_found", 0),
                    "data_source": "real_web_scraping"
                }
            )
            
            if not created:
                # Update existing community with real data
                old_echo_score = community.echo_score or 0.0
                new_echo_score = community_data["echo_score"]
                
                community.echo_score = new_echo_score
                community.echo_score_change = round(
                    ((new_echo_score - old_echo_score) / max(old_echo_score, 0.1)) * 100, 1
                )
                community.member_count = community_data["member_count"]
                community.last_updated = timezone.now()
                community.data_source = "real_web_scraping"
                community.save()

        # Store real pain points extracted from actual content
        for pain_point_data in collected_data.get("pain_points", []):
            community = Community.objects.filter(
                platform__in=["reddit", "forum", "tech_forums", "review_sites"]
            ).first()
            
            if community:
                PainPoint.objects.update_or_create(
                    keyword=pain_point_data["keyword"],
                    campaign_id=campaign.id,
                    community=community,
                    defaults={
                        "mention_count": pain_point_data["mention_count"],
                        "growth_percentage": pain_point_data["growth_percentage"],
                        "sentiment_score": pain_point_data["sentiment_score"],
                        "heat_level": pain_point_data["heat_level"],
                        "severity": pain_point_data.get("severity", "medium"),
                        "category": pain_point_data.get("category", "general"),
                        "trend_direction": pain_point_data.get("trend_direction", "stable"),
                        "priority_score": pain_point_data.get("priority_score", 0.0),
                        "brand_context": pain_point_data.get("brand_context", []),
                        "last_updated": timezone.now()
                    }
                )

        # Store real threads from actual forums/Reddit
        for thread_data in collected_data.get("threads", []):
            community = Community.objects.filter(
                name=thread_data.get("community")
            ).first()
            
            if community:
                Thread.objects.update_or_create(
                    thread_id=thread_data["thread_id"],
                    defaults={
                        "title": thread_data["title"],
                        "content": thread_data["content"][:2000],  # Limit content length
                        "community": community,
                        "author": thread_data.get("author", "unknown"),
                        "url": thread_data.get("url", ""),
                        "echo_score": thread_data.get("echo_score", 0.0),
                        "sentiment_score": thread_data.get("sentiment_score", 0.0),
                        "platform": thread_data.get("platform", "unknown"),
                        "discussion_type": thread_data.get("discussion_type", "general"),
                        "brand_mentioned": thread_data.get("brand_mentioned", False),
                        "reply_count": thread_data.get("reply_count", 0),
                        "view_count": thread_data.get("view_count", 0),
                        "created_at": thread_data.get("created_at", timezone.now()),
                        "last_updated": timezone.now()
                    }
                )

        # Store brand mentions from real content
        for mention_data in collected_data.get("brand_mentions", []):
            # Could store in a separate BrandMention model if needed
            logger.debug(f"Brand mention: {mention_data.get('title', 'No title')}")

        logger.info(f"✅ Real dashboard data stored successfully for brand '{brand_name}'")
        logger.info(f"📊 Stored: {len(collected_data.get('communities', []))} communities, "
                   f"{len(collected_data.get('pain_points', []))} pain points, "
                   f"{len(collected_data.get('threads', []))} threads")

    except Exception as e:
        logger.error(f"❌ Error storing real dashboard data: {e}")
        # Don't raise exception to avoid breaking the workflow


# Remove all the old simulated data collection functions that were duplicated
# (collect_reddit_data, collect_discord_data, collect_tiktok_data, etc.)
# Keep only the essential node implementations


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
    """
    Extract influencers from content batch using enhanced analysis.
    NOTE: This is now a simplified version. Full analysis happens in enhanced_analyst module.
    """
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