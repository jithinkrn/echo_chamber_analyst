#!/bin/bash

# Script to properly run SHAP tests by handling test database cleanup

echo "======================================"
echo "SHAP Test Runner"
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

echo "Step 3: Running SHAP tests with --reuse-db flag..."
echo ""
pytest SHAP/ -v --reuse-db

echo ""
echo "======================================"
echo "Test run complete!"
echo "======================================"
