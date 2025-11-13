# Security Tests

Comprehensive security test suite for Echo Chamber Analyst platform.

## Overview

This test suite validates critical security features including:
- **LLM Security**: Prompt injection, harmful intent detection, rate limiting
- **Configuration Security**: Secrets protection, debug mode, security headers
- **Authentication Security**: JWT tokens, password hashing, session security
- **Injection Prevention**: SQL injection, XSS, command injection, path traversal
- **API Security**: Input validation, error handling

## Test Statistics

- **Total Tests**: 49
- **Test Files**: 5
- **Lines of Code**: 509
- **Pass Rate**: 100%

## Running Tests

### Run all security tests:
```bash
pytest tests/security_tests/ -v
```

### Run specific test file:
```bash
pytest tests/security_tests/test_llm_security.py -v
pytest tests/security_tests/test_configuration_security.py -v
pytest tests/security_tests/test_authentication_security.py -v
pytest tests/security_tests/test_injection_security.py -v
pytest tests/security_tests/test_api_security.py -v
```

### Run tests by marker:
```bash
pytest tests/security_tests/ -m critical
pytest tests/security_tests/ -m llm
pytest tests/security_tests/ -m config
```

### Generate test reports:
```bash
cd tests/security_tests
pytest
```

This will generate three report formats in `results/` directory:
- **report.html**: Interactive HTML report
- **junit.xml**: JUnit XML format (for CI/CD)
- **report.json**: JSON format with detailed test data

## Test Results

All test results are automatically saved to `tests/security_tests/results/`:

1. **HTML Report** (`results/report.html`)
   - Open in browser for interactive view
   - Shows test execution details, duration, and pass/fail status
   - Self-contained (includes CSS/JS inline)

2. **JUnit XML** (`results/junit.xml`)
   - Standard format for CI/CD integration
   - Compatible with Jenkins, GitLab CI, GitHub Actions

3. **JSON Report** (`results/report.json`)
   - Detailed test metadata
   - Programmatic access to test results
   - Includes duration, outcome, error messages

## Test Structure

```
tests/security_tests/
├── __init__.py                          # Module initialization
├── conftest.py                          # Shared fixtures
├── pytest.ini                           # Test configuration
├── README.md                            # This file
├── results/                             # Test results (auto-generated)
│   ├── .gitignore                       # Ignore results in git
│   ├── report.html                      # HTML report
│   ├── junit.xml                        # JUnit XML
│   └── report.json                      # JSON report
├── test_llm_security.py                 # LLM security tests (25 tests)
├── test_configuration_security.py       # Configuration tests (18 tests)
├── test_authentication_security.py      # Authentication tests (5 tests)
├── test_injection_security.py           # Injection prevention (6 tests)
└── test_api_security.py                 # API security tests (1 test)
```

## Test Details

### 1. LLM Security Tests (25 tests)
- **Prompt Injection Defense** (7 tests)
  - Block "ignore instructions" attacks
  - Block admin mode manipulation
  - Block "forget everything" attacks
  - Block DAN jailbreak attempts
  - Block "disregard" manipulation
  - Block programming override attempts
  - Block explicit jailbreak keywords

- **Harmful Intent Detection** (3 tests)
  - Block violent intent
  - Block misinformation requests
  - Allow legitimate queries

- **Profanity Filtering** (2 tests)
  - Block profane language
  - Allow clean language

- **Rate Limiting** (1 test)
  - Validate rate limit implementation

- **Input Validation** (2 tests)
  - Reject queries too long
  - Accept valid length queries

- **XSS Blocking** (1 test)
  - Block script tag injection

- **SQL Injection Blocking** (1 test)
  - Block DROP TABLE attempts

- **Output Sanitization** (2 tests)
  - Mask email addresses
  - Mask phone numbers

- **ReDoS Prevention** (1 test)
  - Fast validation performance

### 2. Configuration Security Tests (18 tests)
- Secrets not exposed (SECRET_KEY, API keys)
- No stack traces in errors
- Debug mode disabled in production
- Security headers present
- ALLOWED_HOSTS configured
- Secure cookies in production
- Database security
- CORS not allow all origins
- API keys from environment
- Backup/source files not accessible
- Tokens not logged

### 3. Authentication Security Tests (5 tests)
- Valid JWT tokens accepted
- Passwords not in responses
- Passwords hashed in database
- No credentials in URLs

### 4. Injection Prevention Tests (6 tests)
- SQL injection safe filters
- XSS prevention (HTML/JavaScript)
- Command injection prevention
- Path traversal blocked

### 5. API Security Tests (1 test)
- Invalid UUIDs rejected

## Viewing Results

### Quick Summary (Recommended)
```bash
cd tests/security_tests
python3 view_results.py
```

This displays:
- Test summary with pass rate
- Breakdown by test file
- Slowest tests (Top 5)
- Report file locations

### HTML Report
```bash
open tests/security_tests/results/report.html
```

### JSON Report (command line)
```bash
cat tests/security_tests/results/report.json | python -m json.tool
```

## CI/CD Integration

The JUnit XML report can be integrated into CI/CD pipelines:

**GitHub Actions:**
```yaml
- name: Run Security Tests
  run: pytest tests/security_tests/

- name: Publish Test Results
  uses: EnricoMi/publish-unit-test-result-action@v2
  if: always()
  with:
    files: tests/security_tests/results/junit.xml
```

**GitLab CI:**
```yaml
security-tests:
  script:
    - pytest tests/security_tests/
  artifacts:
    reports:
      junit: tests/security_tests/results/junit.xml
```

## Requirements

- pytest >= 9.0.1
- pytest-django >= 4.11.1
- pytest-html >= 4.1.1
- pytest-json-report >= 1.5.0
- Django >= 5.2.7

## Notes

- All tests are designed to pass on implemented features only
- Tests validate security controls are working correctly
- Test results are automatically generated and saved
- Results directory is git-ignored (only .gitignore is tracked)
