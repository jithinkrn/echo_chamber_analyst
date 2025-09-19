"""
Management command to add comprehensive test data for chatbot functionality.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from common.models import Campaign, Source, RawContent, ProcessedContent, Insight
from django.utils import timezone
import uuid


class Command(BaseCommand):
    help = 'Add comprehensive test data for chatbot functionality'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear-existing',
            action='store_true',
            help='Clear existing test data before adding new data',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Adding test data for chatbot...'))

        if options['clear_existing']:
            self.stdout.write('Clearing existing test data...')
            Insight.objects.filter(campaign__name__icontains='Test').delete()
            ProcessedContent.objects.filter(raw_content__campaign__name__icontains='Test').delete()
            RawContent.objects.filter(campaign__name__icontains='Test').delete()
            Campaign.objects.filter(name__icontains='Test').delete()
            self.stdout.write(self.style.SUCCESS('✅ Cleared existing test data'))

        try:
            # Create test user
            user, created = User.objects.get_or_create(
                username='testuser',
                defaults={
                    'email': 'test@example.com',
                    'first_name': 'Test',
                    'last_name': 'User'
                }
            )
            if created:
                self.stdout.write(f"✅ Created test user: {user.username}")
            else:
                self.stdout.write(f"📋 Using existing user: {user.username}")

            # Create test campaign
            campaign, created = Campaign.objects.get_or_create(
                name='Test Campaign - Product Feedback Analysis',
                defaults={
                    'owner': user,
                    'description': 'Test campaign for analyzing product feedback and reviews',
                    'keywords': ['product', 'feedback', 'review', 'experience', 'quality', 'features'],
                    'sources': ['reddit', 'discord'],
                    'exclude_keywords': ['spam', 'advertisement'],
                    'status': 'active'
                }
            )
            if created:
                self.stdout.write(f"✅ Created test campaign: {campaign.name}")
            else:
                self.stdout.write(f"📋 Using existing campaign: {campaign.name}")

            # Create test source
            source, created = Source.objects.get_or_create(
                source_type='reddit',
                url='https://reddit.com/r/ProductFeedback',
                defaults={
                    'name': 'Reddit Product Feedback',
                    'config': {'subreddit': 'ProductFeedback'},
                    'is_active': True
                }
            )
            if created:
                self.stdout.write(f"✅ Created test source: {source.name}")

            # Create test raw content entries
            raw_content_data = [
                {
                    'external_id': 'reddit_123',
                    'title': 'Amazing product experience!',
                    'content': 'I\'ve been using this product for 3 months now and I\'m incredibly impressed with the quality and features. The user interface is intuitive and the performance is outstanding.',
                    'author': 'happy_customer_01',
                    'sentiment': 0.8
                },
                {
                    'external_id': 'reddit_124',
                    'title': 'Some feedback on recent updates',
                    'content': 'The recent update brought some great new features, but I\'ve noticed a few bugs in the notification system. Overall still a great product though.',
                    'author': 'beta_tester_02',
                    'sentiment': 0.6
                },
                {
                    'external_id': 'reddit_125',
                    'title': 'Feature request: Dark mode',
                    'content': 'Would love to see a dark mode option added to the interface. It would make using the product in low-light environments much more comfortable.',
                    'author': 'night_owl_user',
                    'sentiment': 0.4
                },
                {
                    'external_id': 'reddit_126',
                    'title': 'Excellent customer support',
                    'content': 'Had an issue with my account and the customer support team resolved it within hours. Very professional and helpful service.',
                    'author': 'satisfied_customer',
                    'sentiment': 0.9
                },
                {
                    'external_id': 'reddit_127',
                    'title': 'Performance improvements needed',
                    'content': 'The product works well overall, but I\'ve noticed some performance issues during peak usage times. Loading times can be quite slow.',
                    'author': 'power_user_03',
                    'sentiment': 0.3
                }
            ]

            self.stdout.write('Creating test content...')
            for data in raw_content_data:
                # Create raw content
                raw_content, created = RawContent.objects.get_or_create(
                    external_id=data['external_id'],
                    defaults={
                        'source': source,
                        'campaign': campaign,
                        'url': f"https://reddit.com/r/ProductFeedback/comments/{data['external_id']}",
                        'title': data['title'],
                        'content': data['content'],
                        'author': data['author'],
                        'published_at': timezone.now(),
                        'metadata': {'platform': 'reddit', 'upvotes': 25}
                    }
                )

                if created:
                    # Create corresponding processed content
                    processed_content = ProcessedContent.objects.create(
                        raw_content=raw_content,
                        cleaned_content=data['content'],
                        sentiment_score=data['sentiment'],
                        toxicity_score=0.1,
                        keywords=['product', 'feedback', 'review'],
                        topics=['product_feedback', 'user_experience']
                    )
                    self.stdout.write(f"  ✅ Created content: {data['title'][:50]}...")

            # Create test insights
            insights_data = [
                {
                    'title': 'Overall Positive Product Sentiment',
                    'type': 'sentiment_analysis',
                    'content': 'Analysis of recent feedback shows 70% positive sentiment towards the product. Users particularly appreciate the quality and user interface design.',
                    'confidence': 0.85
                },
                {
                    'title': 'Feature Request Trends',
                    'type': 'feature_analysis',
                    'content': 'Dark mode is the most requested feature, mentioned in 15% of feedback. Performance improvements are also frequently mentioned.',
                    'confidence': 0.78
                },
                {
                    'title': 'Customer Support Excellence',
                    'type': 'support_analysis',
                    'content': 'Customer support receives consistently high ratings with 95% positive feedback. Response times average under 2 hours.',
                    'confidence': 0.92
                },
                {
                    'title': 'Performance Concerns Identified',
                    'type': 'issue_detection',
                    'content': 'Some users report performance issues during peak times. This affects approximately 12% of user feedback and should be prioritized.',
                    'confidence': 0.73
                }
            ]

            self.stdout.write('Creating test insights...')
            for data in insights_data:
                insight, created = Insight.objects.get_or_create(
                    title=data['title'],
                    defaults={
                        'campaign': campaign,
                        'insight_type': data['type'],
                        'description': data['content'],
                        'confidence_score': data['confidence'],
                        'tags': ['test_data'],
                        'metadata': {'auto_generated': True, 'test_data': True}
                    }
                )
                if created:
                    self.stdout.write(f"  ✅ Created insight: {data['title']}")

            # Print summary
            self.stdout.write('\n📊 Test data summary:')
            self.stdout.write(f"  Campaigns: {Campaign.objects.filter(name__icontains='Test').count()}")
            self.stdout.write(f"  Raw Content: {RawContent.objects.filter(campaign=campaign).count()}")
            self.stdout.write(f"  Processed Content: {ProcessedContent.objects.filter(raw_content__campaign=campaign).count()}")
            self.stdout.write(f"  Insights: {Insight.objects.filter(campaign=campaign).count()}")
            
            self.stdout.write(f"\n🆔 Test Campaign ID: {campaign.id}")
            self.stdout.write(self.style.SUCCESS('\n✅ Test data added successfully!'))
            self.stdout.write(self.style.SUCCESS('🤖 Chatbot should now be able to answer questions about product feedback.'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Failed to add test data: {str(e)}'))
            raise e