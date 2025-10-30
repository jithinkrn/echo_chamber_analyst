# Generated migration for search performance indexes

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0006_add_vector_fields'),
    ]

    operations = [
        # Vector similarity indexes using IVFFlat
        # Note: For local PostgreSQL, you may need to reduce 'lists' parameter
        # For production with >10K vectors, use lists = sqrt(row_count)
        migrations.RunSQL(
            sql="""
            CREATE INDEX IF NOT EXISTS idx_processed_content_embedding
            ON processed_content USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100);
            """,
            reverse_sql="DROP INDEX IF EXISTS idx_processed_content_embedding;"
        ),

        migrations.RunSQL(
            sql="""
            CREATE INDEX IF NOT EXISTS idx_insight_embedding
            ON insights USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100);
            """,
            reverse_sql="DROP INDEX IF EXISTS idx_insight_embedding;"
        ),

        migrations.RunSQL(
            sql="""
            CREATE INDEX IF NOT EXISTS idx_painpoint_embedding
            ON pain_points USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 50);
            """,
            reverse_sql="DROP INDEX IF EXISTS idx_painpoint_embedding;"
        ),

        # Full-text search indexes (GIN)
        migrations.RunSQL(
            sql="""
            CREATE INDEX IF NOT EXISTS idx_processed_content_text_search
            ON processed_content USING GIN (to_tsvector('english', cleaned_content));
            """,
            reverse_sql="DROP INDEX IF EXISTS idx_processed_content_text_search;"
        ),

        migrations.RunSQL(
            sql="""
            CREATE INDEX IF NOT EXISTS idx_insight_text_search
            ON insights USING GIN (to_tsvector('english', coalesce(title, '') || ' ' || coalesce(description, '')));
            """,
            reverse_sql="DROP INDEX IF EXISTS idx_insight_text_search;"
        ),

        # Performance indexes for common filters
        migrations.RunSQL(
            sql="CREATE INDEX IF NOT EXISTS idx_campaign_brand_id ON campaigns (brand_id) WHERE brand_id IS NOT NULL;",
            reverse_sql="DROP INDEX IF EXISTS idx_campaign_brand_id;"
        ),

        migrations.RunSQL(
            sql="CREATE INDEX IF NOT EXISTS idx_community_echo_score ON communities (echo_score DESC NULLS LAST);",
            reverse_sql="DROP INDEX IF EXISTS idx_community_echo_score;"
        ),

        migrations.RunSQL(
            sql="CREATE INDEX IF NOT EXISTS idx_influencer_influence_score ON influencers (influence_score DESC NULLS LAST);",
            reverse_sql="DROP INDEX IF EXISTS idx_influencer_influence_score;"
        ),

        migrations.RunSQL(
            sql="CREATE INDEX IF NOT EXISTS idx_painpoint_growth ON pain_points (growth_percentage DESC NULLS LAST) WHERE growth_percentage IS NOT NULL;",
            reverse_sql="DROP INDEX IF EXISTS idx_painpoint_growth;"
        ),

        migrations.RunSQL(
            sql="CREATE INDEX IF NOT EXISTS idx_thread_campaign_id ON threads (campaign_id) WHERE campaign_id IS NOT NULL;",
            reverse_sql="DROP INDEX IF EXISTS idx_thread_campaign_id;"
        ),

        migrations.RunSQL(
            sql="CREATE INDEX IF NOT EXISTS idx_thread_community_id ON threads (community_id) WHERE community_id IS NOT NULL;",
            reverse_sql="DROP INDEX IF EXISTS idx_thread_community_id;"
        ),
    ]
