from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from common.models import Brand, Competitor, Campaign, Community, PainPoint, Thread, Influencer
from decimal import Decimal
import uuid


class Command(BaseCommand):
    help = 'Create test brands, competitors, and campaigns for development'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Creating test data...'))

        # Create or get admin user
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@example.com',
                'is_staff': True,
                'is_superuser': True
            }
        )
        if created:
            admin_user.set_password('puthiyathala123')
            admin_user.save()
            self.stdout.write(f'Created admin user: admin/puthiyathala123')

        # Create test brands
        brands_data = [
            {
                'name': 'BreezyCool',
                'description': 'Sustainable cooling solutions for modern homes',
                'website': 'https://breezycool.com',
                'industry': 'Home Appliances',
                'headquarters': 'San Francisco, CA',
                'social_handles': {
                    'twitter': '@BreezyCool',
                    'instagram': '@breezycool_official',
                    'linkedin': 'breezycool'
                },
                'primary_keywords': ['air conditioning', 'cooling', 'AC units', 'HVAC'],
                'product_keywords': ['smart AC', 'eco-friendly cooling', 'energy efficient'],
                'exclude_keywords': ['heating', 'winter', 'furnace'],
                'sources': ['r/HomeImprovement', 'r/HVAC', 'discord:tech-reviews']
            },
            {
                'name': 'TechFlow',
                'description': 'Smart home automation and IoT solutions',
                'website': 'https://techflow.io',
                'industry': 'Technology',
                'headquarters': 'Austin, TX',
                'social_handles': {
                    'twitter': '@TechFlowHQ',
                    'instagram': '@techflow_smart',
                    'linkedin': 'techflow-io'
                },
                'primary_keywords': ['smart home', 'IoT', 'automation', 'connected devices'],
                'product_keywords': ['smart switches', 'home hub', 'voice control'],
                'exclude_keywords': ['manual', 'traditional', 'analog'],
                'sources': ['r/SmartHome', 'r/HomeAutomation', 'discord:iot-community']
            },
            {
                'name': 'EcoVibe',
                'description': 'Sustainable lifestyle products and eco-friendly solutions',
                'website': 'https://ecovibe.green',
                'industry': 'Sustainability',
                'headquarters': 'Portland, OR',
                'social_handles': {
                    'twitter': '@EcoVibeGreen',
                    'instagram': '@ecovibe_lifestyle',
                    'tiktok': '@ecovibegreen'
                },
                'primary_keywords': ['sustainable', 'eco-friendly', 'green living', 'zero waste'],
                'product_keywords': ['biodegradable', 'renewable', 'organic', 'recycled'],
                'exclude_keywords': ['plastic', 'disposable', 'wasteful'],
                'sources': ['r/ZeroWaste', 'r/Sustainability', 'tiktok:sustainability']
            }
        ]

        created_brands = []
        for brand_data in brands_data:
            brand, created = Brand.objects.get_or_create(
                name=brand_data['name'],
                defaults=brand_data
            )
            created_brands.append(brand)
            status = 'Created' if created else 'Updated'
            self.stdout.write(f'{status} brand: {brand.name}')

        # Create competitors for each brand
        competitors_data = {
            'BreezyCool': [
                {
                    'name': 'CoolTech',
                    'description': 'Traditional AC manufacturer',
                    'website': 'https://cooltech.com',
                    'keywords': ['traditional AC', 'cooling systems', 'HVAC'],
                    'social_handles': {'twitter': '@cooltech'},
                    'market_share_estimate': 25.5,
                    'sentiment_comparison': -8.2
                },
                {
                    'name': 'ArcticAir',
                    'description': 'Premium cooling solutions',
                    'website': 'https://arcticair.com',
                    'keywords': ['premium AC', 'luxury cooling'],
                    'social_handles': {'instagram': '@arcticair_premium'},
                    'market_share_estimate': 15.3,
                    'sentiment_comparison': -12.1
                }
            ],
            'TechFlow': [
                {
                    'name': 'SmartConnect',
                    'description': 'IoT connectivity platform',
                    'website': 'https://smartconnect.tech',
                    'keywords': ['IoT platform', 'smart connectivity'],
                    'social_handles': {'linkedin': 'smartconnect-tech'},
                    'market_share_estimate': 30.2,
                    'sentiment_comparison': 5.7
                }
            ],
            'EcoVibe': [
                {
                    'name': 'GreenWave',
                    'description': 'Sustainable product marketplace',
                    'website': 'https://greenwave.earth',
                    'keywords': ['sustainable marketplace', 'green products'],
                    'social_handles': {'instagram': '@greenwave_earth'},
                    'market_share_estimate': 18.9,
                    'sentiment_comparison': -3.4
                }
            ]
        }

        for brand in created_brands:
            if brand.name in competitors_data:
                for comp_data in competitors_data[brand.name]:
                    comp_data['brand'] = brand
                    competitor, created = Competitor.objects.get_or_create(
                        brand=brand,
                        name=comp_data['name'],
                        defaults=comp_data
                    )
                    status = 'Created' if created else 'Updated'
                    self.stdout.write(f'  {status} competitor: {competitor.name}')

        # Create campaigns for each brand
        campaigns_data = [
            {
                'brand': 'BreezyCool',
                'campaigns': [
                    {
                        'name': 'Summer Cooling Campaign',
                        'description': 'Monitor summer AC discussions and energy efficiency concerns',
                        'keywords': ['summer cooling', 'energy bills', 'AC efficiency'],
                        'sources': ['r/HomeImprovement', 'r/HVAC'],
                        'daily_budget': Decimal('150.00'),
                        'current_spend': Decimal('87.50')
                    },
                    {
                        'name': 'Smart AC Feature Analysis',
                        'description': 'Track smart thermostat and IoT AC feature discussions',
                        'keywords': ['smart thermostat', 'WiFi AC', 'app control'],
                        'sources': ['r/SmartHome', 'discord:tech-reviews'],
                        'daily_budget': Decimal('100.00'),
                        'current_spend': Decimal('45.20')
                    }
                ]
            },
            {
                'brand': 'TechFlow',
                'campaigns': [
                    {
                        'name': 'Smart Home Trends',
                        'description': 'Monitor emerging smart home trends and user pain points',
                        'keywords': ['smart home setup', 'automation problems', 'device compatibility'],
                        'sources': ['r/SmartHome', 'r/HomeAutomation'],
                        'daily_budget': Decimal('200.00'),
                        'current_spend': Decimal('125.75')
                    }
                ]
            },
            {
                'brand': 'EcoVibe',
                'campaigns': [
                    {
                        'name': 'Zero Waste Movement',
                        'description': 'Track zero waste trends and sustainable product feedback',
                        'keywords': ['zero waste', 'plastic alternatives', 'sustainable swaps'],
                        'sources': ['r/ZeroWaste', 'tiktok:sustainability'],
                        'daily_budget': Decimal('75.00'),
                        'current_spend': Decimal('32.10')
                    }
                ]
            }
        ]

        for brand_campaigns in campaigns_data:
            brand = Brand.objects.get(name=brand_campaigns['brand'])
            for camp_data in brand_campaigns['campaigns']:
                camp_data['brand'] = brand
                camp_data['owner'] = admin_user
                campaign, created = Campaign.objects.get_or_create(
                    name=camp_data['name'],
                    brand=brand,
                    defaults=camp_data
                )
                status = 'Created' if created else 'Updated'
                self.stdout.write(f'  {status} campaign: {campaign.name}')

        # Create some sample communities
        communities_data = [
            {
                'name': 'r/HomeImprovement',
                'platform': 'reddit',
                'echo_score': 6.8,
                'member_count': 2500000,
                'description': 'DIY home improvement community'
            },
            {
                'name': 'r/HVAC',
                'platform': 'reddit',
                'echo_score': 7.2,
                'member_count': 145000,
                'description': 'HVAC professionals and enthusiasts'
            },
            {
                'name': 'r/SmartHome',
                'platform': 'reddit',
                'echo_score': 5.9,
                'member_count': 890000,
                'description': 'Smart home automation discussion'
            }
        ]

        for comm_data in communities_data:
            community, created = Community.objects.get_or_create(
                name=comm_data['name'],
                platform=comm_data['platform'],
                defaults=comm_data
            )
            status = 'Created' if created else 'Updated'
            self.stdout.write(f'{status} community: {community.name}')

        # Create sample pain points
        pain_points_data = [
            {
                'keyword': 'high energy bills',
                'growth_percentage': 67.3,
                'sentiment_score': -0.6,
                'heat_level': 4,
                'mention_count': 156,
                'example_content': 'Users complaining about rising AC costs in summer',
                'related_keywords': ['energy cost', 'electricity bill', 'AC expenses']
            },
            {
                'keyword': 'smart home compatibility',
                'growth_percentage': 45.8,
                'sentiment_score': -0.4,
                'heat_level': 3,
                'mention_count': 89,
                'example_content': 'Device compatibility issues in smart homes',
                'related_keywords': ['device integration', 'compatibility issues', 'setup problems']
            },
            {
                'keyword': 'plastic packaging',
                'growth_percentage': 78.9,
                'sentiment_score': -0.8,
                'heat_level': 5,
                'mention_count': 234,
                'example_content': 'Frustration with excessive plastic packaging',
                'related_keywords': ['wasteful packaging', 'plastic waste', 'eco packaging']
            }
        ]

        # Get some campaigns and communities to link pain points
        breezycool_campaign = Campaign.objects.filter(brand__name='BreezyCool').first()
        techflow_campaign = Campaign.objects.filter(brand__name='TechFlow').first()
        ecovibe_campaign = Campaign.objects.filter(brand__name='EcoVibe').first()
        
        hvac_community = Community.objects.filter(name='r/HVAC').first()
        smarthome_community = Community.objects.filter(name='r/SmartHome').first()
        homeimprovement_community = Community.objects.filter(name='r/HomeImprovement').first()

        # Link pain points to appropriate campaigns and communities
        pain_point_assignments = [
            (pain_points_data[0], breezycool_campaign, hvac_community),  # high energy bills
            (pain_points_data[1], techflow_campaign, smarthome_community),  # smart home compatibility
            (pain_points_data[2], ecovibe_campaign, homeimprovement_community)  # plastic packaging
        ]

        for pp_data, campaign, community in pain_point_assignments:
            if campaign and community:
                pp_data['campaign'] = campaign
                pp_data['community'] = community
                pain_point, created = PainPoint.objects.get_or_create(
                    keyword=pp_data['keyword'],
                    campaign=campaign,
                    community=community,
                    defaults=pp_data
                )
                status = 'Created' if created else 'Updated'
                self.stdout.write(f'{status} pain point: {pain_point.keyword}')

        # Create sample influencers
        influencers_data = [
            {
                'username': 'SmartHomeGuru',
                'display_name': 'Smart Home Guru',
                'source_type': 'reddit',
                'reach': 45000,
                'engagement_rate': 8.7,
                'karma_score': 12500,
                'topics': ['smart home', 'automation', 'tech reviews']
            },
            {
                'username': 'EcoWarrior',
                'display_name': 'Eco Warrior',
                'source_type': 'tiktok',
                'reach': 230000,
                'engagement_rate': 12.4,
                'karma_score': 8900,
                'topics': ['sustainability', 'zero waste', 'eco tips']
            }
        ]

        # Link influencers to campaigns and communities
        influencer_assignments = [
            (influencers_data[0], techflow_campaign, smarthome_community),  # SmartHomeGuru
            (influencers_data[1], ecovibe_campaign, homeimprovement_community)  # EcoWarrior
        ]

        for inf_data, campaign, community in influencer_assignments:
            if campaign and community:
                inf_data['campaign'] = campaign
                inf_data['community'] = community
                influencer, created = Influencer.objects.get_or_create(
                    username=inf_data['username'],
                    campaign=campaign,
                    defaults=inf_data
                )
                status = 'Created' if created else 'Updated'
                self.stdout.write(f'{status} influencer: {influencer.username}')

        self.stdout.write(
            self.style.SUCCESS('Successfully created test data!')
        )
        self.stdout.write('Summary:')
        self.stdout.write(f'- Brands: {Brand.objects.count()}')
        self.stdout.write(f'- Competitors: {Competitor.objects.count()}')
        self.stdout.write(f'- Campaigns: {Campaign.objects.count()}')
        self.stdout.write(f'- Communities: {Community.objects.count()}')
        self.stdout.write(f'- Pain Points: {PainPoint.objects.count()}')
        self.stdout.write(f'- Influencers: {Influencer.objects.count()}')