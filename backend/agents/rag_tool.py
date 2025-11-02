"""
RAG Tool - Retrieval-Augmented Generation for Brand Analytics Chatbot.

This module provides pure RAG-based query processing:
- Intent classification to determine search strategy
- Vector embeddings search (semantic similarity)
- Hybrid search (semantic + keyword)
- Context extraction from embeddings
- GPT-4 powered response synthesis
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from openai import AsyncOpenAI
from django.conf import settings

from agents.vector_tools import vector_search_tool, hybrid_search_tool

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
            system_prompt = """You are an intent classification system for a RAG-powered brand analytics chatbot.

Analyze the user's query and extract:
1. **intent_type**: One of:
   - "semantic": Questions about content meaning, themes, sentiment (e.g., "What are people saying about X?")
   - "keyword": Exact keyword/phrase searches (e.g., "Find posts mentioning 'product launch'")
   - "hybrid": Combination of semantic + keyword (default for most queries)

2. **entities**: Extract relevant entities:
   - brand_name: Brand mentioned in query
   - campaign_name: Campaign mentioned in query
   - time_period: Time range (recent, last month, etc.)
   - keywords: Specific keywords to search for
   - content_type: What to search for (threads, pain_points, all)

3. **search_strategy**: Which vector search strategy to use:
   - "vector_search": Pure semantic similarity search across all content types
   - "hybrid_search": Combined semantic + keyword search (USE THIS AS DEFAULT)

4. **confidence**: Confidence score (0-1) in classification

IMPORTANT: This is a RAG-based system. ALL queries should use vector embeddings search.
Do NOT use analytics tools - use "hybrid_search" for all queries by default.

For pain point queries: Use "hybrid_search" to find pain points in the embedded content.
For brand analytics: Use "hybrid_search" to find relevant content about the brand.
For campaign questions: Use "hybrid_search" with campaign_name entity.

Respond in JSON format:
{
    "intent_type": "semantic|keyword|hybrid",
    "entities": {
        "brand_name": "...",
        "campaign_name": "...",
        "time_period": "...",
        "keywords": ["...", "..."],
        "content_type": "threads|pain_points|all"
    },
    "search_strategy": "vector_search|hybrid_search",
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


class RAGTool:
    """
    Main RAG orchestrator using vector embeddings for all queries.

    Workflow:
    1. Classify query intent (semantic, keyword, hybrid)
    2. Route to appropriate vector search strategy
    3. Extract context from embedded content
    4. Generate response using GPT-4 with RAG context
    """

    name = "rag"
    description = (
        "Pure RAG system using vector embeddings to answer questions about "
        "brand analytics, pain points, discussions, and insights from collected data."
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
        min_similarity: float = 0.5,  # Lowered from 0.7 for better recall
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
            search_strategy = classification.get("search_strategy", "hybrid_search")
            content_type = entities.get("content_type", "all")

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

            # Step 2: Execute RAG search (vector embeddings only)
            logger.info(f"Executing RAG search: strategy={search_strategy}, content_type={content_type}")
            
            if search_strategy == "vector_search":
                # Pure vector search across all content types
                search_results = await vector_search_tool.search_all(
                    query=query,
                    brand_id=brand_id,
                    campaign_id=campaign_id,
                    min_similarity=min_similarity,
                    limit_per_type=limit
                )
            else:
                # Hybrid search (default) - semantic + keyword
                search_results = await hybrid_search_tool.search(
                    query=query,
                    brand_id=brand_id,
                    campaign_id=campaign_id,
                    content_type=content_type,
                    min_similarity=min_similarity,
                    limit=limit
                )
            
            # DEBUG: Log search results
            logger.info(f"RAG search completed: success={search_results.get('success')}, results_count={len(search_results.get('results', []))}")
            if not search_results.get('success'):
                logger.error(f"RAG search failed: {search_results.get('error')}")
            
            # Step 3: Format search results for LLM context
            aggregated_data = {
                "query": query,
                "intent": intent_type,
                "entities": entities,
                "search_strategy": search_strategy,
                "results": search_results
            }

            # Extract context from search results
            context_items = []
            
            if search_strategy == "vector_search":
                # Results from vector_search_tool.search_all()
                for content_type_key in ["content", "insights", "pain_points", "threads"]:
                    type_results = search_results.get(content_type_key, {})
                    for item in type_results.get("results", []):
                        # Extract content based on type
                        if content_type_key == "insights":
                            content = f"{item.get('title', '')}\n{item.get('description', '')}"
                        elif content_type_key == "pain_points":
                            content = f"Pain Point: {item.get('keyword', '')}\n{item.get('example_content', '')}"
                        elif content_type_key == "threads":
                            content = f"{item.get('title', '')}\n{item.get('content', '')}"
                        else:
                            content = item.get("content", "")
                        
                        context_items.append({
                            "type": content_type_key,
                            "content": content,
                            "similarity": item.get("similarity_score", item.get("similarity", 0)),
                            "metadata": {
                                "id": item.get("id"),
                                "source": item.get("source", item.get("community_name", "Strategic Report")),
                                "date": item.get("analyzed_at", item.get("created_at", item.get("published_at")))
                            }
                        })
            else:
                # Results from hybrid_search_tool.search()
                for item in search_results.get("results", []):
                    # Extract content based on content_type
                    content_type_val = item.get("content_type", "unknown")
                    
                    if content_type_val == "pain_points":
                        content = f"Pain Point: {item.get('keyword', '')}\nMentions: {item.get('mention_count', 0)}\nHeat Level: {item.get('heat_level', 0)}\nExample: {item.get('example_content', '')}"
                        source = item.get("community_name", "Unknown Community")
                    elif content_type_val == "insights":
                        content = f"{item.get('title', '')}\n{item.get('description', '')}"
                        source = item.get("source", "Strategic Report")
                    elif content_type_val == "threads":
                        content = f"{item.get('title', '')}\n{item.get('content', '')}"
                        source = item.get("community", item.get("community_name", "Unknown"))
                    else:
                        content = item.get("content", "")
                        source = item.get("source", "Unknown")
                    
                    context_items.append({
                        "type": content_type_val,
                        "content": content,
                        "similarity": item.get("similarity_score", item.get("similarity", 0)),
                        "metadata": {
                            "id": item.get("id"),
                            "source": source,
                            "date": item.get("analyzed_at", item.get("created_at", item.get("published_at")))
                        }
                    })

            # Sort by similarity/relevance
            context_items.sort(key=lambda x: x["similarity"], reverse=True)
            
            logger.info(f"Extracted {len(context_items)} context items from RAG search")

            # Step 4: Generate natural language response using RAG context
            response_text = await self._generate_response(
                query=query,
                context_items=context_items,
                aggregated_data=aggregated_data,
                conversation_history=conversation_history
            )

            # Step 5: Extract sources from context
            sources = [
                {
                    "type": item["type"],
                    "content_preview": item["content"][:200] if len(item["content"]) > 200 else item["content"],
                    "similarity_score": round(item["similarity"], 3),
                    "source": item["metadata"]["source"],
                    "date": item["metadata"]["date"]
                }
                for item in context_items[:5]  # Top 5 sources
            ]

            execution_time = (datetime.now() - start_time).total_seconds()

            return {
                "success": True,
                "query": query,
                "answer": response_text,
                "sources": sources,
                "metadata": {
                    "intent_type": intent_type,
                    "confidence": classification.get("confidence", 0.0),
                    "search_strategy": search_strategy,
                    "context_items_count": len(context_items),
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
        context_items: List[Dict[str, Any]],
        aggregated_data: Dict[str, Any],
        conversation_history: List[Dict] = None
    ) -> str:
        """
        Generate natural language response using GPT-4 with RAG context.

        Args:
            query: Original user query
            context_items: Relevant content from vector search
            aggregated_data: Metadata about the search
            conversation_history: Previous conversation context

        Returns:
            Natural language response
        """
        try:
            # Build context from RAG results
            context_parts = []
            
            if not context_items:
                return "I couldn't find any relevant information to answer your question. The data might not be available yet, or you could try rephrasing your query."

            context_parts.append("### Relevant Content from Data Collection:\n")
            
            for idx, item in enumerate(context_items[:10], 1):  # Top 10 most relevant
                content_type = item["type"].replace("_", " ").title()
                similarity = item["similarity"]
                content = item["content"]
                source = item["metadata"]["source"]
                date = item["metadata"]["date"]
                
                context_parts.append(
                    f"{idx}. **{content_type}** (Relevance: {similarity:.2f})\n"
                    f"   Source: {source}\n"
                    f"   Date: {date}\n"
                    f"   Content: {content}\n"
                )

            context = "\n".join(context_parts)

            # Build response generation prompt
            system_prompt = """You are a helpful brand analytics assistant powered by RAG (Retrieval-Augmented Generation). 

Based on the relevant content retrieved from our database, provide a clear, accurate answer to the user's question.

Guidelines:
- Be conversational and helpful
- Synthesize information from multiple sources
- Cite specific examples from the content when relevant
- Organize information logically
- Highlight key insights and patterns
- If the retrieved content doesn't fully answer the question, acknowledge what's available
- Keep responses focused but comprehensive
- Use bullet points for lists when appropriate

IMPORTANT: 
- Only use information from the retrieved content below
- DO NOT make up information or assume facts not present
- If you see pain points, mention the specific keywords/issues
- If you see threads/discussions, summarize the main themes
"""

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
                "content": f"Question: {query}\n\n{context}\n\nPlease answer the question based on the content above."
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


# Singleton instance (kept as hybrid_rag_tool for backward compatibility with existing imports)
hybrid_rag_tool = RAGTool()
