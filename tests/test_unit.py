"""
Unit tests for invoice automation parsing and utility functions
"""
import pytest
from datetime import datetime, time
from unittest.mock import Mock, patch, MagicMock
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
from invoice_automation import StripeCalendarInvoicer


class TestParsingFunctions:
    """Test parsing functions for time, duration, and rate"""
    
    def test_parse_time_input_valid_formats(self, test_invoicer):
        """Test parsing various valid time formats"""
        # Test 12-hour formats with minutes
        assert test_invoicer.parse_time_input("2:30 PM") == time(14, 30)
        assert test_invoicer.parse_time_input("2:30PM") == time(14, 30)
        assert test_invoicer.parse_time_input("11:45 AM") == time(11, 45)
        assert test_invoicer.parse_time_input("11:45AM") == time(11, 45)
        
        # Test 24-hour format
        assert test_invoicer.parse_time_input("14:30") == time(14, 30)
        assert test_invoicer.parse_time_input("09:15") == time(9, 15)
        assert test_invoicer.parse_time_input("23:59") == time(23, 59)
        
        # Test hour-only formats
        assert test_invoicer.parse_time_input("2 PM") == time(14, 0)
        assert test_invoicer.parse_time_input("2PM") == time(14, 0)
        assert test_invoicer.parse_time_input("11 AM") == time(11, 0)
        assert test_invoicer.parse_time_input("11AM") == time(11, 0)
        assert test_invoicer.parse_time_input("14") == time(14, 0)
    
    def test_parse_time_input_edge_cases(self, test_invoicer):
        """Test edge cases for time parsing"""
        # Empty or None
        assert test_invoicer.parse_time_input("") is None
        assert test_invoicer.parse_time_input("   ") is None
        assert test_invoicer.parse_time_input(None) is None
        
        # Midnight and noon
        assert test_invoicer.parse_time_input("12:00 AM") == time(0, 0)
        assert test_invoicer.parse_time_input("12:00 PM") == time(12, 0)
    
    def test_parse_time_input_invalid_formats(self, test_invoicer):
        """Test invalid time formats raise ValueError"""
        with pytest.raises(ValueError, match="Unable to parse time"):
            test_invoicer.parse_time_input("25:00")
        
        with pytest.raises(ValueError, match="Unable to parse time"):
            test_invoicer.parse_time_input("2:60 PM")
        
        with pytest.raises(ValueError, match="Unable to parse time"):
            test_invoicer.parse_time_input("invalid")
        
        with pytest.raises(ValueError, match="Unable to parse time"):
            test_invoicer.parse_time_input("14:30:45")  # Seconds not supported
    
    def test_parse_duration_input_valid_formats(self, test_invoicer):
        """Test parsing various valid duration formats"""
        # Plain numbers
        assert test_invoicer.parse_duration_input("1.5") == 1.5
        assert test_invoicer.parse_duration_input("2") == 2.0
        assert test_invoicer.parse_duration_input("0.5") == 0.5
        assert test_invoicer.parse_duration_input("3.25") == 3.25
        
        # With suffixes
        assert test_invoicer.parse_duration_input("1.5h") == 1.5
        assert test_invoicer.parse_duration_input("2hr") == 2.0
        assert test_invoicer.parse_duration_input("0.5 hours") == 0.5
        assert test_invoicer.parse_duration_input("3.25 hour") == 3.25
        
        # With spaces and case variations
        assert test_invoicer.parse_duration_input("  1.5  h  ") == 1.5
        assert test_invoicer.parse_duration_input("2 HR") == 2.0
        assert test_invoicer.parse_duration_input("0.5 HOURS") == 0.5
    
    def test_parse_duration_input_edge_cases(self, test_invoicer):
        """Test edge cases for duration parsing"""
        # Empty or None
        assert test_invoicer.parse_duration_input("") is None
        assert test_invoicer.parse_duration_input("   ") is None
        assert test_invoicer.parse_duration_input(None) is None
        
        # Boundary values
        assert test_invoicer.parse_duration_input("0.01") == 0.01
        assert test_invoicer.parse_duration_input("24") == 24.0
    
    def test_parse_duration_input_invalid_values(self, test_invoicer):
        """Test invalid duration values raise ValueError"""
        # Zero or negative
        with pytest.raises(ValueError, match="Duration must be between 0 and 24 hours"):
            test_invoicer.parse_duration_input("0")
        
        with pytest.raises(ValueError, match="Duration must be between 0 and 24 hours"):
            test_invoicer.parse_duration_input("-1")
        
        # Too large
        with pytest.raises(ValueError, match="Duration must be between 0 and 24 hours"):
            test_invoicer.parse_duration_input("25")
        
        with pytest.raises(ValueError, match="Duration must be between 0 and 24 hours"):
            test_invoicer.parse_duration_input("100")
        
        # Invalid format - these will raise "Unable to parse duration: <cleaned_str>"
        with pytest.raises(ValueError, match="Unable to parse duration"):
            test_invoicer.parse_duration_input("invalid")
        
        with pytest.raises(ValueError, match="Unable to parse duration"):
            test_invoicer.parse_duration_input("two hours")
    
    def test_validate_hourly_rate_valid_values(self, test_invoicer):
        """Test validating hourly rate with valid values"""
        # Plain numbers
        assert test_invoicer.validate_hourly_rate("150") == 150.0
        assert test_invoicer.validate_hourly_rate("99.99") == 99.99
        assert test_invoicer.validate_hourly_rate("1000") == 1000.0
        
        # With dollar sign
        assert test_invoicer.validate_hourly_rate("$150") == 150.0
        assert test_invoicer.validate_hourly_rate("$99.99") == 99.99
        assert test_invoicer.validate_hourly_rate("$1,000") == 1000.0
        
        # With spaces
        assert test_invoicer.validate_hourly_rate("  $150  ") == 150.0
        assert test_invoicer.validate_hourly_rate("  150  ") == 150.0
    
    def test_validate_hourly_rate_edge_cases(self, test_invoicer):
        """Test edge cases for rate validation"""
        # Empty or None
        assert test_invoicer.validate_hourly_rate("") is None
        assert test_invoicer.validate_hourly_rate("   ") is None
        assert test_invoicer.validate_hourly_rate(None) is None
        
        # Boundary values
        assert test_invoicer.validate_hourly_rate("0.01") == 0.01
        assert test_invoicer.validate_hourly_rate("10000") == 10000.0
    
    def test_validate_hourly_rate_invalid_values(self, test_invoicer):
        """Test invalid rate values raise ValueError"""
        # Zero or negative - these actually raise "Unable to parse rate: 0" because the parsing happens first
        with pytest.raises(ValueError):
            test_invoicer.validate_hourly_rate("0")
        
        with pytest.raises(ValueError):
            test_invoicer.validate_hourly_rate("-50")
        
        # Too large
        with pytest.raises(ValueError, match="Rate must be between"):
            test_invoicer.validate_hourly_rate("10001")
        
        with pytest.raises(ValueError, match="Rate must be between"):
            test_invoicer.validate_hourly_rate("99999")
        
        # Invalid format
        with pytest.raises(ValueError, match="Unable to parse rate"):
            test_invoicer.validate_hourly_rate("invalid")
        
        with pytest.raises(ValueError, match="Unable to parse rate"):
            test_invoicer.validate_hourly_rate("one fifty")


class TestCoreFunctions:
    """Test core business logic functions"""
    
    def test_generate_meeting_id(self, test_invoicer):
        """Test meeting ID generation is consistent"""
        # Same inputs should generate same ID
        id1 = test_invoicer.generate_meeting_id("test@example.com", "2025-01-15T14:00:00", "Test Meeting")
        id2 = test_invoicer.generate_meeting_id("test@example.com", "2025-01-15T14:00:00", "Test Meeting")
        assert id1 == id2
        assert len(id1) == 12  # MD5 hash truncated to 12 characters
        
        # Different inputs should generate different IDs
        id3 = test_invoicer.generate_meeting_id("other@example.com", "2025-01-15T14:00:00", "Test Meeting")
        id4 = test_invoicer.generate_meeting_id("test@example.com", "2025-01-16T14:00:00", "Test Meeting")
        id5 = test_invoicer.generate_meeting_id("test@example.com", "2025-01-15T14:00:00", "Other Meeting")
        
        assert id1 != id3
        assert id1 != id4
        assert id1 != id5
    
    def test_calculate_meeting_duration(self, test_invoicer):
        """Test meeting duration calculation"""
        # Normal cases
        assert test_invoicer.calculate_meeting_duration(
            "2025-01-15T14:00:00", "2025-01-15T15:00:00"
        ) == 1.0
        
        assert test_invoicer.calculate_meeting_duration(
            "2025-01-15T14:00:00", "2025-01-15T15:30:00"
        ) == 1.5
        
        assert test_invoicer.calculate_meeting_duration(
            "2025-01-15T09:00:00", "2025-01-15T09:30:00"
        ) == 0.5
        
        assert test_invoicer.calculate_meeting_duration(
            "2025-01-15T09:00:00", "2025-01-15T11:15:00"
        ) == 2.25
        
        # Edge cases - invalid times should return default 1.0
        assert test_invoicer.calculate_meeting_duration("invalid", "2025-01-15T15:00:00") == 1.0
        assert test_invoicer.calculate_meeting_duration("2025-01-15T14:00:00", "invalid") == 1.0
        assert test_invoicer.calculate_meeting_duration("invalid", "invalid") == 1.0
    
    def test_get_customer_hourly_rate(self, test_invoicer, sample_customer, sample_customer_no_rate):
        """Test customer hourly rate retrieval with fallbacks"""
        # Customer with rate set
        rate = test_invoicer.get_customer_hourly_rate(sample_customer, 150.0)
        assert rate == 200.0  # From metadata
        
        # Customer without rate - should use default
        rate = test_invoicer.get_customer_hourly_rate(sample_customer_no_rate, 150.0)
        assert rate == 150.0  # Default rate
        
        # Customer with invalid rate - should use default
        customer_bad_rate = sample_customer.copy()
        customer_bad_rate['metadata']['hourly_rate'] = 'invalid'
        rate = test_invoicer.get_customer_hourly_rate(customer_bad_rate, 150.0)
        assert rate == 150.0  # Default rate
        
        # Customer with empty rate - should use default
        customer_empty_rate = sample_customer.copy()
        customer_empty_rate['metadata']['hourly_rate'] = ''
        rate = test_invoicer.get_customer_hourly_rate(customer_empty_rate, 150.0)
        assert rate == 150.0  # Default rate
    
    def test_check_meeting_invoice_status(self, test_invoicer, mocker, sample_invoice):
        """Test checking if a meeting has been invoiced"""
        # Convert dict to object-like structure for the test
        from types import SimpleNamespace
        invoice_obj = SimpleNamespace(**sample_invoice)
        invoice_obj.lines = SimpleNamespace(data=[SimpleNamespace(description=item['description']) for item in sample_invoice['lines']['data']])
        
        # Mock get_customer_invoices to return sample invoice
        mocker.patch.object(
            test_invoicer, 
            'get_customer_invoices',
            return_value=[invoice_obj]
        )
        
        # Meeting ID that's in the invoice
        status = test_invoicer.check_meeting_invoice_status('cus_TEST123', 'meet_123')
        assert status == 'drafted'
        
        # Meeting ID that's not in any invoice
        status = test_invoicer.check_meeting_invoice_status('cus_TEST123', 'meet_999')
        assert status == 'not_invoiced'
        
        # Test with sent invoice
        sent_invoice_obj = SimpleNamespace(**sample_invoice)
        sent_invoice_obj.status = 'open'
        sent_invoice_obj.lines = SimpleNamespace(data=[SimpleNamespace(description=item['description']) for item in sample_invoice['lines']['data']])
        mocker.patch.object(
            test_invoicer,
            'get_customer_invoices',
            return_value=[sent_invoice_obj]
        )
        
        status = test_invoicer.check_meeting_invoice_status('cus_TEST123', 'meet_123')
        assert status == 'sent'


class TestMeetingDataStructure:
    """Test meeting data structure and manipulation"""
    
    def test_meeting_initialization(self, sample_meeting):
        """Test that meeting objects are initialized correctly"""
        assert sample_meeting['edited_start_time'] is None
        assert sample_meeting['edited_duration'] is None
        assert sample_meeting['custom_rate'] is None
        assert sample_meeting['is_edited'] is False
        assert sample_meeting['selected'] is True  # Not invoiced meetings default to selected
    
    def test_edited_meeting_values(self, sample_edited_meeting):
        """Test edited meeting has correct override values"""
        assert sample_edited_meeting['is_edited'] is True
        assert sample_edited_meeting['edited_start_time'] == time(11, 30)
        assert sample_edited_meeting['edited_duration'] == 2.5
        assert sample_edited_meeting['custom_rate'] == 250.0
    
    def test_meeting_amount_calculation(self, sample_meeting, sample_edited_meeting):
        """Test amount calculation with and without overrides"""
        default_rate = 150.0
        
        # Normal meeting
        amount = sample_meeting['duration'] * default_rate
        assert amount == 150.0  # 1 hour * $150
        
        # Edited meeting with custom rate
        edited_duration = sample_edited_meeting['edited_duration']
        custom_rate = sample_edited_meeting['custom_rate']
        amount = edited_duration * custom_rate
        assert amount == 625.0  # 2.5 hours * $250


class TestAuthenticationLogic:
    """Test Google Calendar authentication logic and error handling"""
    
    def test_authentication_service_failure_initialization(self, mocker):
        """Test that authentication service failure raises proper exception"""
        from invoice_automation import StripeCalendarInvoicer
        
        # Mock _get_calendar_service to return None (failure)
        mocker.patch.object(StripeCalendarInvoicer, '_get_calendar_service', return_value=None)
        
        # Should raise exception when calendar service fails to initialize
        with pytest.raises(Exception, match="Failed to initialize Google Calendar service"):
            StripeCalendarInvoicer('test_key')
    
    def test_token_file_loading_error_handling(self, mocker):
        """Test handling of corrupted or invalid token files"""
        from invoice_automation import StripeCalendarInvoicer
        
        # Create invoicer instance without calling constructor
        invoicer = StripeCalendarInvoicer.__new__(StripeCalendarInvoicer)
        invoicer.token_file = 'test_token.json'
        invoicer.calendar_scopes = ['test_scope']
        invoicer.calendar_credentials_file = 'test_credentials.json'
        
        # Mock file existence but credential loading failure
        mocker.patch('os.path.exists', return_value=True)
        mocker.patch('google.oauth2.credentials.Credentials.from_authorized_user_file', 
                    side_effect=Exception("Corrupted token file"))
        
        # Mock successful fresh authentication
        mock_creds = Mock()
        mock_creds.valid = True
        mock_creds.to_json.return_value = '{"token": "data"}'
        
        mock_flow = Mock()
        mock_flow.run_local_server.return_value = mock_creds
        mocker.patch('google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file', 
                    return_value=mock_flow)
        
        mock_service = Mock()
        mocker.patch('invoice_automation.build', return_value=mock_service)
        mock_open = mocker.patch('builtins.open', mocker.mock_open())
        
        # Should handle corrupted token and proceed with fresh auth
        result = invoicer._get_calendar_service()
        
        # Verify fresh authentication was performed
        mock_flow.run_local_server.assert_called_once()
        assert result == mock_service
    
    @pytest.mark.parametrize("user_choice,expected_removed", [
        ('y', True),
        ('yes', True), 
        ('n', False),
        ('no', False)
    ])
    def test_token_expiration_user_choice_handling(self, mocker, user_choice, expected_removed):
        """Test user choice handling when token refresh fails"""
        from invoice_automation import StripeCalendarInvoicer
        
        invoicer = StripeCalendarInvoicer.__new__(StripeCalendarInvoicer)
        invoicer.token_file = 'test_token.json'
        invoicer.calendar_scopes = ['test_scope']
        invoicer.calendar_credentials_file = 'test_credentials.json'
        
        # Mock file exists and expired credentials
        mocker.patch('os.path.exists', return_value=True)
        
        mock_creds = Mock()
        mock_creds.valid = False
        mock_creds.expired = True
        mock_creds.refresh_token = 'refresh_token'
        mocker.patch('google.oauth2.credentials.Credentials.from_authorized_user_file', 
                    return_value=mock_creds)
        
        # Mock failed refresh
        mock_creds.refresh.side_effect = RefreshError("Token expired")
        mock_request = Mock()
        mocker.patch('google.auth.transport.requests.Request', return_value=mock_request)
        
        # Mock user input
        mocker.patch('builtins.input', return_value=user_choice)
        mocker.patch('builtins.print')  # Suppress output
        
        # Mock file removal
        mock_remove = mocker.patch('os.remove')
        
        if expected_removed:
            # Mock successful fresh authentication
            mock_new_creds = Mock()
            mock_new_creds.valid = True
            mock_new_creds.to_json.return_value = '{"new": "token"}'
            
            mock_flow = Mock()
            mock_flow.run_local_server.return_value = mock_new_creds
            mocker.patch('google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file', 
                        return_value=mock_flow)
            
            mock_service = Mock()
            mocker.patch('invoice_automation.build', return_value=mock_service)
            mock_open = mocker.patch('builtins.open', mocker.mock_open())
            
            result = invoicer._get_calendar_service()
            
            # Should remove token and proceed with fresh auth
            mock_remove.assert_called_once_with('test_token.json')
            mock_flow.run_local_server.assert_called_once()
            assert result == mock_service
        else:
            # Should return None without removing token
            result = invoicer._get_calendar_service()
            mock_remove.assert_not_called()
            assert result is None
    
    def test_token_expiration_invalid_user_choice(self, mocker):
        """Test handling of invalid user input during token expiration"""
        from invoice_automation import StripeCalendarInvoicer
        
        invoicer = StripeCalendarInvoicer.__new__(StripeCalendarInvoicer)
        invoicer.token_file = 'test_token.json'
        invoicer.calendar_scopes = ['test_scope']
        invoicer.calendar_credentials_file = 'test_credentials.json'
        
        # Mock expired credentials
        mocker.patch('os.path.exists', return_value=True)
        mock_creds = Mock()
        mock_creds.valid = False
        mock_creds.expired = True
        mock_creds.refresh_token = 'refresh_token'
        mock_creds.refresh.side_effect = RefreshError("Token expired")
        mocker.patch('google.oauth2.credentials.Credentials.from_authorized_user_file', 
                    return_value=mock_creds)
        mocker.patch('google.auth.transport.requests.Request')
        
        # Mock invalid input followed by valid input
        mocker.patch('builtins.input', side_effect=['invalid', 'maybe', 'y'])
        mock_print = mocker.patch('builtins.print')
        
        # Mock successful file removal and fresh auth
        mocker.patch('os.remove')
        mock_new_creds = Mock()
        mock_new_creds.valid = True
        mock_new_creds.to_json.return_value = '{"new": "token"}'
        mock_flow = Mock()
        mock_flow.run_local_server.return_value = mock_new_creds
        mocker.patch('google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file', 
                    return_value=mock_flow)
        mock_service = Mock()
        mocker.patch('invoice_automation.build', return_value=mock_service)
        mocker.patch('builtins.open', mocker.mock_open())
        
        result = invoicer._get_calendar_service()
        
        # Should prompt user multiple times for invalid input
        assert any("Please enter 'y' or 'n'" in str(call) for call in mock_print.call_args_list)
        assert result == mock_service
    
    def test_token_file_removal_error(self, mocker):
        """Test handling of file removal errors during token expiration"""
        from invoice_automation import StripeCalendarInvoicer
        
        invoicer = StripeCalendarInvoicer.__new__(StripeCalendarInvoicer)
        invoicer.token_file = 'test_token.json'
        invoicer.calendar_scopes = ['test_scope']
        invoicer.calendar_credentials_file = 'test_credentials.json'
        
        # Mock expired credentials and user accepting removal
        mocker.patch('os.path.exists', return_value=True)
        mock_creds = Mock()
        mock_creds.valid = False
        mock_creds.expired = True
        mock_creds.refresh_token = 'refresh_token'
        mock_creds.refresh.side_effect = RefreshError("Token expired")
        mocker.patch('google.oauth2.credentials.Credentials.from_authorized_user_file', 
                    return_value=mock_creds)
        mocker.patch('google.auth.transport.requests.Request')
        mocker.patch('builtins.input', return_value='y')
        mock_print = mocker.patch('builtins.print')
        
        # Mock file removal failure
        mocker.patch('os.remove', side_effect=OSError("Permission denied"))
        
        result = invoicer._get_calendar_service()
        
        # Should handle file removal error gracefully
        assert any("Could not remove token file" in str(call) for call in mock_print.call_args_list)
        assert result is None
    
    def test_fresh_authentication_failure(self, mocker):
        """Test handling of fresh authentication failures"""
        from invoice_automation import StripeCalendarInvoicer
        
        invoicer = StripeCalendarInvoicer.__new__(StripeCalendarInvoicer)
        invoicer.token_file = 'test_token.json'
        invoicer.calendar_scopes = ['test_scope']
        invoicer.calendar_credentials_file = 'test_credentials.json'
        
        # Mock no existing token
        mocker.patch('os.path.exists', return_value=False)
        
        # Mock authentication flow failure
        mock_flow = Mock()
        mock_flow.run_local_server.side_effect = Exception("Authentication failed")
        mocker.patch('google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file', 
                    return_value=mock_flow)
        mock_print = mocker.patch('builtins.print')
        
        result = invoicer._get_calendar_service()
        
        # Should handle auth failure gracefully
        assert any("Google Calendar authentication failed" in str(call) for call in mock_print.call_args_list)
        assert result is None
    
    def test_token_save_failure(self, mocker):
        """Test handling of token save failures"""
        from invoice_automation import StripeCalendarInvoicer
        
        invoicer = StripeCalendarInvoicer.__new__(StripeCalendarInvoicer)
        invoicer.token_file = 'test_token.json'
        invoicer.calendar_scopes = ['test_scope']
        invoicer.calendar_credentials_file = 'test_credentials.json'
        
        # Mock no existing token and successful auth
        mocker.patch('os.path.exists', return_value=False)
        
        mock_creds = Mock()
        mock_creds.valid = True
        mock_creds.to_json.return_value = '{"token": "data"}'
        
        mock_flow = Mock()
        mock_flow.run_local_server.return_value = mock_creds
        mocker.patch('google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file', 
                    return_value=mock_flow)
        
        mock_service = Mock()
        mocker.patch('invoice_automation.build', return_value=mock_service)
        
        # Mock file save failure
        mocker.patch('builtins.open', side_effect=OSError("Disk full"))
        mock_print = mocker.patch('builtins.print')
        
        result = invoicer._get_calendar_service()
        
        # Should handle save failure but still return service
        assert any("Could not save authentication token" in str(call) for call in mock_print.call_args_list)
        assert result == mock_service
    
    def test_calendar_service_build_failure(self, mocker):
        """Test handling of calendar service build failures"""
        from invoice_automation import StripeCalendarInvoicer
        
        invoicer = StripeCalendarInvoicer.__new__(StripeCalendarInvoicer)
        invoicer.token_file = 'test_token.json'
        invoicer.calendar_scopes = ['test_scope']
        invoicer.calendar_credentials_file = 'test_credentials.json'
        
        # Mock successful authentication but service build failure
        mocker.patch('os.path.exists', return_value=False)
        
        mock_creds = Mock()
        mock_creds.valid = True
        mock_creds.to_json.return_value = '{"token": "data"}'
        
        mock_flow = Mock()
        mock_flow.run_local_server.return_value = mock_creds
        mocker.patch('google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file', 
                    return_value=mock_flow)
        
        mocker.patch('builtins.open', mocker.mock_open())
        
        # Mock calendar service build failure
        mocker.patch('invoice_automation.build', side_effect=Exception("Service build failed"))
        mock_print = mocker.patch('builtins.print')
        
        result = invoicer._get_calendar_service()
        
        # Should handle service build failure
        assert any("Failed to initialize Google Calendar service" in str(call) for call in mock_print.call_args_list)
        assert result is None


class TestDescriptionParsing:
    """Test email extraction and customer detection from meeting descriptions"""
    
    def test_extract_emails_from_text_valid_emails(self, test_invoicer):
        """Test extracting valid email addresses from text"""
        # Test single email
        text = "Meeting with john@example.com about project"
        emails = test_invoicer.extract_emails_from_text(text)
        assert emails == {'john@example.com'}
        
        # Test multiple emails
        text = "Attendees: alice@company.com, bob@startup.io, charlie@enterprise.net"
        emails = test_invoicer.extract_emails_from_text(text)
        assert emails == {'alice@company.com', 'bob@startup.io', 'charlie@enterprise.net'}
        
        # Test Zoom meeting format
        text = """Jahmal jahmal.lake@ourkidsreadinc.org is inviting you to a scheduled Zoom meeting.
        Join Zoom Meeting
        https://us06web.zoom.us/j/83340401345?pwd=Gkge53pWb2tnc7RCU9HfYLxiGfmxIX.1&from=addon"""
        emails = test_invoicer.extract_emails_from_text(text)
        assert emails == {'jahmal.lake@ourkidsreadinc.org'}
        
        # Test mixed case emails
        text = "Contact: John.Doe@Example.COM or JANE@COMPANY.ORG"
        emails = test_invoicer.extract_emails_from_text(text)
        assert emails == {'john.doe@example.com', 'jane@company.org'}
    
    def test_extract_emails_from_text_edge_cases(self, test_invoicer):
        """Test email extraction edge cases"""
        # Empty text
        assert test_invoicer.extract_emails_from_text("") == set()
        assert test_invoicer.extract_emails_from_text(None) == set()
        assert test_invoicer.extract_emails_from_text("   ") == set()
        
        # No emails in text
        text = "This is a meeting about quarterly planning"
        assert test_invoicer.extract_emails_from_text(text) == set()
        
        # Emails with special characters
        text = "Contact: user+tag@example.com, first.last@sub.domain.com"
        emails = test_invoicer.extract_emails_from_text(text)
        assert emails == {'user+tag@example.com', 'first.last@sub.domain.com'}
        
        # Duplicate emails
        text = "john@example.com and John@Example.com are the same"
        emails = test_invoicer.extract_emails_from_text(text)
        assert emails == {'john@example.com'}
    
    def test_find_customer_mentions_in_text(self, test_invoicer):
        """Test finding customer mentions by name and email"""
        customers = [
            {'email': 'alice@techcorp.com', 'name': 'Alice Johnson'},
            {'email': 'bob@designstudio.com', 'name': 'Bob Smith'},
            {'email': 'charlie@startup.io', 'name': 'Charlie Davis'},
            {'email': 'unknown@example.com', 'name': 'Unknown'},  # Should be skipped
        ]
        
        # Test name and email close together
        text = "Alice Johnson alice@techcorp.com is joining the meeting"
        found = test_invoicer.find_customer_mentions_in_text(text, customers)
        assert found == {'alice@techcorp.com'}
        
        # Test multiple customers
        text = """Meeting attendees:
        - Bob Smith (bob@designstudio.com)
        - Charlie Davis - charlie@startup.io
        """
        found = test_invoicer.find_customer_mentions_in_text(text, customers)
        assert found == {'bob@designstudio.com', 'charlie@startup.io'}
        
        # Test case insensitive matching
        text = "ALICE JOHNSON from alice@techcorp.com will present"
        found = test_invoicer.find_customer_mentions_in_text(text, customers)
        assert found == {'alice@techcorp.com'}
        
        # Test name and email far apart (>100 chars)
        text = "Alice Johnson" + " " * 110 + "alice@techcorp.com"
        found = test_invoicer.find_customer_mentions_in_text(text, customers)
        assert found == set()  # Too far apart
        
        # Test unknown customer name (should be skipped)
        text = "Unknown unknown@example.com is attending"
        found = test_invoicer.find_customer_mentions_in_text(text, customers)
        assert found == set()
    
    def test_find_customer_mentions_edge_cases(self, test_invoicer):
        """Test edge cases for customer mention detection"""
        customers = [
            {'email': 'alice@techcorp.com', 'name': 'Alice Johnson'},
            {'email': 'no-name@example.com', 'name': ''},  # Empty name
        ]
        
        # Empty text
        assert test_invoicer.find_customer_mentions_in_text("", customers) == set()
        assert test_invoicer.find_customer_mentions_in_text(None, customers) == set()
        
        # Customer with empty name
        text = "Meeting with no-name@example.com"
        found = test_invoicer.find_customer_mentions_in_text(text, customers)
        assert found == set()  # Should not find customers without names
        
        # Only email without name
        text = "alice@techcorp.com will attend"
        found = test_invoicer.find_customer_mentions_in_text(text, customers)
        assert found == set()  # Requires both name and email
        
        # Only name without email
        text = "Alice Johnson will attend"
        found = test_invoicer.find_customer_mentions_in_text(text, customers)
        assert found == set()  # Requires both name and email


