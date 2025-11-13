"""
Pytest configuration for unit tests with result recording.
"""
import pytest
import json
import os
from datetime import datetime
from unittest.mock import Mock, MagicMock

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()


@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch):
    """Mock environment variables for all tests."""
    monkeypatch.setenv('OPENAI_API_KEY', 'test-key-123')
    monkeypatch.setenv('TAVILY_API_KEY', 'test-tavily-key-123')
    monkeypatch.setenv('LANGSMITH_API_KEY', 'test-langsmith-key-123')
    monkeypatch.setenv('DATABASE_URL', 'sqlite:///:memory:')
    monkeypatch.setenv('REDIS_URL', 'redis://localhost:6379')


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI ChatCompletion client."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = '{"intent_type": "conversational", "confidence": 0.9}'
    mock_response.usage.prompt_tokens = 100
    mock_response.usage.completion_tokens = 50
    mock_client.invoke.return_value = mock_response
    return mock_client


@pytest.fixture
def mock_tavily_client():
    """Mock Tavily search client."""
    mock_client = MagicMock()
    mock_client.search.return_value = {
        'results': [
            {
                'url': 'https://reddit.com/r/test/post1',
                'content': 'Test content about pricing concerns',
                'title': 'Pricing Discussion',
                'published_date': '2025-01-15'
            }
        ]
    }
    return mock_client


@pytest.fixture
def mock_brand():
    """Mock Brand model instance."""
    from common.models import Brand
    brand = Mock(spec=Brand)
    brand.id = 1
    brand.name = "Test Brand"
    brand.industry = "Technology"
    brand.description = "A test technology brand"
    return brand


@pytest.fixture
def mock_campaign():
    """Mock Campaign model instance."""
    from common.models import Campaign
    campaign = Mock(spec=Campaign)
    campaign.id = 1
    campaign.name = "Test Campaign"
    campaign.campaign_type = "automatic"
    campaign.status = "active"
    campaign.brand_id = 1
    campaign.metadata = {}
    return campaign


@pytest.fixture
def mock_thread():
    """Mock Thread model instance."""
    from common.models import Thread
    thread = Mock(spec=Thread)
    thread.id = 1
    thread.campaign_id = 1
    thread.content = "Users are complaining about high pricing"
    thread.sentiment_score = -0.5
    thread.embedding = [0.1] * 1536
    return thread


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Hook to capture test results for JSON export."""
    outcome = yield
    report = outcome.get_result()

    if report.when == "call":
        # Store result for JSON export
        if not hasattr(item.config, '_test_results'):
            item.config._test_results = []

        # Extract agent name from test file name
        test_file = item.nodeid.split('::')[0]
        if 'test_' in test_file:
            agent = test_file.split('test_')[-1].replace('_agent.py', '').replace('.py', '')
        else:
            agent = 'unknown'

        item.config._test_results.append({
            'test_name': item.nodeid,
            'test_function': item.name,
            'agent': agent,
            'status': report.outcome,
            'duration': round(report.duration, 4),
            'timestamp': datetime.now().isoformat(),
            'longrepr': str(report.longrepr) if report.failed else None
        })


def pytest_sessionfinish(session, exitstatus):
    """Save results to JSON after all tests complete."""
    if hasattr(session.config, '_test_results'):
        results = session.config._test_results

        # Calculate summary statistics
        summary = {
            'timestamp': datetime.now().isoformat(),
            'exit_status': exitstatus,
            'total_tests': len(results),
            'passed': len([r for r in results if r['status'] == 'passed']),
            'failed': len([r for r in results if r['status'] == 'failed']),
            'skipped': len([r for r in results if r['status'] == 'skipped']),
            'total_duration_seconds': round(sum(r['duration'] for r in results), 2),
            'by_agent': {},
            'details': results
        }

        # Aggregate by agent
        for result in results:
            agent = result['agent']
            if agent not in summary['by_agent']:
                summary['by_agent'][agent] = {
                    'total': 0,
                    'passed': 0,
                    'failed': 0,
                    'skipped': 0,
                    'duration': 0
                }
            summary['by_agent'][agent]['total'] += 1
            if result['status'] == 'passed':
                summary['by_agent'][agent]['passed'] += 1
            elif result['status'] == 'failed':
                summary['by_agent'][agent]['failed'] += 1
            elif result['status'] == 'skipped':
                summary['by_agent'][agent]['skipped'] += 1
            summary['by_agent'][agent]['duration'] = round(
                summary['by_agent'][agent]['duration'] + result['duration'], 2
            )

        # Calculate pass rates
        for agent_stats in summary['by_agent'].values():
            if agent_stats['total'] > 0:
                agent_stats['pass_rate'] = round(
                    (agent_stats['passed'] / agent_stats['total']) * 100, 1
                )

        # Save to JSON
        output_dir = os.path.join(
            os.path.dirname(__file__),
            'test_results.json'
        )
        with open(output_dir, 'w') as f:
            json.dump(summary, f, indent=2)

        # Print summary
        print("\n" + "=" * 80)
        print("📊 UNIT TEST RESULTS SUMMARY")
        print("=" * 80)
        print(f"Total Tests:     {summary['total_tests']}")
        print(f"✅ Passed:       {summary['passed']}")
        print(f"❌ Failed:       {summary['failed']}")
        print(f"⏭️  Skipped:      {summary['skipped']}")
        print(f"⏱️  Duration:     {summary['total_duration_seconds']}s")
        print(f"📈 Pass Rate:    {round((summary['passed'] / summary['total_tests'] * 100), 1)}%")
        print("\n" + "-" * 80)
        print("BY AGENT:")
        print("-" * 80)
        for agent, stats in summary['by_agent'].items():
            print(f"  {agent.upper():<20} {stats['passed']}/{stats['total']} ({stats['pass_rate']}%) - {stats['duration']}s")
        print("=" * 80)
        print(f"✅ Results saved to: {output_dir}")
        print("=" * 80)
