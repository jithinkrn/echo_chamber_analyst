#!/bin/bash

# Script to properly run Promptfoo tests by handling test database cleanup

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  Promptfoo Security & RAG Quality Test Runner                 ║"
echo "║  (Production Code Integration Tests)                          ║"
echo "╚════════════════════════════════════════════════════════════════╝"
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
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  Running Test Suite 1: RAG Quality Tests                      ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "Testing REAL PRODUCTION CODE:"
echo "  ✅ Guardrails (monitoring_integration.py)"
echo "  ✅ IntentClassifier (rag_tool.py)"
echo "  ✅ RAGTool (rag_tool.py)"
echo "  ✅ Vector Search Tools (vector_tools.py)"
echo ""
pytest Promptfoo/test_rag_quality.py -v --reuse-db

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  Running Test Suite 2: Red Team Security (Quick Tests)        ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "Testing MULTI-LAYERED SECURITY:"
echo "  🛡️  Layer 1: Regex-based validation (60+ patterns)"
echo "  🛡️  Layer 2: LLM-based safety flagging"
echo "  🛡️  Layer 3: Response boundary enforcement"
echo ""
pytest Promptfoo/test_redteam_with_guardrails.py -v --reuse-db -m "not slow"

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  Test Results Summary                                          ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "📊 Results saved to:"
echo "   - RAG Quality:      Promptfoo/results/rag_quality_results.json"
echo "   - Red Team:         Promptfoo/results/redteam/redteam_guardrails_summary.json"
echo "   - Defense Layers:   Promptfoo/results/redteam/defense_in_depth_results.json"
echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  Additional Testing Options                                    ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "To run COMPREHENSIVE red team tests (takes 30+ minutes):"
echo "  pytest Promptfoo/test_redteam_with_guardrails.py -v --reuse-db -m slow"
echo ""
echo "To run Promptfoo CLI directly for custom tests:"
echo "  cd Promptfoo"
echo "  npx promptfoo eval -c promptfooconfig-redteam-comprehensive.yaml"
echo ""
echo "To view detailed test reports:"
echo "  cd Promptfoo/results"
echo "  cat rag_quality_results.json"
echo "  cat redteam/redteam_guardrails_summary.json"
echo ""
echo "════════════════════════════════════════════════════════════════"
