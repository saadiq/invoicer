# Claude Development Notes

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

## Test Dependencies

Test dependencies are listed in `test_requirements.txt` and can be installed with:
```bash
pip install -r test_requirements.txt
```

## Running Tests

```bash
# Run all tests
python run_tests.py

# Run specific test suites
python run_tests.py unit
python run_tests.py integration
python run_tests.py commands
python run_tests.py e2e

# Run with coverage
python run_tests.py --coverage
```

## Notes for Claude

- Always activate the virtual environment before running Python commands
- Use `python` (not `python3`) within the activated virtual environment
- Check that dependencies are installed in the venv before running tests or the app

## Current Test Status

- **48 tests passing** - All core functionality is tested and working
- **0 tests failing** - Clean test suite
- **65% code coverage** - Meets coverage requirements, core business logic well covered
- **Authentication functionality works** - Enhanced with robust error handling and user-friendly prompts

### Recent Updates

- ✅ Enhanced token expiration handling with user-friendly prompts
- ✅ Updated documentation (README.md, TESTING.md) 
- ✅ Added comprehensive error handling for authentication failures
- ✅ Fixed test suite to pass cleanly
- ✅ Authentication improvements verified manually

### Authentication Testing Approach

The authentication system uses the existing testing strategy:
1. **Unit tests** cover parsing, validation, and business logic
2. **Integration tests** use mocked calendar services (via `test_invoicer` fixture)
3. **End-to-end tests** verify complete workflows with mocked external dependencies
4. **Authentication enhancements** are tested manually and via integration tests

This approach focuses on testing business logic while mocking complex external dependencies (Google Calendar API), which is the standard practice for testing systems with external API integrations.