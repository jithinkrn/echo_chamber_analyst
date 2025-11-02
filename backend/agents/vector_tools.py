"""
Vector Search Tools for Semantic RAG.

This module provides vector similarity search capabilities using pgvector:
- Semantic search across ProcessedContent, Insights, and PainPoints
- Hybrid search combining vector similarity with keyword matching
- Configurable similarity thresholds and result limits
"""

import logging
from typing import List, Dict, Any, Optional
from django.db.models import Q, F

from common.models import ProcessedContent, Insight, PainPoint
from agents.embedding_service import embedding_service

logger = logging.getLogger(__name__)


class VectorSearchTool:
    """
    Perform semantic similarity search using vector embeddings.

    Use this tool when queries require:
    - Semantic understanding (not just keyword matching)
    - Finding similar content, insights, or pain points
    - Conceptual queries where exact keywords don't appear
    - Natural language questions about content
    """

    name = "vector_search"
    description = (
        "Perform semantic similarity search using vector embeddings. "
        "Returns relevant content, insights, or pain points based on meaning, "
        "not just keyword matches. Use for natural language queries requiring "
        "conceptual understanding."
    )

    async def search_content(
        self,
        query: str,
        brand_id: Optional[str] = None,
        campaign_id: Optional[str] = None,
        min_similarity: float = 0.7,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Search ProcessedContent using vector similarity.

        Args:
            query: Natural language query
            brand_id: Optional brand filter
            campaign_id: Optional campaign filter
            min_similarity: Minimum cosine similarity threshold (0-1)
            limit: Maximum number of results

        Returns:
            Dictionary with search results
        """
        try:
            from asgiref.sync import sync_to_async
            from django.db.models import FloatField, ExpressionWrapper
            from django.db.models.expressions import RawSQL
            
            # Generate query embedding
            query_embedding = await embedding_service.generate_embedding(query)

            # Build queryset with filters
            queryset = ProcessedContent.objects.exclude(embedding__isnull=True)

            if brand_id:
                queryset = queryset.filter(raw_content__campaign__brand_id=brand_id)

            if campaign_id:
                queryset = queryset.filter(raw_content__campaign_id=campaign_id)

            # Perform vector similarity search using pgvector's <=> operator
            # Lower distance = higher similarity
            # We use 1 - distance to get similarity score (0-1)

            # Annotate with similarity score
            queryset = queryset.annotate(
                similarity=ExpressionWrapper(
                    1 - RawSQL(
                        "embedding <=> %s::vector",
                        params=[query_embedding],
                    ),
                    output_field=FloatField()
                )
            ).filter(
                similarity__gte=min_similarity
            ).order_by('-similarity')

            # Execute query in sync context
            results = await sync_to_async(lambda: list(queryset[:limit].values(
                'id', 'cleaned_content', 'sentiment_score',
                'keywords', 'topics', 'created_at',
                'raw_content__url', 'raw_content__title', 
                'raw_content__source__name', 'raw_content__published_at',
                'raw_content__campaign_id', 'raw_content__campaign__brand_id',
                'similarity'
            )))()

            if not results:
                return {
                    "success": False,
                    "message": f"No content found with similarity >= {min_similarity}",
                    "results": []
                }

            formatted_results = [
                {
                    "id": str(r["id"]),
                    "content": r["cleaned_content"][:500],  # Truncate for response
                    "sentiment_score": round(r["sentiment_score"] or 0.0, 2),
                    "keywords": r["keywords"][:5] if r["keywords"] else [],  # Top 5 keywords
                    "topics": r["topics"][:3] if r["topics"] else [],  # Top 3 topics
                    "source": r["raw_content__source__name"],
                    "url": r["raw_content__url"],
                    "title": r["raw_content__title"],
                    "brand_id": str(r["raw_content__campaign__brand_id"]) if r["raw_content__campaign__brand_id"] else None,
                    "campaign_id": str(r["raw_content__campaign_id"]) if r["raw_content__campaign_id"] else None,
                    "published_at": r["raw_content__published_at"].isoformat() if r["raw_content__published_at"] else None,
                    "created_at": r["created_at"].isoformat() if r["created_at"] else None,
                    "similarity_score": round(r["similarity"], 3)
                }
                for r in results
            ]

            return {
                "success": True,
                "query": query,
                "count": len(formatted_results),
                "min_similarity": min_similarity,
                "results": formatted_results
            }

        except Exception as e:
            logger.error(f"Vector search (content) error: {e}")
            return {
                "success": False,
                "error": str(e),
                "results": []
            }

    async def search_insights(
        self,
        query: str,
        brand_id: Optional[str] = None,
        campaign_id: Optional[str] = None,
        insight_type: Optional[str] = None,
        min_similarity: float = 0.3,  # Lower threshold for insights (strategic reports)
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Search Insights using vector similarity.

        Args:
            query: Natural language query
            brand_id: Optional brand filter
            campaign_id: Optional campaign filter
            insight_type: Optional insight type filter
            min_similarity: Minimum cosine similarity threshold
            limit: Maximum number of results

        Returns:
            Dictionary with search results
        """
        try:
            from asgiref.sync import sync_to_async
            from django.db.models import FloatField, ExpressionWrapper
            from django.db.models.expressions import RawSQL
            
            logger.info(f"Searching insights: query='{query[:50]}...', min_similarity={min_similarity}")
            
            query_embedding = await embedding_service.generate_embedding(query)

            queryset = Insight.objects.exclude(embedding__isnull=True)
            
            logger.info(f"Found {await sync_to_async(queryset.count)()} insights with embeddings")

            # Note: Insight model doesn't have direct brand_id field
            # Brand association is through campaign relationship
            if brand_id:
                queryset = queryset.filter(campaign__brand_id=brand_id)

            if campaign_id:
                queryset = queryset.filter(campaign_id=campaign_id)

            if insight_type:
                queryset = queryset.filter(insight_type=insight_type)

            queryset = queryset.annotate(
                similarity=ExpressionWrapper(
                    1 - RawSQL(
                        "embedding <=> %s::vector",
                        params=[query_embedding],
                    ),
                    output_field=FloatField()
                )
            ).filter(
                similarity__gte=min_similarity
            ).order_by('-similarity')

            # Execute query in sync context
            results = await sync_to_async(lambda: list(queryset[:limit].values(
                'id', 'title', 'description', 'insight_type',
                'confidence_score', 'impact_score', 'priority_score',
                'campaign_id', 'created_at', 'similarity'
            )))()

            logger.info(f"Insight vector search: found {len(results)} results with min_similarity={min_similarity}")

            if not results:
                return {
                    "success": False,
                    "message": f"No insights found with similarity >= {min_similarity}",
                    "results": []
                }

            formatted_results = [
                {
                    "id": str(r["id"]),
                    "title": r["title"],
                    "description": r["description"],
                    "insight_type": r["insight_type"],
                    "confidence_score": round(r["confidence_score"] or 0.0, 2),
                    "impact_score": round(r["impact_score"] or 0.0, 2),
                    "priority_score": round(r["priority_score"] or 0.0, 2),
                    "campaign_id": str(r["campaign_id"]) if r["campaign_id"] else None,
                    "created_at": r["created_at"].isoformat() if r["created_at"] else None,
                    "similarity_score": round(r["similarity"], 3)
                }
                for r in results
            ]

            return {
                "success": True,
                "query": query,
                "count": len(formatted_results),
                "min_similarity": min_similarity,
                "results": formatted_results
            }

        except Exception as e:
            logger.error(f"Vector search (insights) error: {e}")
            return {
                "success": False,
                "error": str(e),
                "results": []
            }

    async def search_pain_points(
        self,
        query: str,
        brand_id: Optional[str] = None,
        campaign_id: Optional[str] = None,
        min_severity: Optional[int] = None,
        min_similarity: float = 0.7,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Search PainPoints using vector similarity.

        Args:
            query: Natural language query
            brand_id: Optional brand filter
            campaign_id: Optional campaign filter
            min_severity: Minimum severity level (1-5)
            min_similarity: Minimum cosine similarity threshold
            limit: Maximum number of results

        Returns:
            Dictionary with search results
        """
        try:
            from asgiref.sync import sync_to_async
            from django.db.models import FloatField, ExpressionWrapper
            from django.db.models.expressions import RawSQL
            
            logger.info(f"Searching pain points: query='{query[:50]}...', min_similarity={min_similarity}")
            
            query_embedding = await embedding_service.generate_embedding(query)

            queryset = PainPoint.objects.exclude(embedding__isnull=True)
            
            logger.info(f"Found {await sync_to_async(queryset.count)()} pain points with embeddings")

            if brand_id:
                queryset = queryset.filter(brand_id=brand_id)

            if campaign_id:
                queryset = queryset.filter(campaign_id=campaign_id)

            if min_severity is not None:
                queryset = queryset.filter(severity__gte=min_severity)

            queryset = queryset.annotate(
                similarity=ExpressionWrapper(
                    1 - RawSQL(
                        "embedding <=> %s::vector",
                        params=[query_embedding],
                    ),
                    output_field=FloatField()
                )
            ).filter(
                similarity__gte=min_similarity
            ).order_by('-similarity')

            # Execute query in sync context
            results = await sync_to_async(lambda: list(queryset[:limit].values(
                'id', 'keyword', 'mention_count',
                'heat_level', 'growth_percentage',
                'example_content', 'related_keywords', 'sentiment_score',
                'brand_id', 'campaign_id', 'community__name',
                'created_at', 'similarity'
            )))()

            logger.info(f"Pain point vector search: found {len(results)} results with min_similarity={min_similarity}")
            
            if not results:
                return {
                    "success": False,
                    "message": f"No pain points found with similarity >= {min_similarity}",
                    "results": []
                }

            formatted_results = [
                {
                    "id": str(r["id"]),
                    "keyword": r["keyword"],
                    "mention_count": r["mention_count"] or 0,
                    "heat_level": r["heat_level"] or 0,
                    "growth_percentage": round(r["growth_percentage"] or 0.0, 2),
                    "sentiment_score": round(r["sentiment_score"] or 0.0, 2),
                    "example_content": r["example_content"][:300] if r["example_content"] else None,
                    "related_keywords": r["related_keywords"][:5] if r["related_keywords"] else [],
                    "community_name": r["community__name"],
                    "brand_id": str(r["brand_id"]) if r["brand_id"] else None,
                    "campaign_id": str(r["campaign_id"]) if r["campaign_id"] else None,
                    "created_at": r["created_at"].isoformat() if r["created_at"] else None,
                    "similarity_score": round(r["similarity"], 3)
                }
                for r in results
            ]

            return {
                "success": True,
                "query": query,
                "count": len(formatted_results),
                "min_similarity": min_similarity,
                "results": formatted_results
            }

        except Exception as e:
            logger.error(f"Vector search (pain points) error: {e}")
            return {
                "success": False,
                "error": str(e),
                "results": []
            }

    async def search_threads(
        self,
        query: str,
        brand_id: Optional[str] = None,
        campaign_id: Optional[str] = None,
        community_name: Optional[str] = None,
        min_similarity: float = 0.7,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Search Threads using vector similarity.

        Args:
            query: Natural language query
            brand_id: Optional brand filter
            campaign_id: Optional campaign filter
            community_name: Optional community name filter
            min_similarity: Minimum cosine similarity threshold
            limit: Maximum number of results

        Returns:
            Dictionary with search results
        """
        try:
            from asgiref.sync import sync_to_async
            from django.db.models import FloatField, ExpressionWrapper
            from django.db.models.expressions import RawSQL
            from common.models import Thread
            
            query_embedding = await embedding_service.generate_embedding(query)

            queryset = Thread.objects.exclude(embedding__isnull=True)

            if brand_id:
                queryset = queryset.filter(brand_id=brand_id)

            if campaign_id:
                queryset = queryset.filter(campaign_id=campaign_id)

            if community_name:
                queryset = queryset.filter(community__name__icontains=community_name)

            queryset = queryset.annotate(
                similarity=ExpressionWrapper(
                    1 - RawSQL(
                        "embedding <=> %s::vector",
                        params=[query_embedding],
                    ),
                    output_field=FloatField()
                )
            ).filter(
                similarity__gte=min_similarity
            ).order_by('-similarity').select_related('community', 'campaign')

            # Execute query in sync context
            results = await sync_to_async(lambda: list(queryset[:limit].values(
                'id', 'thread_id', 'title', 'content', 'url',
                'author', 'comment_count', 'upvotes',
                'echo_score', 'sentiment_score', 'published_at',
                'community__name', 'brand_id', 'campaign_id',
                'similarity'
            )))()

            if not results:
                return {
                    "success": False,
                    "message": f"No threads found with similarity >= {min_similarity}",
                    "results": []
                }

            formatted_results = [
                {
                    "id": str(r["id"]),
                    "thread_id": r["thread_id"],
                    "title": r["title"],
                    "content": r["content"][:500] if r["content"] else None,  # Truncate
                    "url": r["url"],
                    "author": r["author"],
                    "community": r["community__name"],
                    "comment_count": r["comment_count"] or 0,
                    "upvotes": r["upvotes"] or 0,
                    "echo_score": round(r["echo_score"] or 0.0, 2),
                    "sentiment_score": round(r["sentiment_score"] or 0.0, 2),
                    "published_at": r["published_at"].isoformat() if r["published_at"] else None,
                    "brand_id": str(r["brand_id"]) if r["brand_id"] else None,
                    "campaign_id": str(r["campaign_id"]) if r["campaign_id"] else None,
                    "similarity": round(r["similarity"], 3)
                }
                for r in results
            ]

            return {
                "success": True,
                "query": query,
                "count": len(formatted_results),
                "min_similarity": min_similarity,
                "results": formatted_results
            }

        except Exception as e:
            logger.error(f"Vector search (threads) error: {e}")
            return {
                "success": False,
                "error": str(e),
                "results": []
            }

    async def search_all(
        self,
        query: str,
        brand_id: Optional[str] = None,
        campaign_id: Optional[str] = None,
        min_similarity: float = 0.7,
        limit_per_type: int = 5
    ) -> Dict[str, Any]:
        """
        Search across all content types (ProcessedContent, Insights, PainPoints, Threads).

        Args:
            query: Natural language query
            brand_id: Optional brand filter
            campaign_id: Optional campaign filter
            min_similarity: Minimum cosine similarity threshold
            limit_per_type: Maximum results per content type

        Returns:
            Dictionary with results from all content types
        """
        try:
            # Search all types in parallel
            import asyncio

            content_task = self.search_content(
                query=query,
                brand_id=brand_id,
                campaign_id=campaign_id,
                min_similarity=min_similarity,
                limit=limit_per_type
            )

            # Use lower threshold for insights (strategic reports need more lenient matching)
            insights_task = self.search_insights(
                query=query,
                brand_id=brand_id,
                campaign_id=campaign_id,
                min_similarity=0.3,  # Lower threshold for strategic reports
                limit=limit_per_type
            )

            pain_points_task = self.search_pain_points(
                query=query,
                brand_id=brand_id,
                campaign_id=campaign_id,
                min_similarity=min_similarity,
                limit=limit_per_type
            )

            threads_task = self.search_threads(
                query=query,
                brand_id=brand_id,
                campaign_id=campaign_id,
                min_similarity=min_similarity,
                limit=limit_per_type
            )

            content_results, insights_results, pain_points_results, threads_results = await asyncio.gather(
                content_task, insights_task, pain_points_task, threads_task
            )

            total_count = (
                len(content_results.get("results", [])) +
                len(insights_results.get("results", [])) +
                len(pain_points_results.get("results", [])) +
                len(threads_results.get("results", []))
            )

            return {
                "success": True,
                "query": query,
                "total_count": total_count,
                "min_similarity": min_similarity,
                "content": content_results,
                "insights": insights_results,
                "pain_points": pain_points_results,
                "threads": threads_results
            }

        except Exception as e:
            logger.error(f"Vector search (all) error: {e}")
            return {
                "success": False,
                "error": str(e),
                "content": {"results": []},
                "insights": {"results": []},
                "pain_points": {"results": []},
                "threads": {"results": []}
            }


class HybridSearchTool:
    """
    Pure vector-based semantic search across multiple content types.
    
    Despite the name "hybrid", this tool now performs ONLY vector similarity search
    to maintain RAG purity. No direct database queries or keyword matching.
    Use for comprehensive semantic search across content, insights, pain points, and threads.
    """

    name = "hybrid_search"
    description = (
        "Pure vector similarity search across multiple content types. "
        "Returns semantically relevant results based on embeddings only. "
        "No direct database queries - fully RAG-powered."
    )

    def __init__(self):
        self.vector_tool = VectorSearchTool()

    async def search(
        self,
        query: str,
        brand_id: Optional[str] = None,
        campaign_id: Optional[str] = None,
        content_type: str = "all",  # all, content, insights, pain_points, threads
        min_similarity: float = 0.7,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Perform pure vector semantic search across specified content types.

        Args:
            query: Natural language query
            brand_id: Optional brand filter
            campaign_id: Optional campaign filter
            content_type: Type of content to search (all, content, insights, pain_points, threads)
            min_similarity: Minimum similarity for vector search
            limit: Maximum total results

        Returns:
            Dictionary with vector search results only
        """
        try:
            # Pure vector search - NO keyword matching, NO direct DB queries
            if content_type == "all":
                # Search across all content types using vector embeddings only
                search_results = await self.vector_tool.search_all(
                    query=query,
                    brand_id=brand_id,
                    campaign_id=campaign_id,
                    min_similarity=min_similarity,
                    limit_per_type=limit
                )
                
                # Flatten results from all types
                all_results = []
                for type_key in ["content", "insights", "pain_points", "threads"]:
                    type_results = search_results.get(type_key, {})
                    for item in type_results.get("results", []):
                        item["content_type"] = type_key
                        item["match_type"] = "semantic"
                        all_results.append(item)
                
                # Sort by similarity score
                all_results.sort(key=lambda x: x.get("similarity", 0), reverse=True)
                
                return {
                    "success": True,
                    "query": query,
                    "count": len(all_results[:limit]),
                    "results": all_results[:limit]
                }

            elif content_type == "content":
                # Vector search for ProcessedContent only
                vector_results = await self.vector_tool.search_content(
                    query=query,
                    brand_id=brand_id,
                    campaign_id=campaign_id,
                    min_similarity=min_similarity,
                    limit=limit
                )
                
                # Mark all as semantic matches
                for r in vector_results.get("results", []):
                    r["match_type"] = "semantic"
                    r["content_type"] = "content"
                
                return vector_results

            elif content_type == "insights":
                # Vector search for Insights only
                vector_results = await self.vector_tool.search_insights(
                    query=query,
                    brand_id=brand_id,
                    campaign_id=campaign_id,
                    min_similarity=min_similarity,
                    limit=limit
                )
                
                # Mark all as semantic matches
                for r in vector_results.get("results", []):
                    r["match_type"] = "semantic"
                    r["content_type"] = "insights"
                
                return vector_results

            elif content_type == "pain_points":
                # Vector search for PainPoints only
                vector_results = await self.vector_tool.search_pain_points(
                    query=query,
                    brand_id=brand_id,
                    campaign_id=campaign_id,
                    min_similarity=min_similarity,
                    limit=limit
                )
                
                # Mark all as semantic matches
                for r in vector_results.get("results", []):
                    r["match_type"] = "semantic"
                    r["content_type"] = "pain_points"
                
                return vector_results

            elif content_type == "threads":
                # Vector search for Threads only
                vector_results = await self.vector_tool.search_threads(
                    query=query,
                    brand_id=brand_id,
                    campaign_id=campaign_id,
                    min_similarity=min_similarity,
                    limit=limit
                )
                
                # Mark all as semantic matches
                for r in vector_results.get("results", []):
                    r["match_type"] = "semantic"
                    r["content_type"] = "threads"
                
                return vector_results

            else:
                # Default to search_all for any unrecognized content_type
                return await self.vector_tool.search_all(
                    query=query,
                    brand_id=brand_id,
                    campaign_id=campaign_id,
                    min_similarity=min_similarity,
                    limit_per_type=limit
                )

        except Exception as e:
            logger.error(f"Hybrid search error: {e}")
            return {
                "success": False,
                "error": str(e),
                "results": []
            }


# Tool instances for easy import
vector_search_tool = VectorSearchTool()
hybrid_search_tool = HybridSearchTool()
