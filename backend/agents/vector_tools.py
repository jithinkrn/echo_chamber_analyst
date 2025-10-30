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
            # Generate query embedding
            query_embedding = await embedding_service.generate_embedding(query)

            # Build queryset with filters
            queryset = ProcessedContent.objects.exclude(embedding__isnull=True)

            if brand_id:
                queryset = queryset.filter(brand_id=brand_id)

            if campaign_id:
                queryset = queryset.filter(campaign_id=campaign_id)

            # Perform vector similarity search using pgvector's <=> operator
            # Lower distance = higher similarity
            # We use 1 - distance to get similarity score (0-1)
            from django.db.models import FloatField, ExpressionWrapper
            from django.db.models.expressions import RawSQL

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

            results = list(queryset[:limit].values(
                'id', 'content_type', 'original_content', 'cleaned_content',
                'sentiment', 'sentiment_score', 'echo_score',
                'source', 'brand_id', 'campaign_id', 'created_at',
                'similarity'
            ))

            if not results:
                return {
                    "success": False,
                    "message": f"No content found with similarity >= {min_similarity}",
                    "results": []
                }

            formatted_results = [
                {
                    "id": str(r["id"]),
                    "content_type": r["content_type"],
                    "content": r["cleaned_content"][:500],  # Truncate for response
                    "sentiment": r["sentiment"],
                    "sentiment_score": round(r["sentiment_score"] or 0.0, 2),
                    "echo_score": round(r["echo_score"] or 0.0, 2),
                    "source": r["source"],
                    "brand_id": str(r["brand_id"]) if r["brand_id"] else None,
                    "campaign_id": str(r["campaign_id"]) if r["campaign_id"] else None,
                    "created_at": r["created_at"].isoformat() if r["created_at"] else None,
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
        min_similarity: float = 0.7,
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
            query_embedding = await embedding_service.generate_embedding(query)

            queryset = Insight.objects.exclude(embedding__isnull=True)

            if brand_id:
                queryset = queryset.filter(brand_id=brand_id)

            if campaign_id:
                queryset = queryset.filter(campaign_id=campaign_id)

            if insight_type:
                queryset = queryset.filter(insight_type=insight_type)

            from django.db.models import FloatField, ExpressionWrapper
            from django.db.models.expressions import RawSQL

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

            results = list(queryset[:limit].values(
                'id', 'title', 'description', 'insight_type',
                'severity', 'confidence_score', 'brand_id',
                'campaign_id', 'created_at', 'similarity'
            ))

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
                    "description": r["description"][:500],
                    "insight_type": r["insight_type"],
                    "severity": r["severity"],
                    "confidence_score": round(r["confidence_score"] or 0.0, 2),
                    "brand_id": str(r["brand_id"]) if r["brand_id"] else None,
                    "campaign_id": str(r["campaign_id"]) if r["campaign_id"] else None,
                    "created_at": r["created_at"].isoformat() if r["created_at"] else None,
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
            query_embedding = await embedding_service.generate_embedding(query)

            queryset = PainPoint.objects.exclude(embedding__isnull=True)

            if brand_id:
                queryset = queryset.filter(brand_id=brand_id)

            if campaign_id:
                queryset = queryset.filter(campaign_id=campaign_id)

            if min_severity is not None:
                queryset = queryset.filter(severity__gte=min_severity)

            from django.db.models import FloatField, ExpressionWrapper
            from django.db.models.expressions import RawSQL

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

            results = list(queryset[:limit].values(
                'id', 'keyword', 'category', 'mentions',
                'severity', 'growth_rate', 'growth_trend',
                'example_content', 'brand_id', 'campaign_id',
                'created_at', 'similarity'
            ))

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
                    "category": r["category"],
                    "mentions": r["mentions"] or 0,
                    "severity": r["severity"] or 0,
                    "growth_rate": round(r["growth_rate"] or 0.0, 2),
                    "growth_trend": r["growth_trend"],
                    "example_content": r["example_content"][:200] if r["example_content"] else None,
                    "brand_id": str(r["brand_id"]) if r["brand_id"] else None,
                    "campaign_id": str(r["campaign_id"]) if r["campaign_id"] else None,
                    "created_at": r["created_at"].isoformat() if r["created_at"] else None,
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
            logger.error(f"Vector search (pain points) error: {e}")
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
        Search across all content types (ProcessedContent, Insights, PainPoints).

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

            insights_task = self.search_insights(
                query=query,
                brand_id=brand_id,
                campaign_id=campaign_id,
                min_similarity=min_similarity,
                limit=limit_per_type
            )

            pain_points_task = self.search_pain_points(
                query=query,
                brand_id=brand_id,
                campaign_id=campaign_id,
                min_similarity=min_similarity,
                limit=limit_per_type
            )

            content_results, insights_results, pain_points_results = await asyncio.gather(
                content_task, insights_task, pain_points_task
            )

            total_count = (
                len(content_results.get("results", [])) +
                len(insights_results.get("results", [])) +
                len(pain_points_results.get("results", []))
            )

            return {
                "success": True,
                "query": query,
                "total_count": total_count,
                "min_similarity": min_similarity,
                "content": content_results,
                "insights": insights_results,
                "pain_points": pain_points_results
            }

        except Exception as e:
            logger.error(f"Vector search (all) error: {e}")
            return {
                "success": False,
                "error": str(e),
                "content": {"results": []},
                "insights": {"results": []},
                "pain_points": {"results": []}
            }


class HybridSearchTool:
    """
    Combine vector similarity search with keyword matching.

    Use this tool when:
    - You want both semantic and exact keyword matches
    - Query contains specific terms that should be matched exactly
    - You need comprehensive results combining both approaches
    """

    name = "hybrid_search"
    description = (
        "Combine vector similarity search with keyword matching for comprehensive results. "
        "Returns results from both semantic understanding and exact keyword matches. "
        "Use when you need both conceptual and literal matching."
    )

    def __init__(self):
        self.vector_tool = VectorSearchTool()

    async def search(
        self,
        query: str,
        brand_id: Optional[str] = None,
        campaign_id: Optional[str] = None,
        content_type: str = "all",  # all, content, insights, pain_points
        min_similarity: float = 0.7,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Perform hybrid search combining vector similarity and keyword matching.

        Args:
            query: Natural language query
            brand_id: Optional brand filter
            campaign_id: Optional campaign filter
            content_type: Type of content to search
            min_similarity: Minimum similarity for vector search
            limit: Maximum total results

        Returns:
            Dictionary with combined results
        """
        try:
            import asyncio

            # Run vector search and keyword search in parallel
            if content_type == "content" or content_type == "all":
                # Vector search
                vector_task = self.vector_tool.search_content(
                    query=query,
                    brand_id=brand_id,
                    campaign_id=campaign_id,
                    min_similarity=min_similarity,
                    limit=limit
                )

                # Keyword search
                keyword_queryset = ProcessedContent.objects.filter(
                    Q(cleaned_content__icontains=query) |
                    Q(original_content__icontains=query)
                )

                if brand_id:
                    keyword_queryset = keyword_queryset.filter(brand_id=brand_id)

                if campaign_id:
                    keyword_queryset = keyword_queryset.filter(campaign_id=campaign_id)

                keyword_results = list(keyword_queryset[:limit].values(
                    'id', 'content_type', 'cleaned_content',
                    'sentiment', 'sentiment_score', 'echo_score',
                    'source', 'brand_id', 'campaign_id', 'created_at'
                ))

                vector_results = await vector_task

                # Combine and deduplicate
                seen_ids = set()
                combined = []

                # Add vector results first (prioritized by similarity)
                for r in vector_results.get("results", []):
                    if r["id"] not in seen_ids:
                        r["match_type"] = "semantic"
                        combined.append(r)
                        seen_ids.add(r["id"])

                # Add keyword results
                for r in keyword_results:
                    r_id = str(r["id"])
                    if r_id not in seen_ids:
                        combined.append({
                            "id": r_id,
                            "content_type": r["content_type"],
                            "content": r["cleaned_content"][:500],
                            "sentiment": r["sentiment"],
                            "sentiment_score": round(r["sentiment_score"] or 0.0, 2),
                            "echo_score": round(r["echo_score"] or 0.0, 2),
                            "source": r["source"],
                            "brand_id": str(r["brand_id"]) if r["brand_id"] else None,
                            "campaign_id": str(r["campaign_id"]) if r["campaign_id"] else None,
                            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
                            "match_type": "keyword",
                            "similarity": None
                        })
                        seen_ids.add(r_id)

                return {
                    "success": True,
                    "query": query,
                    "count": len(combined),
                    "results": combined[:limit]
                }

            elif content_type == "insights":
                vector_results = await self.vector_tool.search_insights(
                    query=query,
                    brand_id=brand_id,
                    campaign_id=campaign_id,
                    min_similarity=min_similarity,
                    limit=limit
                )

                # Keyword search for insights
                keyword_queryset = Insight.objects.filter(
                    Q(title__icontains=query) |
                    Q(description__icontains=query)
                )

                if brand_id:
                    keyword_queryset = keyword_queryset.filter(brand_id=brand_id)

                if campaign_id:
                    keyword_queryset = keyword_queryset.filter(campaign_id=campaign_id)

                keyword_results = list(keyword_queryset[:limit].values(
                    'id', 'title', 'description', 'insight_type',
                    'severity', 'confidence_score', 'brand_id',
                    'campaign_id', 'created_at'
                ))

                # Combine and deduplicate
                seen_ids = set()
                combined = []

                for r in vector_results.get("results", []):
                    if r["id"] not in seen_ids:
                        r["match_type"] = "semantic"
                        combined.append(r)
                        seen_ids.add(r["id"])

                for r in keyword_results:
                    r_id = str(r["id"])
                    if r_id not in seen_ids:
                        combined.append({
                            "id": r_id,
                            "title": r["title"],
                            "description": r["description"][:500],
                            "insight_type": r["insight_type"],
                            "severity": r["severity"],
                            "confidence_score": round(r["confidence_score"] or 0.0, 2),
                            "brand_id": str(r["brand_id"]) if r["brand_id"] else None,
                            "campaign_id": str(r["campaign_id"]) if r["campaign_id"] else None,
                            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
                            "match_type": "keyword",
                            "similarity": None
                        })
                        seen_ids.add(r_id)

                return {
                    "success": True,
                    "query": query,
                    "count": len(combined),
                    "results": combined[:limit]
                }

            elif content_type == "pain_points":
                vector_results = await self.vector_tool.search_pain_points(
                    query=query,
                    brand_id=brand_id,
                    campaign_id=campaign_id,
                    min_similarity=min_similarity,
                    limit=limit
                )

                # Keyword search for pain points
                keyword_queryset = PainPoint.objects.filter(
                    Q(keyword__icontains=query) |
                    Q(example_content__icontains=query)
                )

                if brand_id:
                    keyword_queryset = keyword_queryset.filter(brand_id=brand_id)

                if campaign_id:
                    keyword_queryset = keyword_queryset.filter(campaign_id=campaign_id)

                keyword_results = list(keyword_queryset[:limit].values(
                    'id', 'keyword', 'category', 'mentions',
                    'severity', 'growth_rate', 'growth_trend',
                    'example_content', 'brand_id', 'campaign_id', 'created_at'
                ))

                # Combine and deduplicate
                seen_ids = set()
                combined = []

                for r in vector_results.get("results", []):
                    if r["id"] not in seen_ids:
                        r["match_type"] = "semantic"
                        combined.append(r)
                        seen_ids.add(r["id"])

                for r in keyword_results:
                    r_id = str(r["id"])
                    if r_id not in seen_ids:
                        combined.append({
                            "id": r_id,
                            "keyword": r["keyword"],
                            "category": r["category"],
                            "mentions": r["mentions"] or 0,
                            "severity": r["severity"] or 0,
                            "growth_rate": round(r["growth_rate"] or 0.0, 2),
                            "growth_trend": r["growth_trend"],
                            "example_content": r["example_content"][:200] if r["example_content"] else None,
                            "brand_id": str(r["brand_id"]) if r["brand_id"] else None,
                            "campaign_id": str(r["campaign_id"]) if r["campaign_id"] else None,
                            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
                            "match_type": "keyword",
                            "similarity": None
                        })
                        seen_ids.add(r_id)

                return {
                    "success": True,
                    "query": query,
                    "count": len(combined),
                    "results": combined[:limit]
                }

            else:  # all
                # Search all types using vector_tool.search_all()
                all_results = await self.vector_tool.search_all(
                    query=query,
                    brand_id=brand_id,
                    campaign_id=campaign_id,
                    min_similarity=min_similarity,
                    limit_per_type=limit // 3  # Distribute limit across types
                )

                # Note: For simplicity, we're not adding keyword search for "all" type
                # The vector search already provides comprehensive results
                return all_results

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
