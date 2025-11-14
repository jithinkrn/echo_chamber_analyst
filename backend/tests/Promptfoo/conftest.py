"""
Pytest configuration for Promptfoo LLM quality tests.
"""

import pytest
import os
import sys
import json

# Add backend to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))


# Pytest plugin to capture and save results
class PromptfooResultsPlugin:
    """Plugin to capture Promptfoo test results."""

    def __init__(self):
        from datetime import datetime
        self.results = {
            "test_suite": "Promptfoo LLM Quality Tests",
            "timestamp": datetime.now().isoformat(),
            "tests_run": [],
            "summary": {
                "total": 0,
                "passed": 0,
                "failed": 0
            },
            "note": "These are pytest tests. For full LLM testing, run: promptfoo eval -c promptfooconfig.yaml"
        }

    def pytest_runtest_logreport(self, report):
        """Capture test results."""
        if report.when == 'call':
            test_info = {
                "name": report.nodeid,
                "outcome": report.outcome,
                "duration": report.duration
            }

            if report.outcome == 'failed':
                test_info['error'] = str(report.longrepr)

            self.results['tests_run'].append(test_info)
            self.results['summary']['total'] += 1

            if report.outcome == 'passed':
                self.results['summary']['passed'] += 1
            elif report.outcome == 'failed':
                self.results['summary']['failed'] += 1

    def pytest_sessionfinish(self, session, exitstatus):
        """Save results to JSON files."""
        results_dir = os.path.join(os.path.dirname(__file__), 'results')
        os.makedirs(results_dir, exist_ok=True)

        # Save overall results
        overall_file = os.path.join(results_dir, 'promptfoo_test_results.json')
        with open(overall_file, 'w') as f:
            json.dump(self.results, f, indent=2)

        print(f"\n📊 Promptfoo test results saved to: {results_dir}/")
        print(f"   - Overall: {self.results['summary']['passed']}/{self.results['summary']['total']} passed")
        print(f"   - Note: For full LLM testing, run: promptfoo eval -c promptfooconfig.yaml")


def pytest_configure(config):
    """Register the results plugin and custom markers."""
    # Register custom markers
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )

    # Register results plugin
    plugin = PromptfooResultsPlugin()
    config.pluginmanager.register(plugin, "promptfoo_results")
