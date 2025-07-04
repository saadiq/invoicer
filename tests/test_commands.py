"""
Tests for interactive command processing and user input handling
"""
import pytest
from unittest.mock import Mock, call, patch
from datetime import datetime, time
import io
import sys


class TestMeetingDisplayFormatting:
    """Test meeting display formatting and visual indicators"""
    
    def test_time_display_with_edited_values(self, test_invoicer, mock_print):
        """Test time display formatting with edited start times"""
        customers_with_meetings = {
            'cus_TEST123': {
                'customer': {'id': 'cus_TEST123', 'name': 'Test Customer', 'email': 'test@example.com'},
                'meetings': [
                    {
                        'id': 'meet_1',
                        'summary': 'Meeting 1',
                        'date': '2025-01-15',
                        'time': '2:00 PM',
                        'duration': 1.0,
                        'invoice_status': 'not_invoiced',
                        'selected': True,
                        'synopsis': '',
                        'edited_start_time': time(14, 30),  # 2:30 PM
                        'edited_duration': None,
                        'custom_rate': None,
                        'is_edited': True
                    }
                ]
            }
        }
        
        # Test display formatting - just call display without interaction
        with patch('builtins.input', side_effect=['continue', 'Test synopsis']):
            test_invoicer.display_meetings_interactive(customers_with_meetings, 150.0)
        
        # Verify edited time is displayed
        print_calls = [str(call) for call in mock_print.call_args_list]
        assert any('2:30 PM' in call for call in print_calls), "Edited time should be displayed"
    
    def test_time_display_formatting_error_handling(self, test_invoicer, mock_print):
        """Test time display gracefully handles corrupted edited_start_time"""
        customers_with_meetings = {
            'cus_TEST123': {
                'customer': {'id': 'cus_TEST123', 'name': 'Test Customer', 'email': 'test@example.com'},
                'meetings': [
                    {
                        'id': 'meet_1',
                        'summary': 'Meeting 1',
                        'date': '2025-01-15',
                        'time': '2:00 PM',
                        'duration': 1.0,
                        'invoice_status': 'not_invoiced',
                        'selected': True,
                        'synopsis': '',
                        'edited_start_time': 'corrupted_value',  # Invalid time object
                        'edited_duration': None,
                        'custom_rate': None,
                        'is_edited': True
                    }
                ]
            }
        }
        
        # Should fallback to original time without crashing
        with patch('builtins.input', side_effect=['continue', 'Test synopsis']):
            test_invoicer.display_meetings_interactive(customers_with_meetings, 150.0)
        
        # Verify original time is displayed as fallback
        print_calls = [str(call) for call in mock_print.call_args_list]
        assert any('2:00 PM' in call for call in print_calls), "Original time should be displayed as fallback"
    
    def test_meeting_indicators_display(self, test_invoicer, mock_print):
        """Test visual indicators for edited meetings and custom rates"""
        customers_with_meetings = {
            'cus_TEST123': {
                'customer': {'id': 'cus_TEST123', 'name': 'Test Customer', 'email': 'test@example.com'},
                'meetings': [
                    {
                        'id': 'meet_1',
                        'summary': 'Edited Meeting',
                        'date': '2025-01-15',
                        'time': '2:00 PM',
                        'duration': 1.0,
                        'invoice_status': 'not_invoiced',
                        'selected': True,
                        'synopsis': '',
                        'edited_start_time': time(14, 30),
                        'edited_duration': 2.0,
                        'custom_rate': 250.0,
                        'is_edited': True
                    }
                ]
            }
        }
        
        with patch('builtins.input', side_effect=['continue', 'Test synopsis']):
            test_invoicer.display_meetings_interactive(customers_with_meetings, 150.0)
        
        # Verify both indicators are displayed
        print_calls = [str(call) for call in mock_print.call_args_list]
        assert any('✏️' in call for call in print_calls), "Edit indicator should be displayed"
        assert any('💰$250' in call for call in print_calls), "Custom rate indicator should be displayed"
    
    def test_status_symbol_mapping(self, test_invoicer, mock_print):
        """Test all invoice status symbols are displayed correctly"""
        customers_with_meetings = {
            'cus_TEST123': {
                'customer': {'id': 'cus_TEST123', 'name': 'Test Customer', 'email': 'test@example.com'},
                'meetings': [
                    {
                        'id': 'meet_1',
                        'summary': 'Not Invoiced',
                        'date': '2025-01-15',
                        'time': '2:00 PM',
                        'duration': 1.0,
                        'invoice_status': 'not_invoiced',
                        'selected': False,
                        'synopsis': '',
                        'edited_start_time': None,
                        'edited_duration': None,
                        'custom_rate': None,
                        'is_edited': False
                    },
                    {
                        'id': 'meet_2',
                        'summary': 'Drafted',
                        'date': '2025-01-16',
                        'time': '3:00 PM',
                        'duration': 1.0,
                        'invoice_status': 'drafted',
                        'selected': False,
                        'synopsis': '',
                        'edited_start_time': None,
                        'edited_duration': None,
                        'custom_rate': None,
                        'is_edited': False
                    },
                    {
                        'id': 'meet_3',
                        'summary': 'Sent',
                        'date': '2025-01-17',
                        'time': '4:00 PM',
                        'duration': 1.0,
                        'invoice_status': 'sent',
                        'selected': False,
                        'synopsis': '',
                        'edited_start_time': None,
                        'edited_duration': None,
                        'custom_rate': None,
                        'is_edited': False
                    }
                ]
            }
        }
        
        with patch('builtins.input', side_effect=['continue']):
            test_invoicer.display_meetings_interactive(customers_with_meetings, 150.0)
        
        # Verify all status symbols are displayed
        print_calls = [str(call) for call in mock_print.call_args_list]
        assert any('⭕' in call for call in print_calls), "Not invoiced symbol should be displayed"
        assert any('📄' in call for call in print_calls), "Draft symbol should be displayed"
        assert any('✅' in call for call in print_calls), "Sent symbol should be displayed"


class TestUserInputValidation:
    """Test user input validation and command parsing edge cases"""
    
    def test_command_parsing_with_extra_spaces(self, test_invoicer, mock_input, mock_print):
        """Test command parsing handles extra spaces gracefully"""
        customers_with_meetings = {
            'cus_TEST123': {
                'customer': {'id': 'cus_TEST123', 'name': 'Test Customer', 'email': 'test@example.com'},
                'meetings': [
                    {
                        'id': 'meet_1',
                        'summary': 'Meeting 1',
                        'date': '2025-01-15',
                        'time': '2:00 PM',
                        'duration': 1.0,
                        'invoice_status': 'not_invoiced',
                        'selected': True,
                        'synopsis': '',
                        'edited_start_time': None,
                        'edited_duration': None,
                        'custom_rate': None,
                        'is_edited': False
                    }
                ]
            }
        }
        
        # Test commands with extra spaces
        mock_input.side_effect = [
            '  rate   1   250.50  ',  # Extra spaces in rate command
            'continue',
            'Test synopsis'
        ]
        
        test_invoicer.display_meetings_interactive(customers_with_meetings, 150.0)
        
        # Should parse command correctly despite extra spaces
        assert customers_with_meetings['cus_TEST123']['meetings'][0]['custom_rate'] == 250.50
    
    def test_invalid_meeting_numbers(self, test_invoicer, mock_input, mock_print):
        """Test handling of invalid meeting numbers in commands"""
        customers_with_meetings = {
            'cus_TEST123': {
                'customer': {'id': 'cus_TEST123', 'name': 'Test Customer', 'email': 'test@example.com'},
                'meetings': [
                    {
                        'id': 'meet_1',
                        'summary': 'Meeting 1',
                        'date': '2025-01-15',
                        'time': '2:00 PM',
                        'duration': 1.0,
                        'invoice_status': 'not_invoiced',
                        'selected': True,
                        'synopsis': '',
                        'edited_start_time': None,
                        'edited_duration': None,
                        'custom_rate': None,
                        'is_edited': False
                    }
                ]
            }
        }
        
        mock_input.side_effect = [
            '999',  # Invalid meeting number
            'edit 0',  # Zero meeting number
            'edit -1',  # Negative meeting number
            'edit abc',  # Non-numeric meeting number
            'continue',
            'Test synopsis'
        ]
        
        result = test_invoicer.display_meetings_interactive(customers_with_meetings, 150.0)
        
        # Should handle invalid numbers gracefully without crashing
        assert result is not None
    
    def test_malformed_rate_commands(self, test_invoicer, mock_input, mock_print):
        """Test handling of malformed rate commands"""
        customers_with_meetings = {
            'cus_TEST123': {
                'customer': {'id': 'cus_TEST123', 'name': 'Test Customer', 'email': 'test@example.com'},
                'meetings': [
                    {
                        'id': 'meet_1',
                        'summary': 'Meeting 1',
                        'date': '2025-01-15',
                        'time': '2:00 PM',
                        'duration': 1.0,
                        'invoice_status': 'not_invoiced',
                        'selected': True,
                        'synopsis': '',
                        'edited_start_time': None,
                        'edited_duration': None,
                        'custom_rate': None,
                        'is_edited': False
                    }
                ]
            }
        }
        
        mock_input.side_effect = [
            'rate 1',  # Missing rate value
            'rate 1 abc',  # Invalid rate value
            'rate 1 -50',  # Negative rate
            'rate',  # Missing both meeting and rate
            'continue',
            'Test synopsis'
        ]
        
        result = test_invoicer.display_meetings_interactive(customers_with_meetings, 150.0)
        
        # Custom rate should remain None due to invalid commands
        assert customers_with_meetings['cus_TEST123']['meetings'][0]['custom_rate'] is None


class TestInteractiveCommands:
    """Test the interactive command system"""
    
    def test_meeting_selection_toggle(self, test_invoicer, mock_input, mock_print):
        """Test toggling meeting selection on and off"""
        # Set up test data
        customers_with_meetings = {
            'cus_TEST123': {
                'customer': {'id': 'cus_TEST123', 'name': 'Test Customer', 'email': 'test@example.com'},
                'meetings': [
                    {
                        'id': 'meet_1',
                        'summary': 'Meeting 1',
                        'date': '2025-01-15',
                        'time': '2:00 PM',
                        'duration': 1.0,
                        'invoice_status': 'not_invoiced',
                        'selected': True,
                        'synopsis': '',
                        'edited_start_time': None,
                        'edited_duration': None,
                        'custom_rate': None,
                        'is_edited': False
                    }
                ]
            }
        }
        
        # Simulate user toggling selection and then continuing
        # Need to provide synopsis input too since continue leads to synopsis entry
        mock_input.side_effect = ['1', '1', 'continue', 'Test synopsis']
        
        result = test_invoicer.display_meetings_interactive(customers_with_meetings, 150.0)
        
        # Meeting should be deselected after first toggle, then selected again
        assert mock_input.call_count >= 3
        assert result == customers_with_meetings
    
    def test_all_command(self, test_invoicer, mock_input, mock_print):
        """Test 'all' command to select all uninvoiced meetings"""
        customers_with_meetings = {
            'cus_TEST123': {
                'customer': {'id': 'cus_TEST123', 'name': 'Test Customer', 'email': 'test@example.com'},
                'meetings': [
                    {
                        'id': 'meet_1',
                        'summary': 'Meeting 1',
                        'date': '2025-01-15',
                        'time': '2:00 PM',
                        'duration': 1.0,
                        'invoice_status': 'not_invoiced',
                        'selected': False,
                        'synopsis': '',
                        'edited_start_time': None,
                        'edited_duration': None,
                        'custom_rate': None,
                        'is_edited': False
                    },
                    {
                        'id': 'meet_2',
                        'summary': 'Meeting 2',
                        'date': '2025-01-16',
                        'time': '3:00 PM',
                        'duration': 1.5,
                        'invoice_status': 'sent',
                        'selected': False,
                        'synopsis': '',
                        'edited_start_time': None,
                        'edited_duration': None,
                        'custom_rate': None,
                        'is_edited': False
                    }
                ]
            }
        }
        
        mock_input.side_effect = ['all', 'continue', 'Meeting 1 synopsis']
        
        result = test_invoicer.display_meetings_interactive(customers_with_meetings, 150.0)
        
        # Only uninvoiced meeting should be selected
        assert customers_with_meetings['cus_TEST123']['meetings'][0]['selected'] is True
        assert customers_with_meetings['cus_TEST123']['meetings'][1]['selected'] is False
    
    def test_none_command(self, test_invoicer, mock_input, mock_print):
        """Test 'none' command to deselect all meetings"""
        customers_with_meetings = {
            'cus_TEST123': {
                'customer': {'id': 'cus_TEST123', 'name': 'Test Customer', 'email': 'test@example.com'},
                'meetings': [
                    {
                        'id': 'meet_1',
                        'summary': 'Meeting 1',
                        'date': '2025-01-15',
                        'time': '2:00 PM',
                        'duration': 1.0,
                        'invoice_status': 'not_invoiced',
                        'selected': True,
                        'synopsis': '',
                        'edited_start_time': None,
                        'edited_duration': None,
                        'custom_rate': None,
                        'is_edited': False
                    }
                ]
            }
        }
        
        # 'none' deselects all, so no synopsis needed
        mock_input.side_effect = ['none', 'continue']
        
        result = test_invoicer.display_meetings_interactive(customers_with_meetings, 150.0)
        
        # All meetings should be deselected
        assert customers_with_meetings['cus_TEST123']['meetings'][0]['selected'] is False
    
    def test_edit_command(self, test_invoicer, mock_input, mock_print, mocker):
        """Test 'edit' command for modifying meeting time and duration"""
        customers_with_meetings = {
            'cus_TEST123': {
                'customer': {'id': 'cus_TEST123', 'name': 'Test Customer', 'email': 'test@example.com'},
                'meetings': [
                    {
                        'id': 'meet_1',
                        'summary': 'Meeting 1',
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
                ]
            }
        }
        
        # Mock the edit_meeting_details method
        mock_edit = mocker.patch.object(test_invoicer, 'edit_meeting_details')
        mock_edit.return_value = True
        
        mock_input.side_effect = ['edit 1', 'continue', 'Meeting synopsis']
        
        result = test_invoicer.display_meetings_interactive(customers_with_meetings, 150.0)
        
        # Verify edit_meeting_details was called
        mock_edit.assert_called_once()
    
    def test_time_command(self, test_invoicer, mock_input, mock_print, mocker):
        """Test 'time' command as shortcut for edit"""
        customers_with_meetings = {
            'cus_TEST123': {
                'customer': {'id': 'cus_TEST123', 'name': 'Test Customer', 'email': 'test@example.com'},
                'meetings': [
                    {
                        'id': 'meet_1',
                        'summary': 'Meeting 1',
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
                ]
            }
        }
        
        # Mock the edit_meeting_details method
        mock_edit = mocker.patch.object(test_invoicer, 'edit_meeting_details')
        mock_edit.return_value = True
        
        mock_input.side_effect = ['time 1', 'continue', 'Meeting synopsis']
        
        result = test_invoicer.display_meetings_interactive(customers_with_meetings, 150.0)
        
        # Verify edit_meeting_details was called
        mock_edit.assert_called_once()
    
    def test_rate_command(self, test_invoicer, mock_input, mock_print):
        """Test 'rate' command for setting custom meeting rate"""
        customers_with_meetings = {
            'cus_TEST123': {
                'customer': {'id': 'cus_TEST123', 'name': 'Test Customer', 'email': 'test@example.com'},
                'meetings': [
                    {
                        'id': 'meet_1',
                        'summary': 'Meeting 1',
                        'date': '2025-01-15',
                        'time': '2:00 PM',
                        'duration': 1.0,
                        'invoice_status': 'not_invoiced',
                        'selected': True,
                        'synopsis': '',
                        'edited_start_time': None,
                        'edited_duration': None,
                        'custom_rate': None,
                        'is_edited': False
                    }
                ]
            }
        }
        
        mock_input.side_effect = ['rate 1 250', 'continue', 'Meeting synopsis']
        
        result = test_invoicer.display_meetings_interactive(customers_with_meetings, 150.0)
        
        # Verify custom rate was set
        assert customers_with_meetings['cus_TEST123']['meetings'][0]['custom_rate'] == 250.0
    
    def test_setrate_command(self, test_invoicer, mock_input, mock_print, mocker):
        """Test 'setrate' command for updating customer default rate"""
        customers_with_meetings = {
            'cus_TEST123': {
                'customer': {'id': 'cus_TEST123', 'name': 'Test Customer', 'email': 'test@example.com'},
                'meetings': [
                    {
                        'id': 'meet_1',
                        'summary': 'Meeting 1',
                        'date': '2025-01-15',
                        'time': '2:00 PM',
                        'duration': 1.0,
                        'invoice_status': 'not_invoiced',
                        'selected': True,
                        'synopsis': '',
                        'edited_start_time': None,
                        'edited_duration': None,
                        'custom_rate': None,
                        'is_edited': False
                    }
                ]
            }
        }
        
        # Mock set_customer_hourly_rate
        mock_set_rate = mocker.patch.object(test_invoicer, 'set_customer_hourly_rate')
        mock_set_rate.return_value = True
        
        mock_input.side_effect = ['setrate test@example.com 300', 'continue', 'Meeting synopsis']
        
        result = test_invoicer.display_meetings_interactive(customers_with_meetings, 150.0)
        
        # Verify set_customer_hourly_rate was called
        mock_set_rate.assert_called_once_with('cus_TEST123', 300.0)
    
    def test_invalid_commands(self, test_invoicer, mock_input, mock_print):
        """Test handling of invalid commands"""
        customers_with_meetings = {
            'cus_TEST123': {
                'customer': {'id': 'cus_TEST123', 'name': 'Test Customer', 'email': 'test@example.com'},
                'meetings': [
                    {
                        'id': 'meet_1',
                        'summary': 'Meeting 1',
                        'date': '2025-01-15',
                        'time': '2:00 PM',
                        'duration': 1.0,
                        'invoice_status': 'not_invoiced',
                        'selected': True,
                        'synopsis': '',
                        'edited_start_time': None,
                        'edited_duration': None,
                        'custom_rate': None,
                        'is_edited': False
                    }
                ]
            }
        }
        
        mock_input.side_effect = [
            'invalid',          # Invalid command
            '99',              # Invalid meeting number
            'rate 1',          # Missing rate value
            'setrate',         # Missing email and rate
            'continue',
            'Meeting synopsis'  # For the selected meeting
        ]
        
        result = test_invoicer.display_meetings_interactive(customers_with_meetings, 150.0)
        
        # Should handle errors gracefully and continue
        assert result == customers_with_meetings
        print_calls = [str(call) for call in mock_print.call_args_list]
        # Should show error messages for invalid commands
        assert any('Invalid' in call or 'not found' in call or 'Usage:' in call for call in print_calls), "Should show error messages for invalid inputs"


class TestEditMeetingDetails:
    """Test the edit_meeting_details function"""
    
    def test_edit_meeting_time_only(self, test_invoicer, mock_input, mock_print):
        """Test editing only the meeting time"""
        meeting = {
            'id': 'meet_1',
            'summary': 'Test Meeting',
            'date': '2025-01-15',
            'time': '2:00 PM',
            'duration': 1.0,
            'edited_start_time': None,
            'edited_duration': None,
            'is_edited': False
        }
        customer_data = {'customer': {'name': 'Test Customer'}}
        
        # Edit time to 3:30 PM, keep duration
        mock_input.side_effect = ['3:30 PM', '']
        
        result = test_invoicer.edit_meeting_details(meeting, customer_data)
        
        assert result is True
        assert meeting['edited_start_time'] == time(15, 30)
        assert meeting['edited_duration'] is None
        assert meeting['is_edited'] is True
    
    def test_edit_meeting_duration_only(self, test_invoicer, mock_input, mock_print):
        """Test editing only the meeting duration"""
        meeting = {
            'id': 'meet_1',
            'summary': 'Test Meeting',
            'date': '2025-01-15',
            'time': '2:00 PM',
            'duration': 1.0,
            'edited_start_time': None,
            'edited_duration': None,
            'is_edited': False
        }
        customer_data = {'customer': {'name': 'Test Customer'}}
        
        # Keep time, edit duration to 1.5 hours
        mock_input.side_effect = ['', '1.5']
        
        result = test_invoicer.edit_meeting_details(meeting, customer_data)
        
        assert result is True
        assert meeting['edited_start_time'] is None
        assert meeting['edited_duration'] == 1.5
        assert meeting['is_edited'] is True
    
    def test_edit_meeting_reset_to_original(self, test_invoicer, mock_input, mock_print):
        """Test resetting edited values to original"""
        meeting = {
            'id': 'meet_1',
            'summary': 'Test Meeting',
            'date': '2025-01-15',
            'time': '2:00 PM',
            'duration': 1.0,
            'edited_start_time': time(15, 30),
            'edited_duration': 1.5,
            'is_edited': True
        }
        customer_data = {'customer': {'name': 'Test Customer'}}
        
        # Reset both to original
        mock_input.side_effect = ['original', 'original']
        
        result = test_invoicer.edit_meeting_details(meeting, customer_data)
        
        assert result is True
        assert meeting['edited_start_time'] is None
        assert meeting['edited_duration'] is None
        assert meeting['is_edited'] is False


class TestSynopsisEntry:
    """Test synopsis entry for selected meetings"""
    
    def test_synopsis_entry_with_default(self, test_invoicer, mock_input, mock_print):
        """Test entering synopsis with default value"""
        customers_with_meetings = {
            'cus_TEST123': {
                'customer': {'id': 'cus_TEST123', 'name': 'Test Customer', 'email': 'test@example.com'},
                'meetings': [
                    {
                        'id': 'meet_1',
                        'summary': 'Project Meeting',
                        'date': '2025-01-15',
                        'time': '2:00 PM',
                        'duration': 1.0,
                        'selected': True,
                        'synopsis': '',
                        'edited_start_time': None,
                        'edited_duration': None,
                        'custom_rate': None,
                        'is_edited': False
                    }
                ]
            }
        }
        
        # Press enter to use default (meeting summary)
        mock_input.side_effect = ['']
        
        result = test_invoicer.get_synopsis_for_selected_meetings(customers_with_meetings)
        
        # Should use meeting summary as default
        assert customers_with_meetings['cus_TEST123']['meetings'][0]['synopsis'] == 'Project Meeting'
    
    def test_synopsis_entry_custom(self, test_invoicer, mock_input, mock_print):
        """Test entering custom synopsis"""
        customers_with_meetings = {
            'cus_TEST123': {
                'customer': {'id': 'cus_TEST123', 'name': 'Test Customer', 'email': 'test@example.com'},
                'meetings': [
                    {
                        'id': 'meet_1',
                        'summary': 'Project Meeting',
                        'date': '2025-01-15',
                        'time': '2:00 PM',
                        'duration': 1.0,
                        'selected': True,
                        'synopsis': '',
                        'edited_start_time': None,
                        'edited_duration': None,
                        'custom_rate': None,
                        'is_edited': False
                    }
                ]
            }
        }
        
        # Enter custom synopsis
        mock_input.side_effect = ['Discussed Q1 roadmap and budget planning']
        
        result = test_invoicer.get_synopsis_for_selected_meetings(customers_with_meetings)
        
        # Should use custom synopsis
        assert customers_with_meetings['cus_TEST123']['meetings'][0]['synopsis'] == 'Discussed Q1 roadmap and budget planning'