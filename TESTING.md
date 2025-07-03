# Testing Guide for Invoice Automation System

## Overview

This document describes the comprehensive test suite for the invoice automation system. The tests validate all functionality including core features, new enhancements (meeting time/duration overrides and rate management), and integration with external services.

## Test Structure

```
tests/
├── __init__.py              # Test package initialization
├── conftest.py              # Shared fixtures and test configuration
├── test_unit.py             # Unit tests for individual functions
├── test_integration.py      # Integration tests with external APIs
├── test_commands.py         # Interactive command system tests
├── test_e2e.py             # End-to-end workflow tests
└── test_data/              # Sample test data
    ├── customers.json      # Sample Stripe customers
    ├── meetings.json       # Sample calendar events
    └── invoices.json       # Sample invoices
```

## Quick Start

### Install Test Dependencies

```bash
pip install -r test_requirements.txt
```

### Run All Tests

```bash
# Using pytest directly
pytest

# Using the test runner script
python run_tests.py

# With coverage report
python run_tests.py --coverage
```

### Run Specific Test Suites

```bash
# Unit tests only
python run_tests.py unit

# Integration tests only
python run_tests.py integration

# Interactive command tests
python run_tests.py commands

# End-to-end tests
python run_tests.py e2e

# Quick tests (excludes slow tests)
python run_tests.py quick
```

## Test Categories

### 1. Unit Tests (`test_unit.py`)

Tests individual functions in isolation:

#### Parsing Functions
- `test_parse_time_input_*` - Time parsing with various formats
- `test_parse_duration_input_*` - Duration parsing and validation
- `test_validate_hourly_rate_*` - Rate validation and parsing

#### Core Logic
- `test_generate_meeting_id` - Meeting ID generation consistency
- `test_calculate_meeting_duration` - Duration calculation accuracy
- `test_get_customer_hourly_rate` - Rate retrieval with fallbacks
- `test_check_meeting_invoice_status` - Invoice status checking

#### Data Structures
- `test_meeting_initialization` - Meeting object structure
- `test_edited_meeting_values` - Override value handling
- `test_meeting_amount_calculation` - Billing calculations

### 2. Integration Tests (`test_integration.py`)

Tests interactions with external services (mocked):

#### Stripe Integration
- Customer fetching with pagination
- Invoice creation and line items
- Customer metadata updates
- Error handling for API failures

#### Google Calendar Integration
- Event fetching within date ranges
- Meeting-to-customer matching
- OAuth token handling
- Error recovery scenarios

### 3. Command Tests (`test_commands.py`)

Tests the interactive command system:

#### Command Processing
- Meeting selection/deselection (`1`, `2`, etc.)
- Bulk operations (`all`, `none`)
- Meeting editing (`edit 1`, `time 1`)
- Rate management (`rate 1 250`, `setrate email@example.com 200`)
- Invalid command handling

#### User Interaction
- `test_edit_meeting_details` - Time/duration editing flow
- `test_synopsis_entry` - Meeting description input
- Input validation and error handling

### 4. End-to-End Tests (`test_e2e.py`)

Tests complete workflows:

#### Happy Path Scenarios
- Single customer with multiple meetings
- Meeting time/duration editing workflow
- Custom rate application workflow
- Customer rate update workflow

#### Edge Cases
- No meetings found
- All meetings already invoiced
- API failures and recovery
- Invalid data handling

## Test Data

### Sample Customers (`test_data/customers.json`)
- 5 test customers with various configurations
- Some with hourly rates, some without
- Different rate tiers ($150-$300/hour)

### Sample Meetings (`test_data/meetings.json`)
- 6 calendar events with different scenarios
- Various durations (30 min to 2 hours)
- Different attendee configurations

### Sample Invoices (`test_data/invoices.json`)
- Existing invoices in different states (draft, open, paid)
- Used for testing duplicate invoice prevention

## Running Tests with Coverage

```bash
# Generate coverage report
pytest --cov=invoice_automation --cov-report=html

# View coverage report
open htmlcov/index.html
```

### Coverage Goals
- Overall coverage: >80%
- Critical paths: 100%
- Error handling: >90%

## Test Markers

Use pytest markers to run specific test categories:

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run only end-to-end tests
pytest -m e2e

# Exclude slow tests
pytest -m "not slow"
```

## Continuous Integration

### GitHub Actions Example

```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r test_requirements.txt
      - name: Run tests
        run: pytest --cov=invoice_automation
```

## Writing New Tests

### Test Structure Template

```python
class TestFeatureName:
    """Test suite for specific feature"""
    
    def test_happy_path(self, test_invoicer, mock_input):
        """Test normal successful flow"""
        # Arrange
        test_data = {...}
        
        # Act
        result = test_invoicer.method_name(test_data)
        
        # Assert
        assert result.expected_value == actual_value
    
    def test_edge_case(self, test_invoicer):
        """Test boundary conditions"""
        pass
    
    def test_error_handling(self, test_invoicer, mocker):
        """Test error scenarios"""
        pass
```

### Using Fixtures

Common fixtures available in `conftest.py`:
- `test_invoicer` - Pre-configured invoicer instance
- `sample_customer` - Test customer data
- `sample_meeting` - Test meeting data
- `mock_input` - Mock user input
- `mock_print` - Capture print output

## Debugging Tests

### Run specific test
```bash
pytest tests/test_unit.py::TestParsingFunctions::test_parse_time_input_valid_formats -v
```

### Show print output
```bash
pytest -s
```

### Drop into debugger on failure
```bash
pytest --pdb
```

### Show local variables on failure
```bash
pytest -l
```

## Best Practices

1. **Isolation**: Each test should be independent
2. **Mocking**: Mock external services (Stripe, Google Calendar)
3. **Fixtures**: Use shared fixtures for common test data
4. **Assertions**: Be specific about what you're testing
5. **Coverage**: Aim for high coverage but focus on critical paths
6. **Documentation**: Document complex test scenarios

## Troubleshooting

### Common Issues

**Import errors**: Ensure the parent directory is in Python path
```python
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
```

**Mock not working**: Check mock path matches actual import
```python
mocker.patch('invoice_automation.stripe.Customer.list')  # ❌ Wrong
mocker.patch('stripe.Customer.list')  # ✅ Correct
```

**Fixture not found**: Ensure conftest.py is in the tests directory

## Future Enhancements

- [ ] Performance benchmarks
- [ ] Load testing for bulk operations
- [ ] Integration tests with real test accounts
- [ ] Mutation testing
- [ ] Security testing for API key handling