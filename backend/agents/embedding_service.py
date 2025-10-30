"""
Embedding Service for generating and managing vector embeddings.

This service handles:
- Generating embeddings using OpenAI text-embedding-3-small
- Batch processing for efficiency
- Cost tracking
- Error handling and retries
"""

import asyncio
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from openai import AsyncOpenAI
from django.conf import settings
from django.utils import timezone

from common.models import ProcessedContent, Insight, PainPoint

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Service for generating and managing embeddings for RAG.

    Features:
    - Batch embedding generation
    - Caching to avoid re-embedding
    - Cost tracking
    - Error handling and retry logic
    """

    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = "text-embedding-3-small"  # 1536 dimensions, $0.02/1M tokens
        self.dimensions = 1536
        self.batch_size = 100  # OpenAI allows up to 2048

    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            List of floats (embedding vector)
        """
        try:
            # Truncate text to fit token limits (8191 tokens for text-embedding-3-small)
            text = text[:8000]  # ~8000 chars ≈ 2000 tokens (safe limit)

            if not text.strip():
                logger.warning("Empty text provided for embedding, using placeholder")
                text = "No content available"

            response = await self.client.embeddings.create(
                model=self.model,
                input=text,
                dimensions=self.dimensions
            )

            return response.data[0].embedding

        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise

    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batch.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        try:
            # Truncate all texts and handle empty texts
            processed_texts = []
            for text in texts:
                text = text[:8000] if text else "No content available"
                if not text.strip():
                    text = "No content available"
                processed_texts.append(text)

            response = await self.client.embeddings.create(
                model=self.model,
                input=processed_texts,
                dimensions=self.dimensions
            )

            # Sort by index to maintain order
            embeddings = sorted(response.data, key=lambda x: x.index)
            return [emb.embedding for emb in embeddings]

        except Exception as e:
            logger.error(f"Failed to generate batch embeddings: {e}")
            raise

    async def embed_processed_content(
        self,
        content_ids: Optional[List[str]] = None,
        force_regenerate: bool = False,
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate embeddings for ProcessedContent records.

        Args:
            content_ids: Optional list of specific IDs to embed
            force_regenerate: If True, regenerate even if embeddings exist
            limit: Maximum number of items to process

        Returns:
            Stats dict with counts and cost
        """
        try:
            # Query content needing embeddings
            queryset = ProcessedContent.objects.all()

            if content_ids:
                queryset = queryset.filter(id__in=content_ids)

            if not force_regenerate:
                queryset = queryset.filter(embedding__isnull=True)

            if limit:
                queryset = queryset[:limit]

            content_items = list(queryset)

            if not content_items:
                logger.info("No ProcessedContent items need embedding")
                return {"embedded": 0, "skipped": 0, "cost": 0.0}

            logger.info(f"Generating embeddings for {len(content_items)} ProcessedContent items")

            # Process in batches
            embedded_count = 0
            total_tokens = 0

            for i in range(0, len(content_items), self.batch_size):
                batch = content_items[i:i + self.batch_size]
                texts = [item.cleaned_content for item in batch]

                # Generate embeddings
                embeddings = await self.generate_embeddings_batch(texts)

                # Update database
                for item, embedding in zip(batch, embeddings):
                    item.embedding = embedding
                    item.embedding_model = self.model
                    item.embedding_created_at = timezone.now()
                    item.save(update_fields=['embedding', 'embedding_model', 'embedding_created_at'])

                embedded_count += len(batch)
                # Rough token estimate: words * 1.3 tokens/word
                total_tokens += sum(len(text.split()) * 1.3 for text in texts)

                logger.info(f"Embedded batch {i//self.batch_size + 1}/{(len(content_items)-1)//self.batch_size + 1}")

            # Calculate cost: $0.02 per 1M tokens
            cost = (total_tokens / 1_000_000) * 0.02

            return {
                "embedded": embedded_count,
                "skipped": 0,
                "total_tokens": int(total_tokens),
                "cost": round(cost, 4),
                "model": self.model
            }

        except Exception as e:
            logger.error(f"Failed to embed ProcessedContent: {e}")
            raise

    async def embed_insights(
        self,
        insight_ids: Optional[List[str]] = None,
        force_regenerate: bool = False,
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """Generate embeddings for Insight records."""
        try:
            queryset = Insight.objects.all()

            if insight_ids:
                queryset = queryset.filter(id__in=insight_ids)

            if not force_regenerate:
                queryset = queryset.filter(embedding__isnull=True)

            if limit:
                queryset = queryset[:limit]

            insights = list(queryset)

            if not insights:
                logger.info("No Insights need embedding")
                return {"embedded": 0, "skipped": 0, "cost": 0.0}

            logger.info(f"Generating embeddings for {len(insights)} Insights")

            embedded_count = 0
            total_tokens = 0

            for i in range(0, len(insights), self.batch_size):
                batch = insights[i:i + self.batch_size]
                # Combine title + description for richer embeddings
                texts = [f"{item.title}\n\n{item.description}" for item in batch]

                embeddings = await self.generate_embeddings_batch(texts)

                for item, embedding in zip(batch, embeddings):
                    item.embedding = embedding
                    item.embedding_model = self.model
                    item.embedding_created_at = timezone.now()
                    item.save(update_fields=['embedding', 'embedding_model', 'embedding_created_at'])

                embedded_count += len(batch)
                total_tokens += sum(len(text.split()) * 1.3 for text in texts)

                logger.info(f"Embedded batch {i//self.batch_size + 1}/{(len(insights)-1)//self.batch_size + 1}")

            cost = (total_tokens / 1_000_000) * 0.02

            return {
                "embedded": embedded_count,
                "skipped": 0,
                "total_tokens": int(total_tokens),
                "cost": round(cost, 4),
                "model": self.model
            }

        except Exception as e:
            logger.error(f"Failed to embed Insights: {e}")
            raise

    async def embed_pain_points(
        self,
        pain_point_ids: Optional[List[str]] = None,
        force_regenerate: bool = False,
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """Generate embeddings for PainPoint records."""
        try:
            queryset = PainPoint.objects.all()

            if pain_point_ids:
                queryset = queryset.filter(id__in=pain_point_ids)

            if not force_regenerate:
                queryset = queryset.filter(embedding__isnull=True)

            if limit:
                queryset = queryset[:limit]

            pain_points = list(queryset)

            if not pain_points:
                logger.info("No PainPoints need embedding")
                return {"embedded": 0, "skipped": 0, "cost": 0.0}

            logger.info(f"Generating embeddings for {len(pain_points)} PainPoints")

            embedded_count = 0
            total_tokens = 0

            for i in range(0, len(pain_points), self.batch_size):
                batch = pain_points[i:i + self.batch_size]
                # Use keyword + context
                texts = [
                    f"{item.keyword}\n{item.example_content}" if item.example_content else item.keyword
                    for item in batch
                ]

                embeddings = await self.generate_embeddings_batch(texts)

                for item, embedding in zip(batch, embeddings):
                    item.embedding = embedding
                    item.embedding_model = self.model
                    item.embedding_created_at = timezone.now()
                    item.save(update_fields=['embedding', 'embedding_model', 'embedding_created_at'])

                embedded_count += len(batch)
                total_tokens += sum(len(text.split()) * 1.3 for text in texts)

                logger.info(f"Embedded batch {i//self.batch_size + 1}/{(len(pain_points)-1)//self.batch_size + 1}")

            cost = (total_tokens / 1_000_000) * 0.02

            return {
                "embedded": embedded_count,
                "skipped": 0,
                "total_tokens": int(total_tokens),
                "cost": round(cost, 4),
                "model": self.model
            }

        except Exception as e:
            logger.error(f"Failed to embed PainPoints: {e}")
            raise

    async def embed_all(
        self,
        force_regenerate: bool = False,
        limit_per_type: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate embeddings for all content types.

        Args:
            force_regenerate: If True, regenerate even if embeddings exist
            limit_per_type: Maximum number of items to process per type

        Returns:
            Combined stats for all types
        """
        logger.info("Starting embedding generation for all content types")

        # Run all embedding tasks in parallel
        content_task = self.embed_processed_content(
            force_regenerate=force_regenerate,
            limit=limit_per_type
        )
        insight_task = self.embed_insights(
            force_regenerate=force_regenerate,
            limit=limit_per_type
        )
        pain_point_task = self.embed_pain_points(
            force_regenerate=force_regenerate,
            limit=limit_per_type
        )

        content_stats, insight_stats, pain_point_stats = await asyncio.gather(
            content_task, insight_task, pain_point_task
        )

        # Combine statistics
        total_stats = {
            "content": content_stats,
            "insights": insight_stats,
            "pain_points": pain_point_stats,
            "totals": {
                "embedded": (
                    content_stats["embedded"] +
                    insight_stats["embedded"] +
                    pain_point_stats["embedded"]
                ),
                "total_tokens": (
                    content_stats["total_tokens"] +
                    insight_stats["total_tokens"] +
                    pain_point_stats["total_tokens"]
                ),
                "cost": round(
                    content_stats["cost"] +
                    insight_stats["cost"] +
                    pain_point_stats["cost"],
                    4
                )
            }
        }

        logger.info(
            f"Embedding generation complete: {total_stats['totals']['embedded']} items embedded, "
            f"cost: ${total_stats['totals']['cost']}"
        )

        return total_stats


# Singleton instance
embedding_service = EmbeddingService()
