#!/usr/bin/env python3
"""
Test runner script for LeaderOracle backend.
Provides easy commands to run different test suites with coverage reporting.
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

def run_command(cmd, description=""):
    """Run a command and handle errors."""
    print(f"\n{'='*60}")
    print(f"Running: {description or cmd}")
    print(f"{'='*60}")
    
    result = subprocess.run(cmd, shell=True, capture_output=False)
    
    if result.returncode != 0:
        print(f"\n❌ Command failed: {cmd}")
        return False
    else:
        print(f"\n✅ Command succeeded: {description or cmd}")
        return True

def run_unit_tests():
    """Run unit tests only."""
    cmd = "pytest tests/ -m unit -v --tb=short"
    return run_command(cmd, "Unit Tests")

def run_integration_tests():
    """Run integration tests only."""
    cmd = "pytest tests/ -m integration -v --tb=short"
    return run_command(cmd, "Integration Tests")

def run_all_tests():
    """Run all tests."""
    cmd = "pytest tests/ -v --tb=short"
    return run_command(cmd, "All Tests")

def run_tests_with_coverage():
    """Run tests with coverage reporting."""
    cmd = "pytest tests/ -v --cov=api --cov-report=term-missing --cov-report=html --cov-report=xml --cov-fail-under=80"
    return run_command(cmd, "Tests with Coverage")

def run_tests_parallel():
    """Run tests in parallel for faster execution."""
    cmd = "pytest tests/ -v -n auto --tb=short"
    return run_command(cmd, "Parallel Tests")

def run_specific_test(test_path):
    """Run a specific test file or test function."""
    cmd = f"pytest {test_path} -v --tb=short"
    return run_command(cmd, f"Specific Test: {test_path}")

def run_linting():
    """Run code linting."""
    commands = [
        ("flake8 api/ --max-line-length=100 --ignore=E203,W503", "Flake8 Linting"),
        ("black --check api/ tests/", "Black Code Formatting Check"),
        ("mypy api/ --ignore-missing-imports", "MyPy Type Checking"),
    ]
    
    all_passed = True
    for cmd, description in commands:
        if not run_command(cmd, description):
            all_passed = False
    
    return all_passed

def generate_coverage_report():
    """Generate detailed coverage report."""
    print("\n" + "="*60)
    print("Generating Coverage Report")
    print("="*60)
    
    # Run tests with coverage
    if run_tests_with_coverage():
        print("\n📊 Coverage report generated:")
        print("  - Terminal: See output above")
        print("  - HTML: Open htmlcov/index.html in your browser")
        print("  - XML: coverage.xml file created")
        return True
    return False

def setup_test_environment():
    """Set up test environment."""
    print("\n" + "="*60)
    print("Setting up Test Environment")
    print("="*60)
    
    # Install test dependencies
    if not run_command("pip install -e .", "Install Package in Development Mode"):
        return False
    
    # Create test directories if they don't exist
    test_dirs = ["tests", "htmlcov", "logs"]
    for dir_name in test_dirs:
        Path(dir_name).mkdir(exist_ok=True)
    
    print("\n✅ Test environment setup complete")
    return True

def run_performance_tests():
    """Run performance tests."""
    cmd = "pytest tests/ -m slow -v --tb=short"
    return run_command(cmd, "Performance Tests")

def main():
    """Main test runner."""
    parser = argparse.ArgumentParser(description="LeaderOracle Backend Test Runner")
    parser.add_argument("--unit", action="store_true", help="Run unit tests only")
    parser.add_argument("--integration", action="store_true", help="Run integration tests only")
    parser.add_argument("--all", action="store_true", help="Run all tests")
    parser.add_argument("--coverage", action="store_true", help="Run tests with coverage")
    parser.add_argument("--parallel", action="store_true", help="Run tests in parallel")
    parser.add_argument("--lint", action="store_true", help="Run code linting")
    parser.add_argument("--setup", action="store_true", help="Set up test environment")
    parser.add_argument("--performance", action="store_true", help="Run performance tests")
    parser.add_argument("--report", action="store_true", help="Generate coverage report")
    parser.add_argument("--test", type=str, help="Run specific test file or function")
    parser.add_argument("--ci", action="store_true", help="Run CI pipeline (all checks)")
    
    args = parser.parse_args()
    
    # Default to all tests if no specific option is provided
    if not any(vars(args).values()):
        args.all = True
    
    success = True
    
    try:
        # Set up environment if requested
        if args.setup:
            if not setup_test_environment():
                success = False
        
        # Run linting if requested
        if args.lint:
            if not run_linting():
                success = False
        
        # Run specific test
        if args.test:
            if not run_specific_test(args.test):
                success = False
        
        # Run unit tests
        if args.unit:
            if not run_unit_tests():
                success = False
        
        # Run integration tests
        if args.integration:
            if not run_integration_tests():
                success = False
        
        # Run all tests
        if args.all:
            if not run_all_tests():
                success = False
        
        # Run tests with coverage
        if args.coverage:
            if not run_tests_with_coverage():
                success = False
        
        # Run parallel tests
        if args.parallel:
            if not run_tests_parallel():
                success = False
        
        # Run performance tests
        if args.performance:
            if not run_performance_tests():
                success = False
        
        # Generate coverage report
        if args.report:
            if not generate_coverage_report():
                success = False
        
        # Run CI pipeline
        if args.ci:
            print("\n🚀 Running CI Pipeline...")
            ci_success = True
            
            # Run linting
            if not run_linting():
                ci_success = False
            
            # Run all tests with coverage
            if not run_tests_with_coverage():
                ci_success = False
            
            # Run performance tests
            if not run_performance_tests():
                ci_success = False
            
            if ci_success:
                print("\n🎉 CI Pipeline Passed!")
            else:
                print("\n❌ CI Pipeline Failed!")
                success = False
        
        # Final status
        if success:
            print("\n🎉 All tests completed successfully!")
            sys.exit(0)
        else:
            print("\n❌ Some tests failed!")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error running tests: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 