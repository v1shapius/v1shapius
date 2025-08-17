#!/usr/bin/env python3
"""
Test runner script for Discord Rating Bot
Runs all tests with coverage and generates reports
"""

import subprocess
import sys
import os
import argparse

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"\n🔄 {description}...")
    print(f"Command: {' '.join(command)}")
    
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        if result.stdout:
            print("Output:")
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed with exit code {e.returncode}")
        if e.stdout:
            print("Stdout:")
            print(e.stdout)
        if e.stderr:
            print("Stderr:")
            print(e.stderr)
        return False

def main():
    """Main test runner function"""
    parser = argparse.ArgumentParser(description="Run Discord Rating Bot tests")
    parser.add_argument("--unit", action="store_true", help="Run unit tests only")
    parser.add_argument("--integration", action="store_true", help="Run integration tests only")
    parser.add_argument("--coverage", action="store_true", help="Run tests with coverage")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--parallel", action="store_true", help="Run tests in parallel")
    
    args = parser.parse_args()
    
    print("🧪 Discord Rating Bot Test Runner")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not os.path.exists("bot.py"):
        print("❌ Error: Please run this script from the project root directory")
        sys.exit(1)
    
    # Install test dependencies if needed
    print("\n📦 Checking test dependencies...")
    try:
        import pytest
        import pytest_asyncio
        print("✅ Test dependencies are installed")
    except ImportError:
        print("📥 Installing test dependencies...")
        if not run_command([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], "Installing dependencies"):
            print("❌ Failed to install dependencies")
            sys.exit(1)
    
    # Build test command
    test_command = [sys.executable, "-m", "pytest"]
    
    if args.unit:
        test_command.extend(["--markers", "unit"])
        print("🎯 Running unit tests only")
    elif args.integration:
        test_command.extend(["--markers", "integration"])
        print("🎯 Running integration tests only")
    else:
        print("🎯 Running all tests")
    
    if args.coverage:
        test_command.extend([
            "--cov=.",
            "--cov-report=html",
            "--cov-report=term-missing",
            "--cov-config=.coveragerc"
        ])
        print("📊 Coverage reporting enabled")
    
    if args.verbose:
        test_command.append("-v")
    
    if args.parallel:
        test_command.extend(["-n", "auto"])
        print("⚡ Parallel execution enabled")
    
    # Add test paths
    test_command.extend([
        "tests/",
        "--tb=short",
        "--strict-markers",
        "--disable-warnings"
    ])
    
    # Run tests
    print(f"\n🚀 Starting test execution...")
    success = run_command(test_command, "Test execution")
    
    if success:
        print("\n🎉 All tests completed successfully!")
        
        if args.coverage:
            print("\n📊 Coverage reports generated:")
            print("- HTML report: htmlcov/index.html")
            print("- Terminal report: See above")
        
        sys.exit(0)
    else:
        print("\n💥 Some tests failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()