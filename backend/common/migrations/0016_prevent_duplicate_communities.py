# Generated manually to prevent case-sensitive duplicate communities

from django.db import migrations
from django.db.models import Q


def merge_duplicate_communities(apps, schema_editor):
    """
    Merge any existing duplicate communities (case-insensitive duplicates).
    E.g., "TikTok" and "tiktok" -> keep one, merge data
    """
    Community = apps.get_model('common', 'Community')
    PainPoint = apps.get_model('common', 'PainPoint')
    Thread = apps.get_model('common', 'Thread')
    
    # Find all communities grouped by lowercase name, platform, and campaign
    from collections import defaultdict
    groups = defaultdict(list)
    
    for comm in Community.objects.all():
        key = (comm.name.lower(), comm.platform, comm.campaign_id, comm.brand_id)
        groups[key].append(comm)
    
    # Merge duplicates
    merged_count = 0
    for key, communities in groups.items():
        if len(communities) > 1:
            # Keep the most recent one (by updated_at)
            communities_sorted = sorted(communities, key=lambda c: c.updated_at, reverse=True)
            primary = communities_sorted[0]
            duplicates = communities_sorted[1:]
            
            print(f"Merging {len(duplicates)} duplicate(s) of '{primary.name}' (platform={primary.platform})")
            
            # Move all pain points and threads to primary
            for dup in duplicates:
                PainPoint.objects.filter(community=dup).update(community=primary)
                Thread.objects.filter(community=dup).update(community=primary)
                dup.delete()
                merged_count += 1
            
            print(f"  Merged into: {primary.name} (ID: {primary.id})")
    
    if merged_count > 0:
        print(f"\n✅ Merged {merged_count} duplicate communities")
    else:
        print("✅ No duplicate communities found")


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0014_update_community_fields'),
    ]

    operations = [
        # First, merge any existing duplicates
        migrations.RunPython(
            merge_duplicate_communities,
            reverse_code=migrations.RunPython.noop
        ),
        
        # Then add a constraint to prevent future case-insensitive duplicates
        # Note: Django doesn't directly support case-insensitive unique constraints in Meta
        # But we've fixed the code logic to prevent this
        migrations.RunSQL(
            # Create a unique index with LOWER() for case-insensitive uniqueness
            sql="""
                CREATE UNIQUE INDEX IF NOT EXISTS unique_community_name_lower_per_campaign_brand_platform
                ON communities (LOWER(name), platform, campaign_id, brand_id);
            """,
            reverse_sql="""
                DROP INDEX IF EXISTS unique_community_name_lower_per_campaign_brand_platform;
            """
        ),
    ]
