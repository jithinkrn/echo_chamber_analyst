#!/bin/bash

# Master script to run all XAI (Explainability & Security) tests

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  Echo Chamber Analyst - XAI Test Suite                        ║"
echo "║  (Explainability, Fairness & Security Testing)                ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Track results
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
TOTAL_TIME=0

# Function to run a test suite
run_test_suite() {
    local name=$1
    local script=$2
    local description=$3

    echo ""
    echo "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo "${BLUE}  Running: $name${NC}"
    echo "${BLUE}  $description${NC}"
    echo "${BLUE}═══════════════════════════════════════════════════════════${NC}"

    START_TIME=$(date +%s)

    if [ -x "$script" ]; then
        ./"$script"
        EXIT_CODE=$?

        END_TIME=$(date +%s)
        DURATION=$((END_TIME - START_TIME))
        TOTAL_TIME=$((TOTAL_TIME + DURATION))

        if [ $EXIT_CODE -eq 0 ]; then
            echo "${GREEN}✅ $name: PASSED${NC} (${DURATION}s)"
            PASSED_TESTS=$((PASSED_TESTS + 1))
        else
            echo "${RED}❌ $name: FAILED${NC} (exit code: $EXIT_CODE)"
            FAILED_TESTS=$((FAILED_TESTS + 1))
        fi
        TOTAL_TESTS=$((TOTAL_TESTS + 1))
    else
        echo "${RED}❌ Script not found or not executable: $script${NC}"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        TOTAL_TESTS=$((TOTAL_TESTS + 1))
    fi
}

# Kill any hanging processes
echo "${YELLOW}🔧 Cleaning up processes...${NC}"
pkill -9 -f pytest 2>/dev/null || true
pkill -9 -f "django.*test_echo" 2>/dev/null || true
sleep 2

# Run each test suite
run_test_suite \
    "AIF360 Fairness Tests" \
    "run_aif360_tests.sh" \
    "Tests LLM fairness across industries and budgets"

run_test_suite \
    "SHAP Explainability Tests" \
    "run_shap_tests.sh" \
    "Tests feature importance for LLM insights"

run_test_suite \
    "LIME Text Explainability Tests" \
    "run_lime_tests.sh" \
    "Tests word-level attributions for text analysis"

run_test_suite \
    "Promptfoo Security Tests" \
    "run_promptfoo_tests.sh" \
    "Tests prompt injection, PII leakage, and safety"

# Print summary
echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                    TEST SUITE SUMMARY                          ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "  Total Test Suites: $TOTAL_TESTS"

if [ $PASSED_TESTS -gt 0 ]; then
    echo "  ${GREEN}✅ Passed: $PASSED_TESTS${NC}"
fi

if [ $FAILED_TESTS -gt 0 ]; then
    echo "  ${RED}❌ Failed: $FAILED_TESTS${NC}"
fi

MINUTES=$((TOTAL_TIME / 60))
SECONDS=$((TOTAL_TIME % 60))
echo "  ⏱️  Total Time: ${MINUTES}m ${SECONDS}s"
echo ""

# Print detailed results locations
echo "📊 Results saved to:"
echo "   - AIF360:    AIF360/results/"
echo "   - SHAP:      SHAP/results/"
echo "   - LIME:      LIME/results/"
echo "   - Promptfoo: Promptfoo/results/"
echo ""

# Exit with appropriate code
if [ $FAILED_TESTS -gt 0 ]; then
    echo "${RED}❌ Some test suites failed. Please review the output above.${NC}"
    exit 1
else
    echo "${GREEN}✅ All XAI test suites passed successfully!${NC}"
    exit 0
fi
