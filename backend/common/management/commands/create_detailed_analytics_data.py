"""
Management command to create detailed analytics test data for dashboard sections:
- Community heat map data
- Top growing pain points  
- Community watchlist
- Influencer pulse
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
import random

from common.models import (
    Brand, Campaign, Community, PainPoint, Thread, Influencer
)


class Command(BaseCommand):
    help = 'Create detailed analytics test data for dashboard'

    def add_arguments(self, parser):
        parser.add_argument('--brand', type=str, help='Brand name to create data for')
        parser.add_argument('--clear', action='store_true', help='Clear existing data first')

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing analytics data...')
            Community.objects.all().delete()
            PainPoint.objects.all().delete()
            Thread.objects.all().delete()
            Influencer.objects.all().delete()

        # Get existing brands and campaigns
        brands = Brand.objects.all()
        if not brands.exists():
            self.stdout.write(self.style.ERROR('No brands found. Run create_test_data first.'))
            return

        brand_name = options.get('brand')
        if brand_name:
            brands = brands.filter(name=brand_name)
            if not brands.exists():
                self.stdout.write(self.style.ERROR(f'Brand "{brand_name}" not found.'))
                return

        for brand in brands:
            self.stdout.write(f'Creating analytics data for {brand.name}...')
            
            # Get brand campaigns
            campaigns = Campaign.objects.filter(brand=brand)
            if not campaigns.exists():
                self.stdout.write(f'No campaigns found for {brand.name}, skipping...')
                continue

            self.create_communities_for_brand(brand, campaigns)
            self.create_pain_points_for_brand(brand, campaigns)
            self.create_threads_for_brand(brand, campaigns)
            self.create_influencers_for_brand(brand, campaigns)

        self.stdout.write(self.style.SUCCESS('Detailed analytics data created successfully!'))

    def create_communities_for_brand(self, brand, campaigns):
        """Create communities relevant to the brand."""
        
        # BreezyCool communities
        if brand.name == 'BreezyCool':
            communities_data = [
                {'name': 'r/HVAC', 'platform': 'reddit', 'member_count': 125000, 'echo_score': 8.2, 'echo_score_change': 12.0},
                {'name': 'r/HomeImprovement', 'platform': 'reddit', 'member_count': 2500000, 'echo_score': 7.8, 'echo_score_change': 8.5},
                {'name': 'r/SmartHome', 'platform': 'reddit', 'member_count': 380000, 'echo_score': 6.9, 'echo_score_change': -2.1},
                {'name': 'discord:tech-reviews', 'platform': 'discord', 'member_count': 45000, 'echo_score': 9.1, 'echo_score_change': 15.3},
            ]
        elif brand.name == 'EcoVibe':
            communities_data = [
                {'name': 'r/ZeroWaste', 'platform': 'reddit', 'member_count': 890000, 'echo_score': 8.7, 'echo_score_change': 6.2},
                {'name': 'r/Sustainability', 'platform': 'reddit', 'member_count': 650000, 'echo_score': 7.9, 'echo_score_change': 3.4},
                {'name': 'tiktok:sustainability', 'platform': 'tiktok', 'member_count': 1200000, 'echo_score': 6.8, 'echo_score_change': -1.2},
            ]
        else:  # TechFlow
            communities_data = [
                {'name': 'r/SmartHome', 'platform': 'reddit', 'member_count': 380000, 'echo_score': 8.9, 'echo_score_change': 5.7},
                {'name': 'r/HomeAutomation', 'platform': 'reddit', 'member_count': 290000, 'echo_score': 8.1, 'echo_score_change': 8.1},
                {'name': 'discord:iot-community', 'platform': 'discord', 'member_count': 78000, 'echo_score': 7.4, 'echo_score_change': 2.3},
            ]

        for community_data in communities_data:
            community, created = Community.objects.get_or_create(
                name=community_data['name'],
                platform=community_data['platform'],
                defaults={
                    'url': f"https://{community_data['platform']}.com/{community_data['name']}",
                    'member_count': community_data['member_count'],
                    'echo_score': community_data['echo_score'],
                    'echo_score_change': community_data['echo_score_change'],
                    'description': f"{community_data['name']} community",
                    'category': brand.industry,
                    'is_active': True,
                    'last_analyzed': timezone.now()
                }
            )
            if created:
                self.stdout.write(f'  Created community: {community.name}')

    def create_pain_points_for_brand(self, brand, campaigns):
        """Create pain points for each brand."""
        
        if brand.name == 'BreezyCool':
            pain_points_data = [
                {'keyword': 'high energy bills', 'growth_percentage': 78.9, 'heat_level': 5, 'mention_count': 245},
                {'keyword': 'plastic packaging', 'growth_percentage': 67.3, 'heat_level': 4, 'mention_count': 189},
                {'keyword': 'smart home compatibility', 'growth_percentage': 45.8, 'heat_level': 3, 'mention_count': 156},
                {'keyword': 'installation difficulty', 'growth_percentage': 34.2, 'heat_level': 3, 'mention_count': 98},
            ]
        elif brand.name == 'EcoVibe':
            pain_points_data = [
                {'keyword': 'greenwashing', 'growth_percentage': 89.4, 'heat_level': 5, 'mention_count': 312},
                {'keyword': 'high prices', 'growth_percentage': 56.7, 'heat_level': 4, 'mention_count': 201},
                {'keyword': 'limited availability', 'growth_percentage': 42.1, 'heat_level': 3, 'mention_count': 143},
            ]
        else:  # TechFlow
            pain_points_data = [
                {'keyword': 'privacy concerns', 'growth_percentage': 92.3, 'heat_level': 5, 'mention_count': 287},
                {'keyword': 'setup complexity', 'growth_percentage': 67.8, 'heat_level': 4, 'mention_count': 198},
                {'keyword': 'device compatibility', 'growth_percentage': 51.2, 'heat_level': 4, 'mention_count': 165},
            ]

        # Get communities for this brand
        communities = Community.objects.filter(
            name__in=[source.split(':')[-1] if ':' in source else source for source in brand.sources]
        )
        
        # If no communities match, get any community 
        if not communities.exists():
            communities = Community.objects.all()[:3]

        for campaign in campaigns:
            for pain_data in pain_points_data:
                for community in communities:
                    pain_point, created = PainPoint.objects.get_or_create(
                        keyword=pain_data['keyword'],
                        campaign=campaign,
                        community=community,
                        defaults={
                            'mention_count': pain_data['mention_count'],
                            'growth_percentage': pain_data['growth_percentage'],
                            'heat_level': pain_data['heat_level'],
                            'sentiment_score': random.uniform(-0.5, -0.1),  # Pain points are generally negative
                            'example_content': f"Users discussing {pain_data['keyword']} in {community.name}",
                            'related_keywords': [pain_data['keyword'].replace(' ', '_'), f"{brand.name.lower()}_issue"],
                            'first_seen': timezone.now() - timedelta(days=random.randint(1, 30)),
                            'last_seen': timezone.now()
                        }
                    )
                    if created:
                        self.stdout.write(f'  Created pain point: {pain_point.keyword} in {community.name}')

    def create_threads_for_brand(self, brand, campaigns):
        """Create sample threads for communities."""
        
        communities = Community.objects.all()
        
        thread_templates = [
            {
                'title': f"Anyone tried {brand.name} products? Worth the hype?",
                'content': f"I've been seeing {brand.name} everywhere lately. Has anyone actually used their products? Curious about real user experiences.",
                'comment_count': random.randint(15, 85),
                'upvotes': random.randint(10, 150),
                'echo_score': random.uniform(6.0, 9.0),
                'sentiment_score': random.uniform(-0.2, 0.8)
            },
            {
                'title': f"Major issues with {brand.name} - buyer beware",
                'content': f"Bought from {brand.name} last month and having serious problems. Support is non-responsive. Avoid!",
                'comment_count': random.randint(25, 120),
                'upvotes': random.randint(5, 90),
                'echo_score': random.uniform(7.5, 9.5),
                'sentiment_score': random.uniform(-0.9, -0.3)
            },
            {
                'title': f"{brand.name} vs competitors - honest comparison",
                'content': f"Been researching options and {brand.name} seems promising. How do they compare to alternatives?",
                'comment_count': random.randint(30, 200),
                'upvotes': random.randint(20, 180),
                'echo_score': random.uniform(5.5, 8.0),
                'sentiment_score': random.uniform(-0.1, 0.6)
            }
        ]

        for campaign in campaigns:
            for community in communities[:3]:  # Create threads in first 3 communities
                for i, template in enumerate(thread_templates):
                    thread_id = f"{brand.name.lower()}_{community.name.replace('r/', '').replace(':', '_').replace('/', '_')}_{campaign.id}_{i+1}"
                    thread, created = Thread.objects.get_or_create(
                        thread_id=thread_id,
                        community=community,
                        campaign=campaign,
                        defaults={
                            'title': template['title'],
                            'content': template['content'],
                            'author': f"user_{random.randint(1000, 9999)}",
                            'author_karma': random.randint(100, 50000),
                            'comment_count': template['comment_count'],
                            'upvotes': template['upvotes'],
                            'downvotes': random.randint(0, template['upvotes'] // 3),
                            'echo_score': template['echo_score'],
                            'sentiment_score': template['sentiment_score'],
                            'llm_summary': f"Discussion about {brand.name} in {community.name} with mixed reactions.",
                            'token_count': random.randint(150, 800),
                            'processing_cost': Decimal(random.uniform(0.01, 0.15)),
                            'published_at': timezone.now() - timedelta(days=random.randint(1, 14)),
                            'engagement_rate': random.uniform(0.05, 0.25),
                            'controversy_score': random.uniform(0.1, 0.8)
                        }
                    )
                    if created:
                        self.stdout.write(f'  Created thread: {thread.title[:50]}...')

    def create_influencers_for_brand(self, brand, campaigns):
        """Create influencers for each brand."""
        
        if brand.name == 'BreezyCool':
            influencers_data = [
                {'username': 'may.tan', 'display_name': 'May Tan', 'platform': 'tiktok', 'reach': 41000, 'engagement_rate': 8.1, 'topics': 'transparency video'},
                {'username': 'SmartGuru', 'display_name': 'Smart Home Guru', 'platform': 'reddit', 'reach': 23000, 'engagement_rate': 12.4, 'topics': 'DIY collar fix'},
                {'username': 'ZHangCycle', 'display_name': 'Zhang Cycle', 'platform': 'youtube', 'reach': 17000, 'engagement_rate': 9.6, 'topics': 'sweat-wicking test'},
                {'username': 'SmartHomeGuru', 'display_name': 'Smart Home Expert', 'platform': 'reddit', 'reach': 28000, 'engagement_rate': 10.2, 'topics': 'HVAC reviews'},
            ]
        elif brand.name == 'EcoVibe':
            influencers_data = [
                {'username': 'EcoWarrior99', 'display_name': 'Eco Warrior', 'platform': 'reddit', 'reach': 35000, 'engagement_rate': 7.8, 'topics': 'sustainability tips'},
                {'username': 'GreenLifestyle', 'display_name': 'Green Lifestyle', 'platform': 'tiktok', 'reach': 48000, 'engagement_rate': 11.2, 'topics': 'zero waste living'},
                {'username': 'ZeroWasteJen', 'display_name': 'Zero Waste Jen', 'platform': 'instagram', 'reach': 22000, 'engagement_rate': 9.4, 'topics': 'eco products'},
            ]
        else:  # TechFlow
            influencers_data = [
                {'username': 'TechReviewer42', 'display_name': 'Tech Reviewer', 'platform': 'reddit', 'reach': 31000, 'engagement_rate': 8.7, 'topics': 'smart home tech'},
                {'username': 'IoTExpert', 'display_name': 'IoT Expert', 'platform': 'discord', 'reach': 19000, 'engagement_rate': 13.1, 'topics': 'home automation'},
                {'username': 'AutomationPro', 'display_name': 'Automation Pro', 'platform': 'youtube', 'reach': 26000, 'engagement_rate': 6.9, 'topics': 'smart devices'},
            ]

        # Get communities for the brand
        communities = Community.objects.all()

        for campaign in campaigns:
            for inf_data in influencers_data:
                # Assign to a random community
                community = random.choice(communities) if communities.exists() else None
                
                influencer, created = Influencer.objects.get_or_create(
                    username=inf_data['username'],
                    campaign=campaign,
                    source_type=inf_data['platform'],
                    defaults={
                        'community': community,
                        'display_name': inf_data['display_name'],
                        'profile_url': f"https://{inf_data['platform']}.com/{inf_data['username']}",
                        'reach': inf_data['reach'],
                        'engagement_rate': inf_data['engagement_rate'],
                        'karma_score': random.randint(1000, 15000),
                        'topics': [inf_data['topics']],
                        'last_active': timezone.now() - timedelta(days=random.randint(1, 7)),
                        'follower_count': inf_data['reach'],
                        'influence_score': random.uniform(0.6, 0.95),
                        'post_frequency': random.uniform(0.5, 3.0),
                        'avg_likes': random.uniform(50, 500),
                        'avg_comments': random.uniform(10, 80),
                        'content_topics': [inf_data['topics'], brand.industry.lower()],
                        'sentiment_distribution': {
                            'positive': random.uniform(0.4, 0.7),
                            'neutral': random.uniform(0.2, 0.4),
                            'negative': random.uniform(0.1, 0.3)
                        }
                    }
                )
                if created:
                    self.stdout.write(f'  Created influencer: {influencer.display_name}')
