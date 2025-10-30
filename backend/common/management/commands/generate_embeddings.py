"""
Django Management Command for Generating Embeddings.

Usage:
    python manage.py generate_embeddings --all
    python manage.py generate_embeddings --content
    python manage.py generate_embeddings --insights
    python manage.py generate_embeddings --pain-points
    python manage.py generate_embeddings --force
    python manage.py generate_embeddings --limit 100
"""

import asyncio
import logging
from django.core.management.base import BaseCommand, CommandError
from agents.embedding_service import embedding_service

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Generate embeddings for content, insights, and pain points'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Generate embeddings for all content types'
        )
        parser.add_argument(
            '--content',
            action='store_true',
            help='Generate embeddings for ProcessedContent only'
        )
        parser.add_argument(
            '--insights',
            action='store_true',
            help='Generate embeddings for Insights only'
        )
        parser.add_argument(
            '--pain-points',
            action='store_true',
            help='Generate embeddings for PainPoints only'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Regenerate embeddings even if they already exist'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Maximum number of items to process per type'
        )
        parser.add_argument(
            '--brand',
            type=str,
            default=None,
            help='Process only items for specific brand ID'
        )
        parser.add_argument(
            '--campaign',
            type=str,
            default=None,
            help='Process only items for specific campaign ID'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== Embedding Generation Started ===\n'))

        all_types = options['all']
        content = options['content']
        insights = options['insights']
        pain_points = options['pain_points']
        force = options['force']
        limit = options['limit']
        brand_id = options['brand']
        campaign_id = options['campaign']

        # If no specific type selected, default to all
        if not (all_types or content or insights or pain_points):
            all_types = True

        # Run async embedding generation
        try:
            if all_types:
                self.stdout.write('Generating embeddings for all content types...\n')
                stats = asyncio.run(embedding_service.embed_all(
                    force_regenerate=force,
                    limit_per_type=limit
                ))
                self._print_all_stats(stats)

            else:
                if content:
                    self.stdout.write('Generating embeddings for ProcessedContent...\n')
                    stats = asyncio.run(embedding_service.embed_processed_content(
                        force_regenerate=force,
                        limit=limit
                    ))
                    self._print_stats('ProcessedContent', stats)

                if insights:
                    self.stdout.write('Generating embeddings for Insights...\n')
                    stats = asyncio.run(embedding_service.embed_insights(
                        force_regenerate=force,
                        limit=limit
                    ))
                    self._print_stats('Insights', stats)

                if pain_points:
                    self.stdout.write('Generating embeddings for PainPoints...\n')
                    stats = asyncio.run(embedding_service.embed_pain_points(
                        force_regenerate=force,
                        limit=limit
                    ))
                    self._print_stats('PainPoints', stats)

            self.stdout.write(self.style.SUCCESS('\n=== Embedding Generation Complete ==='))

        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            raise CommandError(f'Embedding generation failed: {e}')

    def _print_stats(self, content_type, stats):
        """Print statistics for a single content type."""
        self.stdout.write(self.style.SUCCESS(f'\n{content_type} Statistics:'))
        self.stdout.write(f'  Embedded: {stats.get("embedded", 0)} items')
        self.stdout.write(f'  Skipped: {stats.get("skipped", 0)} items')
        self.stdout.write(f'  Total Tokens: {stats.get("total_tokens", 0):,}')
        self.stdout.write(f'  Cost: ${stats.get("cost", 0):.4f}')
        self.stdout.write(f'  Model: {stats.get("model", "unknown")}\n')

    def _print_all_stats(self, stats):
        """Print statistics for all content types."""
        self.stdout.write(self.style.SUCCESS('\nProcessedContent Statistics:'))
        content_stats = stats.get('content', {})
        self.stdout.write(f'  Embedded: {content_stats.get("embedded", 0)} items')
        self.stdout.write(f'  Total Tokens: {content_stats.get("total_tokens", 0):,}')
        self.stdout.write(f'  Cost: ${content_stats.get("cost", 0):.4f}\n')

        self.stdout.write(self.style.SUCCESS('Insights Statistics:'))
        insight_stats = stats.get('insights', {})
        self.stdout.write(f'  Embedded: {insight_stats.get("embedded", 0)} items')
        self.stdout.write(f'  Total Tokens: {insight_stats.get("total_tokens", 0):,}')
        self.stdout.write(f'  Cost: ${insight_stats.get("cost", 0):.4f}\n')

        self.stdout.write(self.style.SUCCESS('PainPoints Statistics:'))
        pain_point_stats = stats.get('pain_points', {})
        self.stdout.write(f'  Embedded: {pain_point_stats.get("embedded", 0)} items')
        self.stdout.write(f'  Total Tokens: {pain_point_stats.get("total_tokens", 0):,}')
        self.stdout.write(f'  Cost: ${pain_point_stats.get("cost", 0):.4f}\n')

        self.stdout.write(self.style.SUCCESS('=== TOTALS ==='))
        totals = stats.get('totals', {})
        self.stdout.write(f'  Total Embedded: {totals.get("embedded", 0)} items')
        self.stdout.write(f'  Total Tokens: {totals.get("total_tokens", 0):,}')
        self.stdout.write(f'  Total Cost: ${totals.get("cost", 0):.4f}')
