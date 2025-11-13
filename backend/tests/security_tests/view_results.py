#!/usr/bin/env python3
"""
View Security Test Results

Simple script to display test results from the JSON report.
"""
import json
import sys
from pathlib import Path
from datetime import datetime


def format_duration(seconds):
    """Format duration in human-readable format."""
    if seconds < 1:
        return f"{seconds*1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.2f}s"
    else:
        minutes = int(seconds / 60)
        secs = seconds % 60
        return f"{minutes}m {secs:.1f}s"


def main():
    # Load JSON report
    report_path = Path(__file__).parent / "results" / "report.json"

    if not report_path.exists():
        print("❌ No test results found. Run tests first with: pytest")
        sys.exit(1)

    with open(report_path) as f:
        data = json.load(f)

    # Display summary
    print("\n" + "="*70)
    print("SECURITY TEST RESULTS".center(70))
    print("="*70 + "\n")

    summary = data.get("summary", {})
    total = summary.get("total", 0)
    passed = summary.get("passed", 0)

    # Calculate pass rate
    pass_rate = (passed / total * 100) if total > 0 else 0

    print(f"📊 Test Summary:")
    print(f"   Total Tests:  {total}")
    print(f"   Passed:       {passed} ✅")
    print(f"   Pass Rate:    {pass_rate:.1f}%")
    print(f"   Duration:     {format_duration(data.get('duration', 0))}")
    print()

    # Test breakdown by file
    print(f"📁 Test Breakdown by File:")
    print()

    tests_by_file = {}
    for test in data.get("tests", []):
        nodeid = test.get("nodeid", "")
        filename = nodeid.split("::")[0] if "::" in nodeid else "unknown"

        if filename not in tests_by_file:
            tests_by_file[filename] = {"total": 0, "passed": 0, "duration": 0}

        tests_by_file[filename]["total"] += 1
        if test.get("outcome") == "passed":
            tests_by_file[filename]["passed"] += 1
        tests_by_file[filename]["duration"] += test.get("call", {}).get("duration", 0)

    # Display by file
    for filename in sorted(tests_by_file.keys()):
        stats = tests_by_file[filename]
        rate = (stats["passed"] / stats["total"] * 100) if stats["total"] > 0 else 0
        duration = format_duration(stats["duration"])

        status = "✅" if rate == 100 else "⚠️"
        print(f"   {status} {filename:40s} {stats['passed']:2d}/{stats['total']:2d} ({rate:5.1f}%) - {duration}")

    print()

    # Slowest tests
    print(f"🐌 Slowest Tests (Top 5):")
    print()

    tests = data.get("tests", [])
    slowest = sorted(tests, key=lambda t: t.get("call", {}).get("duration", 0), reverse=True)[:5]

    for i, test in enumerate(slowest, 1):
        duration = test.get("call", {}).get("duration", 0)
        nodeid = test.get("nodeid", "")
        testname = nodeid.split("::")[-1] if "::" in nodeid else nodeid
        classname = nodeid.split("::")[-2] if nodeid.count("::") >= 2 else ""

        print(f"   {i}. {classname}::{testname}")
        print(f"      Duration: {format_duration(duration)}")

    print()

    # Report files
    print(f"📄 Report Files:")
    results_dir = Path(__file__).parent / "results"
    print(f"   HTML Report:  {results_dir / 'report.html'}")
    print(f"   JUnit XML:    {results_dir / 'junit.xml'}")
    print(f"   JSON Report:  {results_dir / 'report.json'}")
    print()

    # View HTML report
    print(f"💡 To view the HTML report, run:")
    print(f"   open {results_dir / 'report.html'}")
    print()
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
