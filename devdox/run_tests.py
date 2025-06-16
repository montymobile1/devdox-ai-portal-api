#!/usr/bin/env python
import coverage
import os
import sys
import pytest

# Start code coverage collection
cov = coverage.Coverage(
    source=["app"],
    omit=[
        "*/__pycache__/*",
        "*/tests/*",
        "*/migrations/*",
    ],
)
cov.start()

# Run pytest
pytest_args = [
    "tests",  # test directory
    "-v",  # verbose
    "--tb=short",  # shorter traceback
]
exit_code = pytest.main(pytest_args)

# Stop coverage and generate reports
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

# Generate XML report for SonarQube
cov.xml_report(outfile="coverage.xml")

print(f"\nHTML coverage report generated in {cov_dir}/")
print(f"XML coverage report generated in coverage.xml")

# Show absolute path for debugging
coverage_file = os.path.abspath("../coverage.xml")
print(f"Absolute path to coverage report: {coverage_file}")

# Exit with pytest's exit code
sys.exit(exit_code)
