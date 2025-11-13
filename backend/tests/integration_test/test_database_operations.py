"""
Integration tests for database operations.

Tests CRUD operations, relationships, transactions, and data integrity.
"""
import pytest
from django.db import transaction, IntegrityError
from django.utils import timezone
from datetime import datetime, timedelta

# Import models inside tests to avoid circular import
from common.models import (
    Brand, Campaign, RawContent, ProcessedContent,
    Insight, Influencer, Source
)



@pytest.mark.integration
@pytest.mark.django_db(transaction=True)
class TestDatabaseOperations:
    """Test database CRUD operations and relationships."""

    def test_brand_creation_and_retrieval(self, db):
        """Test creating and retrieving brands."""
        brand = Brand.objects.create(
            name=f'Integration Test Brand {datetime.now().timestamp()}',
            description='Test brand for integration testing',
            industry='Technology',
            primary_keywords=['AI', 'ML', 'automation'],
            product_keywords=['software', 'SaaS'],
            sources=['reddit', 'discord']
        )

        # Retrieve and verify
        retrieved = Brand.objects.get(id=brand.id)
        assert 'Integration Test Brand' in retrieved.name
        assert retrieved.industry == 'Technology'
        assert 'AI' in retrieved.primary_keywords
        assert retrieved.is_active is True

        print(f"✅ Brand created: {brand.name} (ID: {brand.id})")

    def test_campaign_creation_with_brand(self, test_user, test_brand):
        """Test creating campaign linked to brand."""
        campaign = Campaign.objects.create(
            name='Test Campaign with Brand',
            brand=test_brand,
            owner=test_user,
            campaign_type='automatic',
            keywords=['test', 'integration'],
            sources=['reddit'],
            budget_limit=100.00
        )

        # Verify relationships
        assert campaign.brand == test_brand
        assert campaign.owner == test_user
        assert campaign in test_brand.campaigns.all()

        print(f"✅ Campaign created: {campaign.name} linked to {test_brand.name}")

    def test_raw_content_bulk_creation(self, test_campaign_custom, db):
        """Test bulk creating raw content."""
        import uuid
        # Create a source first
        unique_id = uuid.uuid4().hex[:8]
        source = Source.objects.create(
            name=f'Test Reddit {unique_id}',
            source_type='reddit',
            url=f'https://reddit.com/r/test_{unique_id}'
        )

        # Bulk create raw content
        raw_content_list = []
        for i in range(50):
            raw_content_list.append(
                RawContent(
                    source=source,
                    campaign=test_campaign_custom,
                    external_id=f'test_content_{i}',
                    url=f'https://reddit.com/r/test/comments/{i}',
                    title=f'Test Thread {i}',
                    author=f'user_{i}',
                    published_at=timezone.now() - timedelta(days=i),
                    content=f'This is test content number {i}',
                    is_processed=False
                )
            )

        created = RawContent.objects.bulk_create(raw_content_list)
        assert len(created) == 50

        # Verify retrieval
        count = RawContent.objects.filter(campaign=test_campaign_custom).count()
        assert count == 50

        print(f"✅ Bulk created 50 raw content items for campaign: {test_campaign_custom.name}")

    def test_processed_content_with_embedding(self, test_campaign_custom, db):
        """Test creating processed content with vector embeddings."""
        import uuid
        # Create source and raw content
        unique_id = uuid.uuid4().hex[:8]
        source = Source.objects.create(
            name=f'Test Reddit 2 {unique_id}',
            source_type='reddit',
            url=f'https://reddit.com/r/test2_{unique_id}'
        )

        raw = RawContent.objects.create(
            source=source,
            campaign=test_campaign_custom,
            external_id='test_embed_1',
            url='https://reddit.com/r/test/comments/embed1',
            title='Test Embedding',
            author='test_user',
            published_at=timezone.now(),
            content='Test content for embedding'
        )

        # Create processed content (without embedding for now, as generating embeddings requires OpenAI)
        processed = ProcessedContent.objects.create(
            raw_content=raw,
            cleaned_content='Test content for embedding',
            language='en',
            sentiment_score=0.5,
            toxicity_score=0.1,
            spam_score=0.05,
            keywords=['test', 'embedding'],
            topics=['technology']
        )

        # Verify
        assert processed.raw_content == raw
        assert processed.cleaned_content == 'Test content for embedding'
        assert processed.sentiment_score == 0.5

        # Verify one-to-one relationship
        assert raw.processed == processed

        print(f"✅ Processed content created with ID: {processed.id}")

    def test_insight_creation_with_content_relationship(self, test_campaign_custom, db):
        """Test creating insights linked to processed content."""
        import uuid
        # Create raw and processed content
        unique_id = uuid.uuid4().hex[:8]
        source = Source.objects.create(
            name=f'Test Reddit 3 {unique_id}',
            source_type='reddit',
            url=f'https://reddit.com/r/test3_{unique_id}'
        )

        raw = RawContent.objects.create(
            source=source,
            campaign=test_campaign_custom,
            external_id='insight_test_1',
            url='https://reddit.com/r/test/comments/insight1',
            title='Pain Point Thread',
            author='user_1',
            published_at=timezone.now(),
            content='Users complaining about pricing'
        )

        processed = ProcessedContent.objects.create(
            raw_content=raw,
            cleaned_content='Users complaining about pricing',
            sentiment_score=-0.6
        )

        # Create insight
        insight = Insight.objects.create(
            campaign=test_campaign_custom,
            insight_type='pain_point',
            title='Pricing Concerns',
            description='Multiple users expressing concerns about high pricing',
            confidence_score=0.85,
            impact_score=0.9,
            priority_score=0.88
        )

        # Link processed content to insight (many-to-many)
        insight.content.add(processed)

        # Verify
        assert insight in processed.insights.all()
        assert processed in insight.content.all()

        print(f"✅ Insight created: {insight.title} (confidence: {insight.confidence_score})")

    def test_influencer_scoring_calculation(self, test_campaign_automatic, test_brand, db):
        """Test creating influencers with scoring."""
        influencer = Influencer.objects.create(
            campaign=test_campaign_automatic,
            brand=test_brand,
            username='tech_reviewer_pro',
            source_type='reddit',
            platform='reddit',
            profile_url='https://reddit.com/u/tech_reviewer_pro',
            total_karma=15000,
            total_posts=250,
            total_comments=1200,
            avg_post_score=60.5,
            # Component scores
            reach_score=82.0,
            authority_score=75.0,
            advocacy_score=80.0,
            relevance_score=77.0,
            # Overall influence score (weighted: reach*0.3 + authority*0.3 + advocacy*0.2 + relevance*0.2)
            influence_score=78.5,
            sentiment_towards_brand=0.7,
            brand_mention_count=45
        )

        # Verify
        assert influencer.influence_score == 78.5
        assert influencer.username == 'tech_reviewer_pro'
        assert influencer.campaign == test_campaign_automatic

        print(f"✅ Influencer created: {influencer.username} (influence: {influencer.influence_score})")

    def test_transaction_rollback_on_error(self, test_campaign_custom, db):
        """Test that transactions rollback on errors."""
        import uuid
        unique_id = uuid.uuid4().hex[:8]
        source = Source.objects.create(
            name=f'Test Reddit Rollback {unique_id}',
            source_type='reddit',
            url=f'https://reddit.com/r/rollback_{unique_id}'
        )

        initial_count = RawContent.objects.filter(campaign=test_campaign_custom).count()

        try:
            with transaction.atomic():
                # Create first content
                RawContent.objects.create(
                    source=source,
                    campaign=test_campaign_custom,
                    external_id='rollback_test_1',
                    url='https://reddit.com/r/test/1',
                    title='Test 1',
                    author='user1',
                    published_at=timezone.now(),
                    content='Test content 1'
                )

                # Try to create duplicate (should fail due to unique constraint)
                RawContent.objects.create(
                    source=source,
                    campaign=test_campaign_custom,
                    external_id='rollback_test_1',  # Duplicate external_id for same source
                    url='https://reddit.com/r/test/2',
                    title='Test 2',
                    author='user2',
                    published_at=timezone.now(),
                    content='Test content 2'
                )
        except IntegrityError:
            print("✅ IntegrityError caught as expected")

        # Verify rollback - count should be same as before
        final_count = RawContent.objects.filter(campaign=test_campaign_custom).count()
        assert final_count == initial_count

        print(f"✅ Transaction rollback verified (count unchanged: {final_count})")

    def test_cascade_delete_campaign(self, test_campaign_custom, db):
        """Test cascade delete when campaign is deleted."""
        import uuid
        # Create related data
        unique_id = uuid.uuid4().hex[:8]
        source = Source.objects.create(
            name=f'Test Reddit Cascade {unique_id}',
            source_type='reddit',
            url=f'https://reddit.com/r/cascade_{unique_id}'
        )

        raw = RawContent.objects.create(
            source=source,
            campaign=test_campaign_custom,
            external_id='cascade_test_1',
            url='https://reddit.com/r/test/cascade',
            title='Cascade Test',
            author='user1',
            published_at=timezone.now(),
            content='Test cascade delete'
        )

        insight = Insight.objects.create(
            campaign=test_campaign_custom,
            insight_type='trend',
            title='Test Insight',
            description='Test cascade',
            confidence_score=0.8
        )

        campaign_id = test_campaign_custom.id

        # Delete campaign
        test_campaign_custom.delete()

        # Verify cascade delete
        assert not Campaign.objects.filter(id=campaign_id).exists()
        assert not RawContent.objects.filter(campaign_id=campaign_id).exists()
        assert not Insight.objects.filter(campaign_id=campaign_id).exists()

        print(f"✅ Cascade delete verified for campaign {campaign_id}")

    def test_query_performance_with_select_related(self, test_campaign_custom, db):
        """Test query optimization with select_related."""
        import uuid
        # Create test data
        unique_id = uuid.uuid4().hex[:8]
        source = Source.objects.create(
            name=f'Test Reddit Performance {unique_id}',
            source_type='reddit',
            url=f'https://reddit.com/r/performance_{unique_id}'
        )

        for i in range(10):
            raw = RawContent.objects.create(
                source=source,
                campaign=test_campaign_custom,
                external_id=f'perf_test_{i}',
                url=f'https://reddit.com/r/test/{i}',
                title=f'Test {i}',
                author=f'user_{i}',
                published_at=timezone.now(),
                content=f'Content {i}'
            )

            ProcessedContent.objects.create(
                raw_content=raw,
                cleaned_content=f'Cleaned content {i}'
            )

        # Query without select_related (will cause N+1 queries)
        contents = ProcessedContent.objects.filter(raw_content__campaign=test_campaign_custom)
        count_without_optimization = len(contents)

        # Query with select_related (optimized)
        contents_optimized = ProcessedContent.objects.filter(
            raw_content__campaign=test_campaign_custom
        ).select_related('raw_content', 'raw_content__source', 'raw_content__campaign')

        count_with_optimization = len(contents_optimized)

        assert count_without_optimization == count_with_optimization == 10

        print(f"✅ Query optimization test passed: {count_with_optimization} items retrieved")

    def test_campaign_metadata_json_field(self, test_campaign_custom, db):
        """Test JSON field operations for campaign metadata."""
        # Update metadata
        test_campaign_custom.metadata = {
            'ai_insights': {
                'pain_points_summary': 'High pricing concerns',
                'sentiment_trend': 'improving',
                'top_keywords': ['price', 'quality', 'support']
            },
            'execution_stats': {
                'threads_collected': 150,
                'influencers_identified': 8,
                'execution_time_seconds': 45.2
            }
        }
        test_campaign_custom.save()

        # Refresh and verify
        test_campaign_custom.refresh_from_db()

        assert 'ai_insights' in test_campaign_custom.metadata
        assert test_campaign_custom.metadata['ai_insights']['pain_points_summary'] == 'High pricing concerns'
        assert test_campaign_custom.metadata['execution_stats']['threads_collected'] == 150

        print(f"✅ JSON metadata operations verified")
