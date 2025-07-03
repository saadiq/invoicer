"""
Shared fixtures and configuration for pytest test suite
"""
import pytest
from datetime import datetime, timedelta
import json
import os
import sys

# Add parent directory to path so we can import invoice_automation
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

@pytest.fixture
def sample_customer():
    """Sample Stripe customer data"""
    return {
        'id': 'cus_TEST123',
        'email': 'test@example.com',
        'name': 'Test Customer',
        'created': 1609459200,
        'metadata': {'hourly_rate': '200.00'}
    }

@pytest.fixture
def sample_customer_no_rate():
    """Sample Stripe customer without hourly rate"""
    return {
        'id': 'cus_TEST456',
        'email': 'norak@example.com',
        'name': 'No Rate Customer',
        'created': 1609459200,
        'metadata': {}
    }

@pytest.fixture
def sample_meeting():
    """Sample meeting data structure"""
    return {
        'id': 'meet_123',
        'summary': 'Test Meeting',
        'date': '2025-01-15',
        'time': '2:00 PM',
        'duration': 1.0,
        'start_time': '2025-01-15T14:00:00',
        'end_time': '2025-01-15T15:00:00',
        'invoice_status': 'not_invoiced',
        'selected': True,
        'synopsis': '',
        'edited_start_time': None,
        'edited_duration': None,
        'custom_rate': None,
        'is_edited': False
    }

@pytest.fixture
def sample_edited_meeting():
    """Sample meeting with edited time and duration"""
    meeting = {
        'id': 'meet_456',
        'summary': 'Edited Meeting',
        'date': '2025-01-16',
        'time': '10:00 AM',
        'duration': 2.0,
        'start_time': '2025-01-16T10:00:00',
        'end_time': '2025-01-16T12:00:00',
        'invoice_status': 'not_invoiced',
        'selected': True,
        'synopsis': 'Project discussion',
        'edited_start_time': datetime.strptime('11:30 AM', '%I:%M %p').time(),
        'edited_duration': 2.5,
        'custom_rate': 250.0,
        'is_edited': True
    }
    return meeting

@pytest.fixture
def sample_calendar_event():
    """Sample Google Calendar event"""
    return {
        'id': 'cal_event_123',
        'summary': 'Client Meeting',
        'start': {'dateTime': '2025-01-15T14:00:00-05:00'},
        'end': {'dateTime': '2025-01-15T15:00:00-05:00'},
        'attendees': [
            {'email': 'test@example.com', 'responseStatus': 'accepted'},
            {'email': 'me@mycompany.com', 'responseStatus': 'accepted'}
        ]
    }

@pytest.fixture
def sample_invoice():
    """Sample Stripe invoice"""
    return {
        'id': 'inv_TEST123',
        'customer': 'cus_TEST123',
        'status': 'draft',
        'lines': {
            'data': [
                {
                    'description': 'Test Meeting - 2025-01-15 at 2:00 PM (1.0h @ $200/h) [ID:meet_123]'
                }
            ]
        }
    }

@pytest.fixture
def mock_stripe_customers():
    """Multiple sample customers for testing"""
    return [
        {
            'id': 'cus_ALICE',
            'email': 'alice@company1.com',
            'name': 'Alice Smith',
            'created': 1609459200,
            'metadata': {'hourly_rate': '150.00'}
        },
        {
            'id': 'cus_BOB',
            'email': 'bob@company2.com',
            'name': 'Bob Johnson',
            'created': 1609459200,
            'metadata': {'hourly_rate': '225.00'}
        },
        {
            'id': 'cus_CHARLIE',
            'email': 'charlie@company3.com',
            'name': 'Charlie Brown',
            'created': 1609459200,
            'metadata': {}  # No rate set
        }
    ]

@pytest.fixture
def mock_calendar_events():
    """Multiple calendar events for testing"""
    base_date = datetime.now() - timedelta(days=3)
    return [
        {
            'id': 'evt_1',
            'summary': 'Strategy Session',
            'start': {'dateTime': base_date.replace(hour=10, minute=0, second=0, microsecond=0).isoformat()},
            'end': {'dateTime': base_date.replace(hour=11, minute=0, second=0, microsecond=0).isoformat()},
            'attendees': [{'email': 'alice@company1.com'}]
        },
        {
            'id': 'evt_2',
            'summary': 'Project Review',
            'start': {'dateTime': (base_date + timedelta(days=1)).replace(hour=14, minute=0, second=0, microsecond=0).isoformat()},
            'end': {'dateTime': (base_date + timedelta(days=1)).replace(hour=15, minute=30, second=0, microsecond=0).isoformat()},
            'attendees': [{'email': 'bob@company2.com'}]
        },
        {
            'id': 'evt_3',
            'summary': 'Quick Check-in',
            'start': {'dateTime': (base_date + timedelta(days=2)).replace(hour=9, minute=0, second=0, microsecond=0).isoformat()},
            'end': {'dateTime': (base_date + timedelta(days=2)).replace(hour=9, minute=30, second=0, microsecond=0).isoformat()},
            'attendees': [{'email': 'charlie@company3.com'}]
        }
    ]

@pytest.fixture
def test_invoicer(mocker):
    """Create a test instance of StripeCalendarInvoicer with mocked services"""
    # Import here to avoid issues with missing dependencies during test discovery
    from invoice_automation import StripeCalendarInvoicer
    
    # Mock the Google Calendar service initialization
    mocker.patch.object(StripeCalendarInvoicer, '_get_calendar_service', return_value=mocker.Mock())
    
    # Create instance with test API key
    invoicer = StripeCalendarInvoicer(
        stripe_api_key='sk_test_fake_key',
        calendar_credentials_file='test_credentials.json',
        token_file='test_token.json',
        days_back=7
    )
    
    return invoicer

@pytest.fixture
def mock_input(mocker):
    """Helper to mock user input"""
    return mocker.patch('builtins.input')

@pytest.fixture
def mock_print(mocker):
    """Helper to capture print output"""
    return mocker.patch('builtins.print')