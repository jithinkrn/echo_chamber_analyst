#!/bin/bash

# Script to properly run Promptfoo tests by handling test database cleanup

echo "======================================"
echo "Promptfoo Security Test Runner"
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

# Check if Promptfoo is installed
echo "Step 3: Checking Promptfoo installation..."
if ! command -v npx &> /dev/null; then
    echo "❌ Error: npx is not installed. Please install Node.js first."
    exit 1
fi

echo "✅ Node.js and npx are available"

# Check if OpenAI API key is set
echo "Step 4: Checking OpenAI API key..."
if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️  Warning: OPENAI_API_KEY environment variable is not set"
    echo "   Some tests may fail or be skipped"
else
    echo "✅ OpenAI API key is configured"
fi

echo ""
echo "Step 5: Running Promptfoo tests with --reuse-db flag..."
echo ""
pytest Promptfoo/ -v --reuse-db -m "not slow"

echo ""
echo "======================================"
echo "Quick tests complete!"
echo ""
echo "To run comprehensive red team tests (takes 30+ minutes):"
echo "  pytest Promptfoo/ -v --reuse-db -m slow"
echo ""
echo "To run Promptfoo directly:"
echo "  cd Promptfoo"
echo "  npx promptfoo eval -c promptfooconfig-redteam-comprehensive.yaml"
echo "======================================"
