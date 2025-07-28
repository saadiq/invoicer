# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Environment Setup

This project uses a Python virtual environment located in the `venv/` directory.

**Before running any Python commands, tests, or the application, you must activate the virtual environment:**

```bash
# Activate the virtual environment
source venv/bin/activate

# Then you can run commands like:
python invoice_automation.py
python run_tests.py
pip install -r requirements.txt
```

**To deactivate the virtual environment when done:**
```bash
deactivate
```

## Common Commands

### Installation
```bash
# Install main application dependencies
pip install -r requirements.txt

# Install test dependencies
pip install -r test_requirements.txt
```

### Running the Application
```bash
# Run the main invoice automation script
python invoice_automation.py
```

### Testing Commands
```bash
# Run all tests
python run_tests.py

# Run all tests with coverage
python run_tests.py --coverage

# Run specific test suites
python run_tests.py unit        # Unit tests for core functions
python run_tests.py integration # Integration tests (Stripe/Google)
python run_tests.py commands    # Interactive command tests
python run_tests.py e2e        # End-to-end workflow tests

# Run with verbose output
python run_tests.py --verbose

# Run specific test files
python run_tests.py --file tests/test_unit.py

# Run tests with specific markers
python run_tests.py --marker unit

# Stop on first failure
python run_tests.py --failfast
```

### Direct pytest Commands (within venv)
```bash
# Run specific test classes
pytest tests/test_unit.py::TestAuthenticationLogic -v
pytest tests/test_commands.py::TestMeetingDisplayFormatting -v

# Run with coverage for specific module
pytest --cov=invoice_automation --cov-report=term-missing

# Run all tests with HTML coverage report
pytest --cov=invoice_automation --cov-report=html
```

## Architecture Overview

This is a single-module Python application for automating meeting-based invoicing workflows:

### Core Components
- **StripeCalendarInvoicer class** (`invoice_automation.py`): Main automation engine that integrates Google Calendar and Stripe APIs
- **Authentication system**: Handles Google OAuth with token refresh and expiration recovery
- **Meeting detection**: Scans calendar events and matches with Stripe customer emails
- **Interactive interface**: Command-line UI for meeting selection, editing, and invoice creation

### Key Integration Points
- **Google Calendar API**: Reads meeting data with robust authentication handling
- **Stripe API**: Customer management, rate storage in metadata, and invoice creation
- **OAuth flow**: Manages Google Calendar access tokens with automatic refresh

### Data Flow
1. Authenticate with Google Calendar (OAuth)
2. Fetch customer list from Stripe
3. Scan calendar for meetings with customer emails
4. Present interactive interface for selection/editing
5. Generate unique meeting IDs for duplicate prevention
6. Create draft invoices in Stripe with custom synopses

## Test Architecture

### Test Structure
```
tests/
├── test_unit.py           # Core business logic tests
│   ├── TestParsingFunctions      # Time, duration, rate parsing
│   ├── TestCoreFunctions         # Meeting ID, duration calculation
│   ├── TestMeetingDataStructure  # Data validation and manipulation
│   └── TestAuthenticationLogic   # Authentication error handling
├── test_commands.py       # Interactive functionality tests
│   ├── TestMeetingDisplayFormatting   # Visual indicators, time display
│   ├── TestUserInputValidation        # Command parsing, edge cases
│   ├── TestInteractiveCommands        # Command functionality
│   ├── TestEditMeetingDetails         # Meeting editing
│   └── TestSynopsisEntry             # Synopsis input handling
├── test_integration.py    # External API integration tests
│   ├── TestStripeIntegration         # Stripe API mocking
│   └── TestGoogleCalendarIntegration # Google Calendar API mocking
└── test_e2e.py           # End-to-end workflow tests
    └── TestEndToEndScenarios        # Complete user workflows
```

### Test Coverage Requirements
- **Minimum**: 64% (configured in pytest.ini)
- **Current**: 75.24%
- **All tests**: 66 tests passing consistently

## Development Workflow

### Making Changes
1. **Activate virtual environment**: `source venv/bin/activate`
2. **Run tests before changes**: `python run_tests.py --coverage`
3. **Make your changes**
4. **Run tests after changes**: `python run_tests.py --coverage`
5. **Ensure coverage maintains 64%+ requirement**

### Authentication Testing Strategy
The authentication system has comprehensive isolated testing:
- **Authentication Logic Tests**: Direct testing of auth error paths without complex API mocking
- **Integration Tests**: Use `test_invoicer` fixture with mocked calendar services
- **Unit Tests**: Focus on business logic with minimal external dependencies

### Google API Mocking Notes
- Authentication tests use `invoice_automation.build` mock target (not `googleapiclient.discovery.build`)
- This is because the main module imports build directly: `from googleapiclient.discovery import build`

## Development Guidelines

- **Always activate venv first**: `source venv/bin/activate`
- **Use `python` not `python3`** within activated virtual environment
- **Run full test suite** before making commits: `python run_tests.py --coverage`
- **Maintain 64%+ coverage** - current target achieved at 75%

## Configuration

### Environment Variables
The application supports configuration via `.env` file or environment variables:
- `STRIPE_SECRET_KEY` - Your Stripe secret API key (required)
- `DEFAULT_HOURLY_RATE` - Default hourly rate for customers without specific rates (default: 150.00)
- `DAYS_BACK` - Number of days back to check for meetings (default: 7)

### Required Files
- `credentials.json` - Google Calendar API credentials (OAuth client)
- `token.json` - Auto-generated OAuth token (don't commit!)
- `.env` - Environment variables (don't commit!)

## Troubleshooting

### Common Issues

**Tests failing after venv activation:**
```bash
# Ensure test dependencies are installed
pip install -r test_requirements.txt

# Check if you're in the right directory
pwd  # Should be /path/to/invoicer
```

**Google API authentication errors:**
- Delete `token.json` and re-authenticate if tokens are expired
- Ensure `credentials.json` is valid OAuth desktop application credentials
- Check Calendar API is enabled in Google Cloud Console

**Coverage warnings:**
- The coverage warning about "module-not-measured" is normal when running tests multiple times
- Coverage calculations remain accurate despite warnings