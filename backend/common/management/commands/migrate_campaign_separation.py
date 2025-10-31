"""
Django management command to migrate existing data for campaign separation.

This script:
1. Marks automatic campaigns with campaign_type='automatic'
2. Marks custom campaigns with campaign_type='custom'
3. Links communities to brands via campaigns
4. Links pain points to brands
5. Links threads to brands

Usage:
    python manage.py migrate_campaign_separation
    python manage.py migrate_campaign_separation --dry-run  # To preview changes
"""

from django.core.management.base import BaseCommand
from common.models import Campaign, Community, PainPoint, Thread, Brand
from django.db import transaction


class Command(BaseCommand):
    help = 'Migrate existing data to separated Brand Analytics and Custom Campaign architecture'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run migration in dry-run mode (no changes will be saved)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 DRY RUN MODE - No changes will be saved\n'))
        else:
            self.stdout.write(self.style.WARNING('⚠️  LIVE MODE - Changes will be saved to database\n'))

        stats = {
            'automatic_campaigns': 0,
            'custom_campaigns': 0,
            'communities_linked': 0,
            'pain_points_linked': 0,
            'threads_linked': 0,
        }

        with transaction.atomic():
            # Step 1: Mark automatic campaigns
            self.stdout.write('\n📋 Step 1: Marking automatic campaigns...')
            automatic_campaigns = Campaign.objects.filter(
                metadata__is_auto_campaign=True
            )

            for campaign in automatic_campaigns:
                if campaign.campaign_type != 'automatic':
                    campaign.campaign_type = 'automatic'
                    if not dry_run:
                        campaign.save()
                    stats['automatic_campaigns'] += 1
                    self.stdout.write(
                        f"  ✓ Marked campaign '{campaign.name}' as automatic"
                    )

            # Step 2: Mark custom campaigns
            self.stdout.write('\n📋 Step 2: Marking custom campaigns...')
            custom_campaigns = Campaign.objects.exclude(
                metadata__is_auto_campaign=True
            )

            for campaign in custom_campaigns:
                if campaign.campaign_type != 'custom':
                    campaign.campaign_type = 'custom'
                    if not dry_run:
                        campaign.save()
                    stats['custom_campaigns'] += 1
                    self.stdout.write(
                        f"  ✓ Marked campaign '{campaign.name}' as custom"
                    )

            # Step 3: Link communities to brands via campaigns
            self.stdout.write('\n🏘️  Step 3: Linking communities to brands...')
            communities_without_brand = Community.objects.filter(brand__isnull=True)

            for community in communities_without_brand:
                # Find a thread from this community to get the brand
                thread = Thread.objects.filter(community=community).first()

                if thread and thread.campaign and thread.campaign.brand:
                    community.brand = thread.campaign.brand
                    community.campaign = thread.campaign
                    if not dry_run:
                        community.save()
                    stats['communities_linked'] += 1
                    self.stdout.write(
                        f"  ✓ Linked '{community.name}' to brand '{community.brand.name}'"
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  ⚠️  Could not link '{community.name}' - no threads found"
                        )
                    )

            # Step 4: Link pain points to brands
            self.stdout.write('\n💢 Step 4: Linking pain points to brands...')
            pain_points_without_brand = PainPoint.objects.filter(brand__isnull=True)

            for pp in pain_points_without_brand:
                if pp.campaign and pp.campaign.brand:
                    pp.brand = pp.campaign.brand
                    if not dry_run:
                        pp.save()
                    stats['pain_points_linked'] += 1

            self.stdout.write(f"  ✓ Linked {stats['pain_points_linked']} pain points to brands")

            # Step 5: Link threads to brands
            self.stdout.write('\n📄 Step 5: Linking threads to brands...')
            threads_without_brand = Thread.objects.filter(brand__isnull=True)

            for thread in threads_without_brand:
                if thread.campaign and thread.campaign.brand:
                    thread.brand = thread.campaign.brand
                    if not dry_run:
                        thread.save()
                    stats['threads_linked'] += 1

            self.stdout.write(f"  ✓ Linked {stats['threads_linked']} threads to brands")

            # Summary
            self.stdout.write('\n' + '=' * 60)
            self.stdout.write(self.style.SUCCESS('\n✅ Migration Summary:\n'))
            self.stdout.write(f"  • Automatic campaigns marked: {stats['automatic_campaigns']}")
            self.stdout.write(f"  • Custom campaigns marked: {stats['custom_campaigns']}")
            self.stdout.write(f"  • Communities linked to brands: {stats['communities_linked']}")
            self.stdout.write(f"  • Pain points linked to brands: {stats['pain_points_linked']}")
            self.stdout.write(f"  • Threads linked to brands: {stats['threads_linked']}")
            self.stdout.write('=' * 60 + '\n')

            if dry_run:
                self.stdout.write(self.style.WARNING('🔍 DRY RUN - Rolling back transaction (no changes saved)'))
                transaction.set_rollback(True)
            else:
                self.stdout.write(self.style.SUCCESS('💾 Migration completed successfully!'))

        # Verification
        if not dry_run:
            self.stdout.write('\n📊 Verification:')
            total_automatic = Campaign.objects.filter(campaign_type='automatic').count()
            total_custom = Campaign.objects.filter(campaign_type='custom').count()
            total_communities_with_brand = Community.objects.filter(brand__isnull=False).count()

            self.stdout.write(f"  • Total automatic campaigns: {total_automatic}")
            self.stdout.write(f"  • Total custom campaigns: {total_custom}")
            self.stdout.write(f"  • Communities with brand link: {total_communities_with_brand}")
            self.stdout.write('')
