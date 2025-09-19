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
from datetime import datetime

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
    Scout Node - Content Discovery and Collection

    Replaces the Scout Agent with LangGraph node that uses tools
    for content discovery, EchoScore calculation, and source management.
    """
    state.current_node = "scout_content"

    try:
        logger.info(f"Scout node processing campaign: {state.campaign.campaign_id}")

        # Get tools for scout operations
        tools = get_tools_for_node("scout")

        # Create scout prompt
        scout_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a content scout agent responsible for discovering and collecting relevant content.

            Campaign Context:
            - Campaign: {campaign_name}
            - Keywords: {keywords}
            - Sources: {sources}
            - Budget Remaining: ${budget_remaining}

            Your tasks:
            1. Analyze the campaign requirements
            2. Determine optimal content sources
            3. Calculate EchoScore for discovered content
            4. Prioritize content based on relevance and quality

            Use the available tools to query databases and create audit logs.
            Focus on finding high-quality, relevant content that matches the campaign keywords.
            """),
            ("human", "Discover and collect content for this campaign. Sources to check: {sources}")
        ])

        # Format the prompt
        formatted_prompt = scout_prompt.format_messages(
            campaign_name=state.campaign.name,
            keywords=", ".join(state.campaign.keywords),
            sources=", ".join(state.campaign.sources),
            budget_remaining=state.campaign.budget_limit - state.campaign.current_spend
        )

        # Simulate content discovery (in real implementation, would use PRAW, BeautifulSoup, etc.)
        discovered_content = await _discover_content(state.campaign)

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

        # Update metrics
        state.update_metrics(
            tokens=len(str(formatted_prompt)) // 4,  # Rough token estimate
            cost=0.001,  # Estimated cost
            api_calls=1
        )

        # Create audit log
        audit_tool = LANGGRAPH_TOOLS["create_audit_log"]
        await audit_tool._arun(
            action_type="content_discovery",
            action_description=f"Scout discovered {len(discovered_content)} content items",
            agent_name="scout_node",
            metadata={
                "campaign_id": state.campaign.campaign_id,
                "content_count": len(discovered_content),
                "sources": state.campaign.sources
            }
        )

        logger.info(f"Scout node completed - discovered {len(discovered_content)} items")

    except Exception as e:
        logger.error(f"Scout node error: {e}")
        state.add_error(f"Scout node failed: {e}")

    return state


@monitor_node_execution(global_monitor)
async def cleaner_node(state: EchoChamberAnalystState) -> EchoChamberAnalystState:
    """
    Data Cleaner Node - Content Cleaning and Validation

    Replaces the Data Cleaner Agent with PII detection, spam filtering,
    and content validation using LLM and specialized tools.
    """
    state.current_node = "clean_content"

    try:
        logger.info(f"Cleaner node processing {len(state.raw_content)} items")

        # Get tools for cleaning operations
        tools = get_tools_for_node("cleaner")

        # Create cleaner prompt
        cleaner_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a data cleaning agent responsible for content validation and cleaning.

            Your tasks:
            1. Detect and mask PII (personally identifiable information)
            2. Filter spam and low-quality content
            3. Detect language and perform sentiment analysis
            4. Extract keywords and entities
            5. Calculate toxicity scores
            6. Validate content quality

            Guidelines:
            - Remove or mask any PII like emails, phone numbers, addresses
            - Filter out spam, promotional content, and bot-generated text
            - Maintain content integrity while ensuring compliance
            - Calculate sentiment scores from -1 (negative) to +1 (positive)
            - Assign toxicity scores from 0 (clean) to 1 (toxic)
            """),
            ("human", "Clean and validate this content: {content}")
        ])

        cleaned_items = []

        for content_item in state.raw_content:
            if not content_item.is_cleaned:
                try:
                    # Format prompt for this content
                    formatted_prompt = cleaner_prompt.format_messages(
                        content=content_item.content[:1000]  # Truncate for token limits
                    )

                    # Call LLM for content analysis
                    response = await llm.ainvoke(formatted_prompt)

                    # Simulate cleaning operations (in real implementation, would use specialized tools)
                    cleaned_data = await _clean_content(content_item)

                    # Update content item
                    content_item.is_cleaned = True
                    content_item.sentiment_score = cleaned_data.get("sentiment_score", 0.0)
                    content_item.toxicity_score = cleaned_data.get("toxicity_score", 0.0)
                    content_item.keywords = cleaned_data.get("keywords", [])
                    content_item.entities = cleaned_data.get("entities", [])
                    content_item.language = cleaned_data.get("language", "en")

                    # Apply content filters with compliance tracking
                    if cleaned_data.get("is_spam", False) or cleaned_data.get("toxicity_score", 0) > 0.8:
                        # Log content filtering for compliance
                        global_monitor.compliance_tracker.log_content_filtering(
                            content_item.id,
                            "spam" if cleaned_data.get("is_spam") else "toxicity",
                            cleaned_data.get("toxicity_score", 0)
                        )
                        logger.info(f"Filtered out content item {content_item.id} (spam/toxic)")
                        continue

                    cleaned_items.append(content_item)

                    # Update metrics
                    state.update_metrics(
                        tokens=response.usage_metadata.get("total_tokens", 0) if hasattr(response, 'usage_metadata') else 100,
                        cost=0.002,  # Estimated cost per item
                        api_calls=1
                    )

                except Exception as e:
                    logger.warning(f"Failed to clean content item {content_item.id}: {e}")
                    state.metrics.warnings.append(f"Content cleaning failed for {content_item.id}: {e}")

        # Update state with cleaned content
        state.cleaned_content.extend(cleaned_items)

        # Create audit log
        audit_tool = LANGGRAPH_TOOLS["create_audit_log"]
        await audit_tool._arun(
            action_type="content_cleaning",
            action_description=f"Cleaner processed {len(state.raw_content)} items, cleaned {len(cleaned_items)}",
            agent_name="cleaner_node",
            metadata={
                "raw_count": len(state.raw_content),
                "cleaned_count": len(cleaned_items),
                "filtered_count": len(state.raw_content) - len(cleaned_items)
            }
        )

        logger.info(f"Cleaner node completed - cleaned {len(cleaned_items)} items")

    except Exception as e:
        logger.error(f"Cleaner node error: {e}")
        state.add_error(f"Cleaner node failed: {e}")

    return state


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