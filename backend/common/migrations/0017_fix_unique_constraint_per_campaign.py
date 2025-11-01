# Fix unique constraint to be per campaign only (not brand-specific)

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0016_prevent_duplicate_communities'),
    ]

    operations = [
        # Drop the old constraint
        migrations.RunSQL(
            sql="""
                DROP INDEX IF EXISTS unique_community_name_lower_per_campaign_brand_platform;
            """,
            reverse_sql=migrations.RunSQL.noop
        ),
        
        # Create new constraint without brand_id (allow same community name across brands, but not within same campaign/platform)
        migrations.RunSQL(
            sql="""
                CREATE UNIQUE INDEX unique_community_name_lower_per_campaign_platform
                ON communities (LOWER(name), platform, campaign_id)
                WHERE campaign_id IS NOT NULL;
            """,
            reverse_sql="""
                DROP INDEX IF EXISTS unique_community_name_lower_per_campaign_platform;
            """
        ),
    ]
