#!/bin/bash
set -e

# Run tests and generate coverage report
echo "Running tests and generating coverage report..."
python run_tests.py

# Check if coverage.xml exists
if [ ! -f "coverage.xml" ]; then
    echo "Error: coverage.xml file not found!"
    exit 1
fi

# Print coverage file location for debugging
echo "Coverage file location: $(pwd)/coverage.xml"
echo "Coverage file contents (first 10 lines):"
head -n 10 coverage.xml

# Run SonarQube scan
echo "Running SonarQube scan..."
sonar-scanner

echo "SonarQube scan completed!"
