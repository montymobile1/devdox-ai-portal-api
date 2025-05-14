#!/usr/bin/env python
import unittest
import coverage
import os
import sys

# Start code coverage collection
cov = coverage.Coverage(
    source=["app"],
    omit=[
        "*/__pycache__/*",
        "*/tests/*",
        "*/migrations/*",
    ]
)
cov.start()

# Discover and run tests
loader = unittest.TestLoader()
start_dir = "tests"
pattern = "test_*.py"

suite = loader.discover(start_dir, pattern=pattern)
runner = unittest.TextTestRunner(verbosity=2)
result = runner.run(suite)

# Stop coverage and generate report
cov.stop()
cov.save()

# Print coverage report to console
print("\nCoverage Summary:")
cov.report()

# Generate HTML coverage report
cov_dir = "htmlcov"
if not os.path.exists(cov_dir):
    os.makedirs(cov_dir)
cov.html_report(directory=cov_dir)

# Generate XML report for SonarQube - removed unsupported parameter
cov.xml_report(outfile="coverage.xml")

print(f"\nHTML coverage report generated in {cov_dir}/")
print(f"XML coverage report generated in coverage.xml")

# Show coverage path for debugging
coverage_file = os.path.abspath("coverage.xml")
print(f"Absolute path to coverage report: {coverage_file}")

# Return non-zero exit code if tests failed
sys.exit(not result.wasSuccessful())
