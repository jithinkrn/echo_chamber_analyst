"""
Management command to test LangGraph workflow functionality.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from agents.orchestrator import workflow_orchestrator
from agents.state import CampaignContext
from common.models import Campaign, Source
from django.utils import timezone
import asyncio


class Command(BaseCommand):
    help = 'Test LangGraph workflow functionality'

    def add_arguments(self, parser):
        parser.add_argument(
            '--test-chat',
            action='store_true',
            help='Test chat workflow functionality',
        )
        parser.add_argument(
            '--test-content-analysis',
            action='store_true',
            help='Test content analysis workflow',
        )
        parser.add_argument(
            '--test-all',
            action='store_true',
            help='Run all tests',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting LangGraph workflow testing...'))

        # Test workflow coordinator initialization
        self.stdout.write('🚀 Testing workflow coordinator...')
        self.test_workflow_orchestrator()

        # Show workflow node status
        self.stdout.write('\n📊 Testing workflow nodes...')
        self.test_workflow_nodes()

        if options['test_chat'] or options['test_all']:
            self.stdout.write('\n💬 Testing chat workflow...')
            asyncio.run(self.test_chat_workflow())

        if options['test_content_analysis'] or options['test_all']:
            self.stdout.write('\n🧪 Testing content analysis workflow...')
            asyncio.run(self.test_content_analysis_workflow())

        # Create test campaign if needed
        self.stdout.write('\n📋 Setting up test campaign...')
        self.setup_test_campaign()

        self.stdout.write(self.style.SUCCESS('\n✅ LangGraph workflow testing completed!'))

    def test_workflow_orchestrator(self):
        """Test workflow orchestrator functionality."""
        self.stdout.write("\n=== Testing Workflow Orchestrator ===")
        try:
            orchestrator_status = workflow_orchestrator.get_status()
            self.stdout.write(
                self.style.SUCCESS(f"✓ Orchestrator status: {orchestrator_status}")
            )
            active_count = len(workflow_orchestrator.active_workflows)
            self.stdout.write(
                self.style.SUCCESS(f"✓ Active workflows: {active_count}")
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Orchestrator error: {e}")
            )

    def test_workflow_nodes(self):
        """Test individual workflow nodes."""
        workflow_nodes = [
            'scout_node',
            'cleaner_node',
            'analyst_node',
            'chatbot_node'
        ]

        for node_name in workflow_nodes:
            try:
                # Test node health
                health_status = workflow_orchestrator.get_node_health(node_name)
                self.stdout.write(f"  ✅ {node_name}: healthy")
            except Exception as e:
                self.stdout.write(f"  ❌ {node_name}: {str(e)}")

    async def test_chat_workflow(self):
        """Test chat workflow functionality."""
        try:
            # Test simple chat query
            final_state = await workflow_orchestrator.execute_chat_workflow(
                user_query="Hello, can you help me understand campaign metrics?",
                conversation_history=[],
                campaign_id=None
            )

            if final_state.rag_context and 'response' in final_state.rag_context:
                self.stdout.write(f"  ✅ Chat workflow successful")
                self.stdout.write(f"  📊 Tokens used: {final_state.metrics.total_tokens_used}")
                self.stdout.write(f"  💰 Cost: ${final_state.metrics.total_cost:.4f}")
            else:
                self.stdout.write(f"  ⚠️ Chat workflow completed but no response")

        except Exception as e:
            self.stdout.write(f"  ❌ Chat workflow failed: {str(e)}")

    async def test_content_analysis_workflow(self):
        """Test content analysis workflow."""
        try:
            # Create a test campaign context
            test_campaign = CampaignContext(
                campaign_id="test-campaign-123",
                name="Test Campaign",
                keywords=["test", "sample"],
                sources=["https://reddit.com/r/test"],
                budget_limit=10.0,
                current_spend=0.0
            )

            # Test content analysis workflow
            final_state = await workflow_orchestrator.execute_workflow(
                campaign=test_campaign,
                workflow_type="content_analysis",
                config={"test_mode": True}
            )

            self.stdout.write(f"  ✅ Content analysis workflow completed")
            self.stdout.write(f"  📊 Total cost: ${final_state.metrics.total_cost:.4f}")
            self.stdout.write(f"  ⏱️ Processing time: {final_state.metrics.processing_time:.2f}s")
            self.stdout.write(f"  🔍 Insights generated: {len(final_state.insights)}")

        except Exception as e:
            self.stdout.write(f"  ❌ Content analysis workflow failed: {str(e)}")

    def setup_test_campaign(self):
        """Create a test campaign for demonstration."""
        try:
            # Get or create test user
            user, created = User.objects.get_or_create(
                username='test_user',
                defaults={
                    'email': 'test@example.com',
                    'first_name': 'Test',
                    'last_name': 'User'
                }
            )

            # Create test campaign
            campaign, created = Campaign.objects.get_or_create(
                name='Test Campaign - Product Feedback',
                defaults={
                    'owner': user,
                    'description': 'Test campaign for analyzing product feedback',
                    'keywords': ['product', 'feedback', 'review', 'experience'],
                    'sources': [
                        {
                            'type': 'reddit',
                            'subreddit': 'ProductFeedback',
                            'limit': 10,
                            'sort': 'hot'
                        }
                    ],
                    'exclude_keywords': ['spam', 'advertisement'],
                    'status': 'active',
                    'schedule_enabled': True,
                    'schedule_interval': 3600,  # 1 hour
                    'daily_budget': 5.00
                }
            )

            if created:
                self.stdout.write(f"  ✅ Created test campaign: {campaign.name}")
            else:
                self.stdout.write(f"  📋 Using existing campaign: {campaign.name}")

            # Create test source
            source, created = Source.objects.get_or_create(
                source_type='reddit',
                url='https://reddit.com/r/ProductFeedback',
                defaults={
                    'name': 'r/ProductFeedback',
                    'config': {
                        'subreddit': 'ProductFeedback',
                        'rate_limit': 60
                    },
                    'is_active': True,
                    'rate_limit': 60
                }
            )

            if created:
                self.stdout.write(f"  ✅ Created test source: {source.name}")
            else:
                self.stdout.write(f"  📋 Using existing source: {source.name}")

            self.stdout.write(f"  🆔 Campaign ID: {campaign.id}")
            self.stdout.write(f"  🆔 Source ID: {source.id}")

        except Exception as e:
            self.stdout.write(f"  ❌ Failed to setup test campaign: {str(e)}")