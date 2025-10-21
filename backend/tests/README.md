# Contract Tests for Echo Chamber Analyst

This directory contains comprehensive contract tests for all major nodes in the Echo Chamber Analyst system. These tests verify that each component adheres to its expected interface and behavior without impacting the existing codebase.

## Overview

The contract tests validate the following nodes:
- **Scout Node**: Data collection from Reddit, forums, and review platforms
- **Cleaner Node**: Content sanitization, PII removal, and quality filtering
- **Analyst Node**: Sentiment analysis, trend detection, and insight generation
- **Chatbot Node**: RAG functionality, conversation handling, and response generation

## Test Structure

```
tests/
├── __init__.py                              # Test package initialization
├── contract_tests/
│   ├── __init__.py                          # Contract tests package
│   ├── test_scout_node_contracts.py         # Scout node contract tests
│   ├── test_cleaner_node_contracts.py       # Cleaner node contract tests
│   ├── test_analyst_node_contracts.py       # Analyst node contract tests
│   ├── test_chatbot_node_contracts.py       # Chatbot node contract tests
│   └── test_fixtures.py                     # Shared test utilities and data
└── run_contract_tests.py                    # Test runner script
```

## Running the Tests

### Quick Start

Run all contract tests:
```bash
cd backend/tests
python run_contract_tests.py
```

### Specific Node Tests

Run tests for a specific node:
```bash
# Scout node only
python run_contract_tests.py --node scout

# Cleaner node only
python run_contract_tests.py --node cleaner

# Analyst node only
python run_contract_tests.py --node analyst

# Chatbot node only
python run_contract_tests.py --node chatbot
```

### Advanced Options

Verbose output:
```bash
python run_contract_tests.py --verbose
```

Include performance benchmarking:
```bash
python run_contract_tests.py --performance
```

Save results to file:
```bash
python run_contract_tests.py --save-results contract_results.json
```

### Using Standard unittest

You can also run individual test files directly:
```bash
# Run scout tests only
python -m unittest contract_tests.test_scout_node_contracts -v

# Run specific test method
python -m unittest contract_tests.test_scout_node_contracts.TestScoutNodeContracts.test_scout_config_validation_contract -v
```

## Test Categories

### Scout Node Contracts

**File**: `test_scout_node_contracts.py`

Tests the scout node's contract for:
- ✅ Configuration validation and parameter handling
- ✅ Reddit data collection and API integration
- ✅ Forum data scraping and processing
- ✅ Review platform data extraction
- ✅ Pain point identification and categorization
- ✅ Data aggregation and deduplication
- ✅ Error handling and retry mechanisms
- ✅ Performance characteristics and timeouts
- ✅ Data persistence and storage contracts

Key contract validations:
- Input configuration structure and validation
- Output data format consistency
- Error response standardization
- Performance threshold compliance
- Data quality assurance

### Cleaner Node Contracts

**File**: `test_cleaner_node_contracts.py`

Tests the cleaner node's contract for:
- ✅ PII (Personally Identifiable Information) detection
- ✅ Content sanitization and filtering
- ✅ Spam detection and classification
- ✅ Content quality validation
- ✅ Deduplication algorithms
- ✅ Data retention policy compliance
- ✅ Batch processing capabilities
- ✅ Configuration validation
- ✅ Performance metrics and monitoring

Key contract validations:
- PII removal accuracy and completeness
- Content safety and sanitization
- Quality scoring consistency
- Processing pipeline reliability
- Configuration parameter validation

### Analyst Node Contracts

**File**: `test_analyst_node_contracts.py`

Tests the analyst node's contract for:
- ✅ Sentiment analysis across different content types
- ✅ Trend analysis and time-series processing
- ✅ Competitive analysis and benchmarking
- ✅ Topic modeling and keyword extraction
- ✅ Pain point analysis and categorization
- ✅ Insight generation and recommendation systems
- ✅ Statistical analysis and correlation detection
- ✅ Real-time analysis capabilities
- ✅ Export functionality and data formatting

Key contract validations:
- Sentiment scoring accuracy and consistency
- Trend detection algorithm reliability
- Insight quality and actionability
- Statistical analysis correctness
- Performance optimization compliance

### Chatbot Node Contracts

**File**: `test_chatbot_node_contracts.py`

Tests the chatbot node's contract for:
- ✅ RAG (Retrieval-Augmented Generation) pipeline
- ✅ Query processing and intent recognition
- ✅ Context retrieval and relevance scoring
- ✅ Response generation and quality control
- ✅ Conversation state management
- ✅ Safety filtering and content moderation
- ✅ Knowledge base search and integration
- ✅ Multi-turn conversation handling
- ✅ Fallback and error handling mechanisms

Key contract validations:
- RAG pipeline accuracy and reliability
- Response quality and coherence
- Safety filter effectiveness
- Conversation context maintenance
- Fallback mechanism robustness

## Test Utilities

### Test Fixtures (`test_fixtures.py`)

Provides comprehensive utilities for contract testing:

**TestDataGenerator**: Creates realistic test data
- `generate_threads()`: Mock thread data with varied sentiment
- `generate_knowledge_base()`: Mock knowledge base entries
- `generate_pain_points()`: Realistic pain point scenarios

**MockUtilities**: Simulation and mocking helpers
- `simulate_processing_time()`: Realistic timing simulation
- `generate_confidence_score()`: Confidence score generation
- `mock_api_response()`: API response mocking
- `simulate_rate_limit()`: Rate limiting simulation

**ContractTestValidators**: Contract compliance validation
- `validate_response_structure()`: Structure validation
- `validate_score_range()`: Score range validation
- `validate_timestamp_format()`: Timestamp validation
- `validate_list_structure()`: List structure validation

**PerformanceTestHelpers**: Performance testing utilities
- `measure_execution_time()`: Execution time measurement
- `generate_performance_baseline()`: Performance baselines

**ConfigurationTestHelpers**: Configuration testing
- `generate_valid_configs()`: Valid configuration examples
- `generate_invalid_configs()`: Invalid configuration test cases

## Contract Specifications

### Input/Output Contracts

All nodes must adhere to standardized input/output contracts:

**Standard Input Structure**:
```python
{
    "config": {
        # Node-specific configuration
    },
    "data": {
        # Input data payload
    },
    "metadata": {
        "timestamp": "ISO-8601",
        "request_id": "unique_id",
        "source": "originating_component"
    }
}
```

**Standard Output Structure**:
```python
{
    "success": boolean,
    "data": {
        # Processed output data
    },
    "metadata": {
        "processing_time_ms": number,
        "timestamp": "ISO-8601",
        "confidence_score": number,  # 0.0-1.0
        "quality_metrics": {}
    },
    "errors": [
        # Any errors or warnings
    ]
}
```

### Error Handling Contracts

All nodes must implement standardized error handling:

**Error Response Structure**:
```python
{
    "success": false,
    "error": {
        "type": "error_category",
        "code": "specific_error_code",
        "message": "human_readable_message",
        "details": {},
        "retryable": boolean,
        "retry_after_seconds": number
    },
    "metadata": {
        "timestamp": "ISO-8601",
        "request_id": "unique_id"
    }
}
```

### Performance Contracts

Each node must meet performance requirements:

- **Scout Node**: Complete data collection within 30 seconds
- **Cleaner Node**: Process 1000 threads within 60 seconds
- **Analyst Node**: Generate insights within 120 seconds
- **Chatbot Node**: Respond within 5 seconds

## Safety and Security Testing

All contract tests include safety and security validations:

### PII Protection
- Email address detection and redaction
- Phone number identification and masking
- SSN and sensitive data handling
- Privacy compliance verification

### Content Safety
- Toxic content detection and filtering
- Harmful intent recognition
- Inappropriate content blocking
- Safety score calculation

### Security Measures
- Input sanitization validation
- XSS prevention testing
- Injection attack prevention
- Rate limiting compliance

## Continuous Integration

These contract tests are designed to be integrated into CI/CD pipelines:

### GitHub Actions Example
```yaml
name: Contract Tests
on: [push, pull_request]
jobs:
  contract-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.9
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run Contract Tests
        run: |
          cd backend/tests
          python run_contract_tests.py --save-results ci_results.json
      - name: Upload Results
        uses: actions/upload-artifact@v2
        with:
          name: contract-test-results
          path: backend/tests/ci_results.json
```

## Extending the Tests

### Adding New Contract Tests

1. **Create test method** in the appropriate test class:
```python
def test_new_functionality_contract(self):
    """Test new functionality contract compliance"""
    # Arrange
    test_input = {...}
    
    # Act
    result = self._mock_new_functionality(test_input)
    
    # Assert
    self.assertIsInstance(result, dict)
    self.assertIn('required_field', result)
    # ... additional assertions
```

2. **Add corresponding mock method**:
```python
def _mock_new_functionality(self, input_data):
    """Mock implementation for testing"""
    # Simulate the expected behavior
    return {
        'required_field': 'mock_value',
        'success': True
    }
```

3. **Update test fixtures** if needed:
```python
# Add to test_fixtures.py
@staticmethod
def generate_new_test_data():
    """Generate test data for new functionality"""
    return {...}
```

### Best Practices

1. **Comprehensive Coverage**: Test both happy path and error conditions
2. **Realistic Data**: Use realistic test data that mirrors production scenarios
3. **Performance Awareness**: Include performance assertions for critical paths
4. **Safety First**: Always test safety and security measures
5. **Documentation**: Document contract expectations clearly
6. **Isolation**: Ensure tests don't impact existing code or data
7. **Deterministic**: Make tests reproducible and deterministic

## Troubleshooting

### Common Issues

**Import Errors**:
```bash
# Ensure you're running from the correct directory
cd backend/tests
python run_contract_tests.py
```

**Test Failures**:
- Check that mock implementations match expected contracts
- Verify test data meets the expected format
- Ensure all required fields are present in test responses

**Performance Issues**:
- Adjust performance thresholds if needed
- Use `--verbose` flag to see detailed timing information
- Run performance benchmark to identify bottlenecks

### Getting Help

For issues with contract tests:
1. Check the test output for specific error messages
2. Review the contract specifications above
3. Examine the mock implementations for guidance
4. Run individual tests with `-v` flag for detailed output

## Future Enhancements

Planned improvements to the contract test suite:

- [ ] Integration with property-based testing (Hypothesis)
- [ ] Automated contract documentation generation
- [ ] Contract versioning and backward compatibility testing
- [ ] Visual test result reporting dashboard
- [ ] Performance regression detection
- [ ] Automated test data generation based on production patterns
- [ ] Cross-node integration contract testing
- [ ] Load testing for scalability validation