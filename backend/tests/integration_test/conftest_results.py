"""
Pytest plugin to record integration test results to JSON.
"""
import json
import time
from pathlib import Path
import pytest


# Store test results
test_results = {
    "test_type": "integration",
    "timestamp": None,
    "total_tests": 0,
    "passed": 0,
    "failed": 0,
    "skipped": 0,
    "errors": 0,
    "total_duration_seconds": 0.0,
    "by_module": {},
    "test_details": []
}

test_start_times = {}


def pytest_sessionstart(session):
    """Called before test session starts."""
    test_results["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
    test_results["session_start_time"] = time.time()


def pytest_runtest_setup(item):
    """Called before each test runs."""
    test_start_times[item.nodeid] = time.time()


def pytest_runtest_makereport(item, call):
    """Called after each test phase."""
    if call.when == "call":  # Only record the actual test call, not setup/teardown
        duration = time.time() - test_start_times.get(item.nodeid, time.time())

        # Get module name
        module_name = item.module.__name__.split('.')[-1]

        # Initialize module stats if not exists
        if module_name not in test_results["by_module"]:
            test_results["by_module"][module_name] = {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "duration": 0.0,
                "pass_rate": "0.0%"
            }

        # Update totals
        test_results["total_tests"] += 1
        test_results["by_module"][module_name]["total"] += 1
        test_results["by_module"][module_name]["duration"] += duration

        # Determine outcome
        if call.excinfo is None:
            outcome = "passed"
            test_results["passed"] += 1
            test_results["by_module"][module_name]["passed"] += 1
        elif call.excinfo.typename == "Skipped":
            outcome = "skipped"
            test_results["skipped"] += 1
            test_results["by_module"][module_name]["skipped"] += 1
        else:
            outcome = "failed"
            test_results["failed"] += 1
            test_results["by_module"][module_name]["failed"] += 1

        # Record test detail
        test_detail = {
            "name": item.name,
            "module": module_name,
            "outcome": outcome,
            "duration": round(duration, 3),
            "nodeid": item.nodeid
        }

        if call.excinfo:
            test_detail["error"] = str(call.excinfo.value)
            test_detail["error_type"] = call.excinfo.typename

        test_results["test_details"].append(test_detail)


def pytest_sessionfinish(session, exitstatus):
    """Called after test session finishes."""
    session_duration = time.time() - test_results.get("session_start_time", time.time())
    test_results["total_duration_seconds"] = round(session_duration, 2)

    # Calculate pass rates for each module
    for module_name, stats in test_results["by_module"].items():
        if stats["total"] > 0:
            pass_rate = (stats["passed"] / stats["total"]) * 100
            stats["pass_rate"] = f"{pass_rate:.1f}%"
        stats["duration"] = round(stats["duration"], 2)

    # Calculate overall pass rate
    if test_results["total_tests"] > 0:
        overall_pass_rate = (test_results["passed"] / test_results["total_tests"]) * 100
        test_results["overall_pass_rate"] = f"{overall_pass_rate:.1f}%"
    else:
        test_results["overall_pass_rate"] = "0.0%"

    # Save results to JSON
    results_file = Path(__file__).parent / "integration_test_results.json"
    with open(results_file, "w") as f:
        json.dump(test_results, f, indent=2)

    print(f"\n{'='*80}")
    print(f"Integration Test Results Summary")
    print(f"{'='*80}")
    print(f"Total Tests: {test_results['total_tests']}")
    print(f"✅ Passed: {test_results['passed']}")
    print(f"❌ Failed: {test_results['failed']}")
    print(f"⏭️  Skipped: {test_results['skipped']}")
    print(f"📊 Pass Rate: {test_results['overall_pass_rate']}")
    print(f"⏱️  Duration: {test_results['total_duration_seconds']}s")
    print(f"\n{'='*80}")
    print(f"Results by Module:")
    print(f"{'='*80}")
    for module_name, stats in test_results["by_module"].items():
        print(f"\n{module_name}:")
        print(f"  Total: {stats['total']}, Passed: {stats['passed']}, Failed: {stats['failed']}, Skipped: {stats['skipped']}")
        print(f"  Pass Rate: {stats['pass_rate']}, Duration: {stats['duration']}s")
    print(f"\n{'='*80}")
    print(f"📄 Full results saved to: {results_file}")
    print(f"{'='*80}\n")
