#!/bin/bash

# Script to properly run Security tests by handling test database cleanup

echo "======================================"
echo "Security Test Runner"
echo "======================================"
echo ""

# Kill any hanging pytest processes
echo "Step 1: Killing any hanging pytest processes..."
pkill -9 -f pytest 2>/dev/null || true
sleep 2

# Kill any python processes connected to test database
echo "Step 2: Checking for python processes using test database..."
pkill -9 -f "django.*test_echo" 2>/dev/null || true
sleep 1

# Drop test database if it exists to ensure clean state
echo "Step 3: Cleaning up test database..."
python manage.py flush --noinput --database=default 2>/dev/null || true
sleep 1

echo "Step 4: Running Security tests with --reuse-db flag..."
echo ""
pytest security_tests/ -v --reuse-db --tb=short

echo ""
echo "======================================"
echo "Test run complete!"
echo "======================================"
