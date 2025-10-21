#!/usr/bin/env python3
"""
Contract Test Runner

This script runs all contract tests for the Echo Chamber Analyst nodes
without impacting existing code. It provides comprehensive testing of:

- Scout Node: Data collection and validation
- Cleaner Node: Content cleaning and PII handling  
- Analyst Node: Content analysis and insights
- Chatbot Node: RAG functionality and conversation handling

Usage:
    python run_contract_tests.py [options]

Options:
    --node <node_name>     Run tests for specific node (scout|cleaner|analyst|chatbot)
    --verbose             Enable verbose output
    --coverage            Run with coverage reporting
    --performance         Include performance benchmarking
    --help               Show this help message
"""

import sys
import os
import unittest
import argparse
import time
from typing import Dict, Any, List
import json


def setup_test_environment():
    """Set up the test environment and paths"""
    # Add the backend directory to Python path
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)
    
    # Ensure tests directory is in path
    tests_dir = os.path.join(backend_dir, 'tests')
    if tests_dir not in sys.path:
        sys.path.insert(0, tests_dir)
    
    # Set environment variables for testing
    os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
    os.environ['TESTING'] = 'true'


def discover_test_modules() -> Dict[str, str]:
    """Discover available test modules"""
    test_modules = {
        'scout': 'contract_tests.test_scout_node_contracts',
        'cleaner': 'contract_tests.test_cleaner_node_contracts',
        'analyst': 'contract_tests.test_analyst_node_contracts',
        'chatbot': 'contract_tests.test_chatbot_node_contracts'
    }
    return test_modules


def run_node_tests(node_name: str, verbose: bool = False) -> Dict[str, Any]:
    """Run tests for a specific node"""
    test_modules = discover_test_modules()
    
    if node_name not in test_modules:
        raise ValueError(f"Unknown node: {node_name}. Available nodes: {list(test_modules.keys())}")
    
    print(f"\n{'='*60}")
    print(f"Running Contract Tests for {node_name.upper()} Node")
    print(f"{'='*60}")
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromName(test_modules[node_name])
    
    # Configure test runner
    verbosity = 2 if verbose else 1
    runner = unittest.TextTestRunner(
        verbosity=verbosity,
        stream=sys.stdout,
        buffer=True,
        descriptions=True
    )
    
    # Run tests and measure time
    start_time = time.time()
    result = runner.run(suite)
    end_time = time.time()
    
    # Compile results
    test_results = {
        'node': node_name,
        'tests_run': result.testsRun,
        'failures': len(result.failures),
        'errors': len(result.errors),
        'skipped': len(result.skipped) if hasattr(result, 'skipped') else 0,
        'success_rate': ((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100) if result.testsRun > 0 else 0,
        'execution_time_seconds': end_time - start_time,
        'success': result.wasSuccessful()
    }
    
    # Print summary
    print(f"\n{'-'*40}")
    print(f"Results for {node_name.upper()} Node:")
    print(f"Tests Run: {test_results['tests_run']}")
    print(f"Failures: {test_results['failures']}")
    print(f"Errors: {test_results['errors']}")
    print(f"Success Rate: {test_results['success_rate']:.1f}%")
    print(f"Execution Time: {test_results['execution_time_seconds']:.2f}s")
    print(f"Status: {'PASSED' if test_results['success'] else 'FAILED'}")
    
    # Show failure details if any
    if result.failures:
        print(f"\nFailures ({len(result.failures)}):")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback.split('AssertionError:')[-1].strip() if 'AssertionError:' in traceback else 'See details above'}")
    
    if result.errors:
        print(f"\nErrors ({len(result.errors)}):")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback.split('Exception:')[-1].strip() if 'Exception:' in traceback else 'See details above'}")
    
    return test_results


def run_all_tests(verbose: bool = False) -> Dict[str, Any]:
    """Run contract tests for all nodes"""
    test_modules = discover_test_modules()
    all_results = {}
    overall_start_time = time.time()
    
    print("\n" + "="*80)
    print("ECHO CHAMBER ANALYST - CONTRACT TEST SUITE")
    print("="*80)
    print("Testing all node contracts without impacting existing code...")
    
    for node_name in test_modules.keys():
        try:
            result = run_node_tests(node_name, verbose)
            all_results[node_name] = result
        except Exception as e:
            print(f"\nERROR: Failed to run tests for {node_name}: {e}")
            all_results[node_name] = {
                'node': node_name,
                'success': False,
                'error': str(e)
            }
    
    overall_end_time = time.time()
    
    # Generate overall summary
    total_tests = sum(r.get('tests_run', 0) for r in all_results.values())
    total_failures = sum(r.get('failures', 0) for r in all_results.values())
    total_errors = sum(r.get('errors', 0) for r in all_results.values())
    overall_success = all(r.get('success', False) for r in all_results.values())
    
    overall_results = {
        'summary': {
            'total_nodes_tested': len(test_modules),
            'total_tests_run': total_tests,
            'total_failures': total_failures,
            'total_errors': total_errors,
            'overall_success_rate': ((total_tests - total_failures - total_errors) / total_tests * 100) if total_tests > 0 else 0,
            'total_execution_time': overall_end_time - overall_start_time,
            'overall_success': overall_success
        },
        'node_results': all_results
    }
    
    # Print overall summary
    print(f"\n{'='*80}")
    print("OVERALL TEST RESULTS")
    print(f"{'='*80}")
    print(f"Nodes Tested: {overall_results['summary']['total_nodes_tested']}")
    print(f"Total Tests: {overall_results['summary']['total_tests_run']}")
    print(f"Total Failures: {overall_results['summary']['total_failures']}")
    print(f"Total Errors: {overall_results['summary']['total_errors']}")
    print(f"Overall Success Rate: {overall_results['summary']['overall_success_rate']:.1f}%")
    print(f"Total Time: {overall_results['summary']['total_execution_time']:.2f}s")
    print(f"Overall Status: {'ALL TESTS PASSED' if overall_success else 'SOME TESTS FAILED'}")
    
    # Node-by-node summary
    print(f"\nNode Summary:")
    for node_name, result in all_results.items():
        status = "PASSED" if result.get('success', False) else "FAILED"
        tests_run = result.get('tests_run', 0)
        success_rate = result.get('success_rate', 0)
        print(f"  {node_name.upper():>10}: {status} ({tests_run} tests, {success_rate:.1f}% success)")
    
    return overall_results


def run_performance_benchmark() -> Dict[str, Any]:
    """Run performance benchmarking on contract tests"""
    print("\n" + "="*60)
    print("PERFORMANCE BENCHMARK")
    print("="*60)
    
    test_modules = discover_test_modules()
    performance_results = {}
    
    for node_name in test_modules.keys():
        print(f"\nBenchmarking {node_name.upper()} Node...")
        
        # Run tests multiple times for average
        execution_times = []
        for run in range(3):
            start_time = time.time()
            try:
                # Load and run tests silently
                loader = unittest.TestLoader()
                suite = loader.loadTestsFromName(test_modules[node_name])
                runner = unittest.TextTestRunner(stream=open(os.devnull, 'w'))
                result = runner.run(suite)
                
                execution_time = time.time() - start_time
                execution_times.append(execution_time)
                
            except Exception as e:
                print(f"  Run {run + 1}: FAILED ({e})")
                continue
        
        if execution_times:
            avg_time = sum(execution_times) / len(execution_times)
            min_time = min(execution_times)
            max_time = max(execution_times)
            
            performance_results[node_name] = {
                'average_time': avg_time,
                'min_time': min_time,
                'max_time': max_time,
                'runs_completed': len(execution_times)
            }
            
            print(f"  Average: {avg_time:.3f}s")
            print(f"  Min: {min_time:.3f}s")
            print(f"  Max: {max_time:.3f}s")
        else:
            performance_results[node_name] = {'error': 'No successful runs'}
            print(f"  No successful benchmark runs")
    
    return performance_results


def save_results_to_file(results: Dict[str, Any], filename: str = None):
    """Save test results to JSON file"""
    if filename is None:
        timestamp = int(time.time())
        filename = f"contract_test_results_{timestamp}.json"
    
    filepath = os.path.join(os.path.dirname(__file__), filename)
    
    try:
        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\nResults saved to: {filepath}")
    except Exception as e:
        print(f"\nWarning: Could not save results to file: {e}")


def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(
        description="Run contract tests for Echo Chamber Analyst nodes",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_contract_tests.py                    # Run all tests
  python run_contract_tests.py --node scout      # Run only scout tests
  python run_contract_tests.py --verbose         # Verbose output
  python run_contract_tests.py --performance     # Include benchmarking
        """
    )
    
    parser.add_argument(
        '--node',
        choices=['scout', 'cleaner', 'analyst', 'chatbot'],
        help='Run tests for specific node only'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose test output'
    )
    parser.add_argument(
        '--performance', '-p',
        action='store_true',
        help='Include performance benchmarking'
    )
    parser.add_argument(
        '--save-results',
        metavar='FILENAME',
        help='Save results to JSON file (optional filename)'
    )
    
    args = parser.parse_args()
    
    # Setup environment
    setup_test_environment()
    
    try:
        if args.node:
            # Run tests for specific node
            results = run_node_tests(args.node, args.verbose)
            
            # Wrap single node result for consistency
            results = {
                'summary': {
                    'total_nodes_tested': 1,
                    'total_tests_run': results['tests_run'],
                    'overall_success': results['success']
                },
                'node_results': {args.node: results}
            }
        else:
            # Run all tests
            results = run_all_tests(args.verbose)
        
        # Performance benchmarking
        if args.performance:
            performance_results = run_performance_benchmark()
            results['performance_benchmark'] = performance_results
        
        # Save results if requested
        if args.save_results is not None:
            filename = args.save_results if args.save_results else None
            save_results_to_file(results, filename)
        
        # Exit with appropriate code
        success = results['summary']['overall_success']
        print(f"\nContract tests {'COMPLETED SUCCESSFULLY' if success else 'COMPLETED WITH FAILURES'}")
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n\nTest execution interrupted by user.")
        sys.exit(130)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()