#!/usr/bin/env python3
"""
Test runner script for invoice automation system
Provides convenient ways to run different test suites
"""
import sys
import subprocess
import argparse


def run_command(cmd):
    """Run a command and return exit code"""
    print(f"Running: {' '.join(cmd)}")
    print("-" * 80)
    result = subprocess.run(cmd, capture_output=False, text=True)
    return result.returncode


def main():
    parser = argparse.ArgumentParser(description='Run tests for invoice automation system')
    parser.add_argument(
        'suite',
        nargs='?',
        default='all',
        choices=['all', 'unit', 'integration', 'e2e', 'commands', 'quick'],
        help='Test suite to run (default: all)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output'
    )
    parser.add_argument(
        '--coverage', '-c',
        action='store_true',
        help='Generate coverage report'
    )
    parser.add_argument(
        '--failfast', '-x',
        action='store_true',
        help='Stop on first failure'
    )
    parser.add_argument(
        '--marker', '-m',
        help='Run tests with specific marker'
    )
    parser.add_argument(
        '--file', '-f',
        help='Run specific test file'
    )
    
    args = parser.parse_args()
    
    # Base pytest command
    cmd = ['pytest']
    
    # Add options
    if args.verbose:
        cmd.append('-vv')
    else:
        cmd.append('-v')
    
    if args.failfast:
        cmd.append('-x')
    
    if args.coverage:
        cmd.extend(['--cov=invoice_automation', '--cov-report=term-missing'])
    
    # Select test suite
    if args.file:
        cmd.append(args.file)
    elif args.marker:
        cmd.extend(['-m', args.marker])
    elif args.suite == 'unit':
        cmd.append('tests/test_unit.py')
    elif args.suite == 'integration':
        cmd.append('tests/test_integration.py')
    elif args.suite == 'e2e':
        cmd.append('tests/test_e2e.py')
    elif args.suite == 'commands':
        cmd.append('tests/test_commands.py')
    elif args.suite == 'quick':
        # Quick tests exclude slow e2e tests
        cmd.extend(['-m', 'not slow'])
    # else 'all' runs everything
    
    # Run the tests
    exit_code = run_command(cmd)
    
    if exit_code == 0:
        print("\n✅ All tests passed!")
    else:
        print(f"\n❌ Tests failed with exit code {exit_code}")
    
    return exit_code


if __name__ == '__main__':
    sys.exit(main())