"""
Hybrid RAG Tool - Intent Classification and Multi-Tool Orchestration.

This module provides intelligent query routing and execution:
- Intent classification to determine query type
- Multi-tool parallel execution
- Result aggregation and ranking
- Context-aware response generation
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from openai import AsyncOpenAI
from django.conf import settings

from agents.vector_tools import vector_search_tool, hybrid_search_tool
from agents.dashboard_tools import (
    brand_analytics_tool,
    community_query_tool,
    influencer_query_tool,
    pain_point_analysis_tool,
    campaign_analytics_tool,
    trend_analysis_tool
)

logger = logging.getLogger(__name__)


class IntentClassifier:
    """
    Classify user query intent to route to appropriate tools.

    Intent types:
    - semantic: Natural language, conceptual questions (use vector search)
    - analytics: Structured queries for metrics, KPIs (use dashboard tools)
    - keyword: Exact keyword/phrase searches (use keyword search)
    - hybrid: Combination of semantic + analytics (use multiple tools)
    """

    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def classify(self, query: str, conversation_history: List[Dict] = None) -> Dict[str, Any]:
        """
        Classify query intent using GPT-4.

        Args:
            query: User's natural language query
            conversation_history: Previous conversation context

        Returns:
            Dictionary with intent, entities, and routing information
        """
        try:
            # Build classification prompt
            system_prompt = """You are an intent classification system for a brand analytics chatbot.

Analyze the user's query and extract:
1. **intent_type**: One of:
   - "semantic": Questions about content meaning, themes, sentiment (e.g., "What are people saying about X?")
   - "analytics": Questions about metrics, trends, statistics (e.g., "What's the campaign ROI?")
   - "keyword": Exact keyword/phrase searches (e.g., "Find posts mentioning 'product launch'")
   - "hybrid": Combination of semantic + analytics (e.g., "Show me negative sentiment trends for Campaign X")

2. **entities**: Extract relevant entities:
   - brand_name: Brand mentioned in query
   - campaign_name: Campaign mentioned in query
   - time_period: Time range (7d, 30d, 90d)
   - keywords: Specific keywords to search for
   - metrics: Metrics requested (sentiment, echo_score, ROI, etc.)

3. **tools_needed**: List of tools to use:
   - vector_search: Semantic similarity search
   - hybrid_search: Combined semantic + keyword
   - brand_analytics: Brand KPIs and campaign budgets
   - community_query: Community and echo chamber analysis
   - influencer_query: Influencer metrics
   - pain_point_analysis: Pain points and complaints
   - campaign_analytics: Campaign performance
   - trend_analysis: Temporal trends

4. **confidence**: Confidence score (0-1) in classification

Respond in JSON format:
{
    "intent_type": "semantic|analytics|keyword|hybrid",
    "entities": {
        "brand_name": "...",
        "campaign_name": "...",
        "time_period": "7d|30d|90d",
        "keywords": ["...", "..."],
        "metrics": ["...", "..."]
    },
    "tools_needed": ["tool1", "tool2"],
    "confidence": 0.95,
    "reasoning": "Brief explanation of classification"
}"""

            # Include conversation context
            messages = [{"role": "system", "content": system_prompt}]

            if conversation_history:
                for msg in conversation_history[-3:]:  # Last 3 messages for context
                    messages.append({
                        "role": msg.get("role", "user"),
                        "content": msg.get("content", "")
                    })

            messages.append({"role": "user", "content": query})

            # Call GPT-4 for classification
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",  # Fast and cost-effective for classification
                messages=messages,
                temperature=0.0,  # Deterministic classification
                response_format={"type": "json_object"}
            )

            result = response.choices[0].message.content
            import json
            classification = json.loads(result)

            logger.info(f"Intent classification: {classification['intent_type']} (confidence: {classification['confidence']})")

            return classification

        except Exception as e:
            logger.error(f"Intent classification error: {e}")
            # Fallback to hybrid search
            return {
                "intent_type": "hybrid",
                "entities": {},
                "tools_needed": ["hybrid_search"],
                "confidence": 0.5,
                "reasoning": "Classification failed, defaulting to hybrid search"
            }


class HybridRAGTool:
    """
    Main RAG orchestrator that combines multiple tools for comprehensive answers.

    Workflow:
    1. Classify query intent
    2. Route to appropriate tools
    3. Execute tools in parallel
    4. Aggregate and rank results
    5. Generate natural language response with sources
    """

    name = "hybrid_rag"
    description = (
        "Intelligent RAG system that combines vector search, keyword search, "
        "and analytics tools to answer complex questions about brand analytics, "
        "campaigns, communities, influencers, and pain points."
    )

    def __init__(self):
        self.classifier = IntentClassifier()
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def run(
        self,
        query: str,
        brand_id: Optional[str] = None,
        campaign_id: Optional[str] = None,
        conversation_history: List[Dict] = None,
        min_similarity: float = 0.7,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Execute hybrid RAG query.

        Args:
            query: User's natural language query
            brand_id: Optional brand filter
            campaign_id: Optional campaign filter
            conversation_history: Previous conversation context
            min_similarity: Minimum similarity for vector search
            limit: Maximum results per tool

        Returns:
            Dictionary with answer, sources, and metadata
        """
        try:
            start_time = datetime.now()

            # Step 1: Classify intent
            classification = await self.classifier.classify(query, conversation_history)

            intent_type = classification.get("intent_type", "hybrid")
            entities = classification.get("entities", {})
            tools_needed = classification.get("tools_needed", ["hybrid_search"])

            # Extract entity filters using sync_to_async for database queries
            from asgiref.sync import sync_to_async
            
            if not brand_id and entities.get("brand_name"):
                # Look up brand by name
                from common.models import Brand
                brand = await sync_to_async(Brand.objects.filter(name__icontains=entities["brand_name"]).first)()
                if brand:
                    brand_id = str(brand.id)

            if not campaign_id and entities.get("campaign_name"):
                # Look up campaign by name
                from common.models import Campaign
                campaign_queryset = Campaign.objects.filter(name__icontains=entities["campaign_name"])
                if brand_id:
                    campaign_queryset = campaign_queryset.filter(brand_id=brand_id)
                campaign = await sync_to_async(campaign_queryset.first)()
                if campaign:
                    campaign_id = str(campaign.id)

            # Step 2: Execute tools in parallel
            # Use sync_to_async for database-heavy tools
            from asgiref.sync import sync_to_async
            
            tasks = []
            tool_map = {}

            for tool_name in tools_needed:
                if tool_name == "vector_search":
                    task = vector_search_tool.search_all(
                        query=query,
                        brand_id=brand_id,
                        campaign_id=campaign_id,
                        min_similarity=min_similarity,
                        limit_per_type=5
                    )
                    tasks.append(task)
                    tool_map[len(tasks) - 1] = "vector_search"

                elif tool_name == "hybrid_search":
                    task = hybrid_search_tool.search(
                        query=query,
                        brand_id=brand_id,
                        campaign_id=campaign_id,
                        content_type="all",
                        min_similarity=min_similarity,
                        limit=limit
                    )
                    tasks.append(task)
                    tool_map[len(tasks) - 1] = "hybrid_search"

                elif tool_name == "brand_analytics":
                    task = sync_to_async(brand_analytics_tool.run)(
                        brand_id=brand_id,
                        brand_name=entities.get("brand_name"),
                        include_campaigns=True,
                        include_kpis=True,
                        limit=5
                    )
                    tasks.append(task)
                    tool_map[len(tasks) - 1] = "brand_analytics"

                elif tool_name == "community_query":
                    task = community_query_tool.run(
                        brand_id=brand_id,
                        campaign_id=campaign_id,
                        sort_by="echo_score",
                        limit=limit
                    )
                    tasks.append(task)
                    tool_map[len(tasks) - 1] = "community_query"

                elif tool_name == "influencer_query":
                    task = influencer_query_tool.run(
                        brand_id=brand_id,
                        campaign_id=campaign_id,
                        sort_by="advocacy_score",
                        limit=limit
                    )
                    tasks.append(task)
                    tool_map[len(tasks) - 1] = "influencer_query"

                elif tool_name == "pain_point_analysis":
                    task = pain_point_analysis_tool.run(
                        brand_id=brand_id,
                        campaign_id=campaign_id,
                        sort_by="mention_count",
                        limit=limit
                    )
                    tasks.append(task)
                    tool_map[len(tasks) - 1] = "pain_point_analysis"

                elif tool_name == "campaign_analytics":
                    task = campaign_analytics_tool.run(
                        campaign_id=campaign_id,
                        brand_id=brand_id,
                        sort_by="created_at",
                        limit=limit
                    )
                    tasks.append(task)
                    tool_map[len(tasks) - 1] = "campaign_analytics"

                elif tool_name == "trend_analysis":
                    time_period = entities.get("time_period", "30d")
                    task = trend_analysis_tool.run(
                        brand_id=brand_id,
                        campaign_id=campaign_id,
                        period=time_period,
                        metric_type="all"
                    )
                    tasks.append(task)
                    tool_map[len(tasks) - 1] = "trend_analysis"

            # Execute all tools in parallel
            tool_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Step 3: Aggregate results
            aggregated_data = {
                "query": query,
                "intent": intent_type,
                "entities": entities,
                "tools_executed": [],
                "results": {}
            }

            for idx, result in enumerate(tool_results):
                tool_name = tool_map[idx]
                aggregated_data["tools_executed"].append(tool_name)

                if isinstance(result, Exception):
                    logger.error(f"Tool {tool_name} failed: {result}")
                    aggregated_data["results"][tool_name] = {
                        "success": False,
                        "error": str(result)
                    }
                else:
                    aggregated_data["results"][tool_name] = result

            # Step 4: Generate natural language response
            response_text = await self._generate_response(
                query=query,
                aggregated_data=aggregated_data,
                conversation_history=conversation_history
            )

            # Step 5: Extract sources
            sources = self._extract_sources(aggregated_data)

            execution_time = (datetime.now() - start_time).total_seconds()

            return {
                "success": True,
                "query": query,
                "answer": response_text,
                "sources": sources,
                "metadata": {
                    "intent_type": intent_type,
                    "confidence": classification.get("confidence", 0.0),
                    "tools_executed": aggregated_data["tools_executed"],
                    "execution_time_seconds": round(execution_time, 2),
                    "timestamp": datetime.now().isoformat()
                }
            }

        except Exception as e:
            logger.error(f"Hybrid RAG error: {e}")
            return {
                "success": False,
                "query": query,
                "answer": f"I encountered an error processing your query: {str(e)}",
                "sources": [],
                "metadata": {
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
            }

    async def _generate_response(
        self,
        query: str,
        aggregated_data: Dict[str, Any],
        conversation_history: List[Dict] = None
    ) -> str:
        """
        Generate natural language response using GPT-4 based on aggregated data.

        Args:
            query: Original user query
            aggregated_data: Results from all executed tools
            conversation_history: Previous conversation context

        Returns:
            Natural language response
        """
        try:
            # Build context from tool results
            context_parts = []

            for tool_name, result in aggregated_data["results"].items():
                if not result.get("success", False):
                    continue

                context_parts.append(f"## {tool_name.replace('_', ' ').title()}")
                context_parts.append(f"```json\n{result}\n```\n")

            context = "\n".join(context_parts)

            # Build response generation prompt
            system_prompt = """You are a helpful brand analytics assistant. Based on the data provided from various analytics tools, generate a clear, concise, and informative response to the user's question.

Guidelines:
- Be conversational and helpful
- Cite specific numbers and metrics when available
- Organize information logically
- Highlight key insights
- If data is missing or insufficient, acknowledge it
- Keep responses focused and avoid excessive detail
- Use bullet points for lists
- Include relevant context from the data

DO NOT make up information. Only use data provided in the context."""

            messages = [{"role": "system", "content": system_prompt}]

            # Add conversation history
            if conversation_history:
                for msg in conversation_history[-3:]:
                    messages.append({
                        "role": msg.get("role", "user"),
                        "content": msg.get("content", "")
                    })

            # Add current query and context
            messages.append({
                "role": "user",
                "content": f"Question: {query}\n\nData from analytics tools:\n{context}\n\nPlease provide a comprehensive answer based on this data."
            })

            # Generate response
            response = await self.client.chat.completions.create(
                model="gpt-4o",  # Use GPT-4 for high-quality responses
                messages=messages,
                temperature=0.7,  # Slightly creative but grounded
                max_tokens=1000
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"Response generation error: {e}")
            return "I found some relevant data but encountered an error generating a response. Please try rephrasing your question."

    def _extract_sources(self, aggregated_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract source citations from tool results.

        Args:
            aggregated_data: Results from all executed tools

        Returns:
            List of source citations
        """
        sources = []

        for tool_name, result in aggregated_data["results"].items():
            if not result.get("success", False):
                continue

            # Extract sources based on tool type
            if tool_name == "vector_search":
                # Vector search has content/insights/pain_points
                for content_type in ["content", "insights", "pain_points"]:
                    if content_type in result:
                        for item in result[content_type].get("results", []):
                            sources.append({
                                "id": item.get("id"),
                                "type": content_type,
                                "similarity": item.get("similarity"),
                                "created_at": item.get("created_at"),
                                "preview": self._get_preview(item, content_type)
                            })

            elif tool_name == "hybrid_search":
                for item in result.get("results", []):
                    sources.append({
                        "id": item.get("id"),
                        "type": "content",
                        "match_type": item.get("match_type"),
                        "similarity": item.get("similarity"),
                        "created_at": item.get("created_at"),
                        "preview": item.get("content", "")[:200]
                    })

            elif tool_name == "pain_point_analysis":
                for item in result.get("pain_points", []):
                    sources.append({
                        "id": item.get("id"),
                        "type": "pain_point",
                        "keyword": item.get("keyword"),
                        "severity": item.get("severity"),
                        "mentions": item.get("mentions")
                    })

            elif tool_name == "campaign_analytics":
                for item in result.get("campaigns", []):
                    sources.append({
                        "id": item.get("id"),
                        "type": "campaign",
                        "name": item.get("name"),
                        "status": item.get("status"),
                        "budget": item.get("budget")
                    })

        return sources

    def _get_preview(self, item: Dict[str, Any], content_type: str) -> str:
        """Extract preview text from item based on content type."""
        if content_type == "content":
            return item.get("content", "")[:200]
        elif content_type == "insights":
            return f"{item.get('title', '')}: {item.get('description', '')[:150]}"
        elif content_type == "pain_points":
            return f"{item.get('keyword', '')}: {item.get('example_content', '')[:150]}"
        return ""


# Singleton instance
hybrid_rag_tool = HybridRAGTool()
