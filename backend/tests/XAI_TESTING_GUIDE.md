# XAI Testing Guide for Echo Chamber Analyst

## Overview

This guide covers all Explainable AI (XAI), Fairness, and Security testing for the Echo Chamber Analyst platform.

## 🎯 Test Suites

### 1. AIF360 - Fairness Testing
**Location:** `tests/AIF360/`
**Tests:** 4 tests
**Duration:** ~4 minutes

Tests LLM fairness across different demographics:
- Industry fairness (Technology vs other industries)
- Budget fairness (Large vs Small/Medium budgets)
- Platform fairness (Reddit, Twitter, Discord)

**Metrics Tested:**
- Statistical Parity Difference (SPD)
- Disparate Impact Ratio (DI)
- Equal Opportunity Difference

**Run Command:**
```bash
./run_aif360_tests.sh
```

---

### 2. SHAP - Feature Importance
**Location:** `tests/SHAP/`
**Tests:** 3 tests
**Duration:** ~6 minutes

Explains which features influence LLM insight generation:
- Sentiment scores
- Echo chamber scores
- Pain point counts
- Engagement rates
- Mention volumes

**Run Command:**
```bash
./run_shap_tests.sh
```

---

### 3. LIME - Text Explainability
**Location:** `tests/LIME/`
**Tests:** 4 tests
**Duration:** ~1 minute

Explains which words/phrases influence LLM decisions:
- Pain point text importance
- Keyword attributions
- Text explainer structure
- Urgent vs minor comparisons

**Run Command:**
```bash
./run_lime_tests.sh
```

---

### 4. Promptfoo - Security Testing
**Location:** `tests/Promptfoo/`
**Tests:** 18+ quick tests, 40+ comprehensive plugins
**Duration:** < 1 minute (quick), 30+ minutes (comprehensive)

Comprehensive security and safety testing:

#### Security Tests:
- Prompt injection & extraction
- PII exposure (direct, API, session, social)
- System manipulation
- Data leakage

#### Safety Tests:
- Harmful content (40+ categories)
- Illegal activities
- Hate speech & harassment
- Sensitive content
- Weapons & dangerous materials

#### Attack Strategies:
- Basic attacks
- Jailbreak attempts
- Encoding bypasses (ROT13, Base64, Leetspeak)
- Multilingual attacks
- Crescendo attacks

**Run Commands:**
```bash
# Quick tests (< 1 minute)
./run_promptfoo_tests.sh

# Comprehensive red team (30+ minutes)
pytest tests/Promptfoo/ -v --reuse-db -m slow
```

---

## 🚀 Running All Tests

Run all XAI test suites sequentially:
```bash
./run_all_xai_tests.sh
```

This master script:
- Cleans up processes
- Runs all 4 test suites
- Provides summary statistics
- Reports total time and pass/fail rates

---

## 📊 Test Results

Results are saved to:
```
tests/
├── AIF360/results/
│   ├── aif360_test_results.json
│   ├── brand_fairness_results.json
│   └── campaign_fairness_results.json
├── SHAP/results/
│   └── shap_test_results.json
├── LIME/results/
│   └── lime_test_results.json
└── Promptfoo/results/
    ├── promptfoo_test_results.json
    └── redteam/
        └── redteam-results.json
```

---

## 🔧 Configuration

### Database Setup
All tests use the same test database:
- Database: `test_echo_chamber_analyst`
- Connection handled by Django's test framework
- Automatically created and cleaned up
- Uses `--reuse-db` flag to avoid conflicts

### Environment Variables
```bash
# Required for Promptfoo security tests
export OPENAI_API_KEY="sk-..."

# Django settings (auto-configured)
export DJANGO_SETTINGS_MODULE="config.settings"
```

---

## 📈 Understanding Results

### AIF360 Results
- **SPD < 0.1**: Fair treatment across groups
- **0.8 < DI < 1.2**: Passes 80% rule (no discrimination)
- Values outside these ranges indicate potential bias

### SHAP Results
- Feature importance scores (positive = increases urgency)
- SHAP values show contribution of each metric
- Waterfall plots explain individual predictions

### LIME Results
- Word importance scores for text inputs
- Positive scores = increase urgency classification
- Negative scores = decrease urgency classification

### Promptfoo Results
- ✅ **Pass**: Model correctly refused/handled attack
- ❌ **Fail**: Model exposed data or violated policy
- ⚠️ **Warning**: Borderline case needing review

---

## 🛡️ Security Best Practices

Based on test results:

1. **Prompt Engineering**
   - Never include credentials in system prompts
   - Use environment variables for sensitive config
   - Implement prompt filtering

2. **Data Protection**
   - Validate all outputs for PII
   - Implement data masking
   - Use access controls

3. **Content Filtering**
   - Enable OpenAI moderation API
   - Add custom safety classifiers
   - Post-process responses

4. **RAG Security**
   - Validate retrieved context
   - Sanitize user queries
   - Use similarity thresholds

---

## 🔄 CI/CD Integration

Add to your GitHub Actions workflow:

```yaml
name: XAI Testing

on: [push, pull_request]

jobs:
  xai-tests:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v2

      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt

      - name: Run XAI Tests
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          cd backend
          ./run_all_xai_tests.sh
        timeout-minutes: 60
```

---

## 📚 Test Architecture

### Test Database Strategy
All tests use the same approach:
1. Kill hanging processes
2. Clean up database connections
3. Run with `--reuse-db` flag
4. Share test database across runs

### Django Integration
- Uses `pytest-django` plugin
- Fixtures create real Django models
- Tests interact with actual database
- Automatic cleanup after tests

### Production Code Testing
All tests use REAL production code:
```python
from agents.analyst import generate_ai_powered_insights_from_brand_analytics
```

This ensures tests validate actual behavior, not mocks.

---

## 🐛 Troubleshooting

### Database Connection Errors
```bash
# Error: "database is being accessed by other users"
pkill -9 -f pytest
pkill -9 -f "django.*test_echo"
```

### Promptfoo Not Found
```bash
# Install Node.js and Promptfoo
npm install -g promptfoo
# Or use npx (auto-installs)
npx promptfoo --version
```

### OpenAI API Rate Limits
```yaml
# In promptfooconfig.yaml, set:
evaluateOptions:
  maxConcurrency: 1  # Reduce parallel requests
```

### Slow Tests
```bash
# Skip slow Promptfoo tests
pytest tests/Promptfoo/ -v -m "not slow"
```

---

## 📖 Additional Resources

### Documentation
- [AIF360 Docs](https://aif360.readthedocs.io/)
- [SHAP Docs](https://shap.readthedocs.io/)
- [LIME Docs](https://github.com/marcotcr/lime)
- [Promptfoo Docs](https://promptfoo.dev/docs)

### Research Papers
- AIF360: "AI Fairness 360: An Extensible Toolkit" (IBM Research, 2018)
- SHAP: "A Unified Approach to Interpreting Model Predictions" (Lundberg & Lee, 2017)
- LIME: "Why Should I Trust You?" (Ribeiro et al., 2016)

---

## 🤝 Contributing

To add new tests:

1. Create test file in appropriate directory
2. Use existing fixtures from `conftest.py`
3. Follow naming convention: `test_*.py`
4. Add to test runner script if needed
5. Document in this guide

---

## 📝 Test Coverage Summary

| Test Suite | Tests | Duration | Purpose |
|------------|-------|----------|---------|
| AIF360 | 4 | 4 min | Fairness across demographics |
| SHAP | 3 | 6 min | Feature importance |
| LIME | 4 | 1 min | Text explainability |
| Promptfoo (Quick) | 18 | < 1 min | Basic security checks |
| Promptfoo (Full) | 200+ | 30+ min | Comprehensive red team |
| **Total** | **229+** | **~40 min** | **Complete XAI coverage** |

---

## ✅ Checklist for Production

Before deploying to production:

- [ ] All AIF360 fairness tests pass
- [ ] SHAP feature importance validated
- [ ] LIME text explanations reviewed
- [ ] Promptfoo quick tests pass
- [ ] Promptfoo comprehensive red team completed
- [ ] No critical security vulnerabilities found
- [ ] Fairness metrics within acceptable thresholds
- [ ] Documentation updated
- [ ] CI/CD pipeline configured

---

## 📧 Support

For questions or issues:
- Review test output logs
- Check `results/` directories
- Consult individual test README files
- Review Django test database setup

---

**Last Updated:** 2025-11-14
**Version:** 1.0
**Maintained by:** Echo Chamber Analyst Team
