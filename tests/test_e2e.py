"""
End-to-end tests for complete invoice automation workflows
"""
import pytest
from unittest.mock import Mock, MagicMock, call, patch
from datetime import datetime, timedelta, time
import stripe


class TestEndToEndScenarios:
    """Test complete workflows from meeting detection to invoice creation"""
    
    def test_single_customer_multiple_meetings_workflow(self, test_invoicer, mocker):
        """Test complete workflow with one customer and multiple meetings"""
        # Mock data
        customer = {
            'id': 'cus_ALICE',
            'email': 'alice@company.com',
            'name': 'Alice Smith',
            'metadata': {'hourly_rate': '200.00'}
        }
        
        base_date = datetime.now() - timedelta(days=2)
        calendar_events = [
            {
                'id': 'evt_1',
                'summary': 'Strategy Session',
                'start': {'dateTime': base_date.replace(hour=10, minute=0, second=0, microsecond=0).isoformat()},
                'end': {'dateTime': base_date.replace(hour=11, minute=0, second=0, microsecond=0).isoformat()},
                'attendees': [{'email': 'alice@company.com'}]
            },
            {
                'id': 'evt_2',
                'summary': 'Follow-up Meeting',
                'start': {'dateTime': (base_date + timedelta(days=1)).replace(hour=14, minute=0, second=0, microsecond=0).isoformat()},
                'end': {'dateTime': (base_date + timedelta(days=1)).replace(hour=15, minute=30, second=0, microsecond=0).isoformat()},
                'attendees': [{'email': 'alice@company.com'}]
            }
        ]
        
        # Mock invoice status check (all not invoiced)
        mocker.patch.object(test_invoicer, 'check_meeting_invoice_status', return_value='not_invoiced')
        
        # Find customers with meetings
        customers_with_meetings = test_invoicer.find_customers_with_meetings([customer], calendar_events)
        
        # Verify meetings found
        assert len(customers_with_meetings) == 1
        assert 'cus_ALICE' in customers_with_meetings
        assert len(customers_with_meetings['cus_ALICE']['meetings']) == 2
        
        # Verify meeting details
        meetings = customers_with_meetings['cus_ALICE']['meetings']
        assert meetings[0]['summary'] == 'Strategy Session'
        assert meetings[0]['duration'] == 1.0
        assert meetings[1]['summary'] == 'Follow-up Meeting'
        assert meetings[1]['duration'] == 1.5
        
        # Mock interactive selection (select all meetings)
        mock_input = mocker.patch('builtins.input')
        mock_input.side_effect = ['all', 'continue', 'Strategy planning discussion', 'Project status update']
        
        # Run interactive selection
        test_invoicer.display_meetings_interactive(customers_with_meetings, 150.0)
        
        # Verify synopses were set
        assert meetings[0]['synopsis'] == 'Strategy planning discussion'
        assert meetings[1]['synopsis'] == 'Project status update'
        
        # Mock invoice creation
        mock_invoice_create = mocker.patch('stripe.Invoice.create')
        mock_invoice_create.return_value = MagicMock(id='inv_TEST123')
        mock_item_create = mocker.patch('stripe.InvoiceItem.create')
        
        # Create invoice
        selected_meetings = [m for m in meetings if m['selected']]
        invoice = test_invoicer.create_draft_invoice(customer, selected_meetings, 200.0)
        
        # Verify invoice created
        assert invoice.id == 'inv_TEST123'
        assert mock_item_create.call_count == 2  # Two line items
        
        # Verify line item amounts
        calls = mock_item_create.call_args_list
        assert calls[0][1]['amount'] == 20000  # 1 hour * $200 = $200 in cents
        assert calls[1][1]['amount'] == 30000  # 1.5 hours * $200 = $300 in cents
    
    def test_edited_meeting_workflow(self, test_invoicer, mocker):
        """Test workflow with edited meeting times and durations"""
        # Mock data
        customer = {
            'id': 'cus_BOB',
            'email': 'bob@company.com',
            'name': 'Bob Johnson',
            'metadata': {'hourly_rate': '150.00'}
        }
        
        calendar_event = {
            'id': 'evt_1',
            'summary': 'Client Consultation',
            'start': {'dateTime': '2025-01-15T14:00:00'},
            'end': {'dateTime': '2025-01-15T15:00:00'},
            'attendees': [{'email': 'bob@company.com'}]
        }
        
        # Mock APIs
        mocker.patch.object(test_invoicer, 'check_meeting_invoice_status', return_value='not_invoiced')
        
        # Find meetings
        customers_with_meetings = test_invoicer.find_customers_with_meetings([customer], [calendar_event])
        meeting = customers_with_meetings['cus_BOB']['meetings'][0]
        
        # Simulate editing the meeting
        mock_input = mocker.patch('builtins.input')
        mock_input.side_effect = [
            'edit 1',           # Edit command
            '3:30 PM',          # New start time
            '2.5',              # New duration
            'continue',         # Continue to synopsis
            'Extended consultation covering multiple topics'
        ]
        
        # Run interactive selection
        test_invoicer.display_meetings_interactive(customers_with_meetings, 150.0)
        
        # Verify meeting was edited
        assert meeting['edited_start_time'] == time(15, 30)
        assert meeting['edited_duration'] == 2.5
        assert meeting['is_edited'] is True
        
        # Mock invoice creation
        mock_invoice_create = mocker.patch('stripe.Invoice.create')
        mock_invoice_create.return_value = MagicMock(id='inv_TEST456')
        mock_item_create = mocker.patch('stripe.InvoiceItem.create')
        
        # Create invoice
        selected_meetings = [meeting]
        invoice = test_invoicer.create_draft_invoice(customer, selected_meetings, 150.0)
        
        # Verify invoice uses edited values
        call_args = mock_item_create.call_args[1]
        assert call_args['amount'] == 37500  # 2.5 hours * $150 = $375 in cents
        assert '3:30 PM' in call_args['description']
        assert '2.5h' in call_args['description']
    
    def test_custom_rate_workflow(self, test_invoicer, mocker):
        """Test workflow with custom rates per meeting"""
        # Mock data
        customer = {
            'id': 'cus_CHARLIE',
            'email': 'charlie@company.com',
            'name': 'Charlie Brown',
            'metadata': {}  # No default rate
        }
        
        calendar_events = [
            {
                'id': 'evt_1',
                'summary': 'Regular Meeting',
                'start': {'dateTime': '2025-01-15T10:00:00'},
                'end': {'dateTime': '2025-01-15T11:00:00'},
                'attendees': [{'email': 'charlie@company.com'}]
            },
            {
                'id': 'evt_2',
                'summary': 'Premium Consultation',
                'start': {'dateTime': '2025-01-16T14:00:00'},
                'end': {'dateTime': '2025-01-16T16:00:00'},
                'attendees': [{'email': 'charlie@company.com'}]
            }
        ]
        
        # Mock APIs
        mocker.patch.object(test_invoicer, 'check_meeting_invoice_status', return_value='not_invoiced')
        
        # Find meetings
        customers_with_meetings = test_invoicer.find_customers_with_meetings([customer], calendar_events)
        meetings = customers_with_meetings['cus_CHARLIE']['meetings']
        
        # Simulate setting custom rates
        mock_input = mocker.patch('builtins.input')
        mock_input.side_effect = [
            'rate 1 175',       # Set rate for first meeting
            'rate 2 350',       # Set premium rate for second meeting
            'continue',         # Continue to synopsis
            'Regular check-in',
            'Advanced technical consultation'
        ]
        
        # Run interactive selection
        test_invoicer.display_meetings_interactive(customers_with_meetings, 150.0)  # Default rate 150
        
        # Verify custom rates were set
        assert meetings[0]['custom_rate'] == 175.0
        assert meetings[1]['custom_rate'] == 350.0
        
        # Mock invoice creation
        mock_invoice_create = mocker.patch('stripe.Invoice.create')
        mock_invoice_create.return_value = MagicMock(id='inv_TEST789')
        mock_item_create = mocker.patch('stripe.InvoiceItem.create')
        
        # Create invoice
        invoice = test_invoicer.create_draft_invoice(customer, meetings, 150.0)
        
        # Verify invoice uses custom rates
        calls = mock_item_create.call_args_list
        assert calls[0][1]['amount'] == 17500  # 1 hour * $175 = $175 in cents
        assert calls[1][1]['amount'] == 70000  # 2 hours * $350 = $700 in cents
    
    def test_customer_rate_update_workflow(self, test_invoicer, mocker):
        """Test updating customer default rate during workflow"""
        customer = {
            'id': 'cus_DAVE',
            'email': 'dave@company.com',
            'name': 'Dave Wilson',
            'metadata': {'hourly_rate': '100.00'}
        }
        
        calendar_event = {
            'id': 'evt_1',
            'summary': 'Consultation',
            'start': {'dateTime': '2025-01-15T10:00:00'},
            'end': {'dateTime': '2025-01-15T11:00:00'},
            'attendees': [{'email': 'dave@company.com'}]
        }
        
        # Mock APIs
        mocker.patch.object(test_invoicer, 'check_meeting_invoice_status', return_value='not_invoiced')
        
        # Mock customer rate update
        mock_customer_modify = mocker.patch('stripe.Customer.modify')
        
        # Find meetings
        customers_with_meetings = test_invoicer.find_customers_with_meetings([customer], [calendar_event])
        
        # Simulate updating customer rate
        mock_input = mocker.patch('builtins.input')
        mock_input.side_effect = [
            'setrate dave@company.com 200',  # Update customer rate
            'continue',                      # Continue to synopsis
            'Business consultation'
        ]
        
        # Run interactive selection
        test_invoicer.display_meetings_interactive(customers_with_meetings, 150.0)
        
        # Verify customer rate was updated in Stripe
        mock_customer_modify.assert_called_once_with(
            'cus_DAVE',
            metadata={'hourly_rate': '200.0'}
        )
    
    def test_edge_case_no_meetings(self, test_invoicer, mocker):
        """Test behavior when no meetings are found"""
        customer = {
            'id': 'cus_EMPTY',
            'email': 'empty@company.com',
            'name': 'Empty Customer',
            'metadata': {}
        }
        
        # Find meetings with empty events
        customers_with_meetings = test_invoicer.find_customers_with_meetings([customer], [])
        
        # Should return empty dict
        assert customers_with_meetings == {}
    
    def test_edge_case_all_meetings_invoiced(self, test_invoicer, mocker):
        """Test behavior when all meetings are already invoiced"""
        customer = {
            'id': 'cus_INVOICED',
            'email': 'invoiced@company.com',
            'name': 'Invoiced Customer',
            'metadata': {'hourly_rate': '200.00'}
        }
        
        calendar_event = {
            'id': 'evt_1',
            'summary': 'Already Billed Meeting',
            'start': {'dateTime': '2025-01-15T10:00:00'},
            'end': {'dateTime': '2025-01-15T11:00:00'},
            'attendees': [{'email': 'invoiced@company.com'}]
        }
        
        # Mock all meetings as already invoiced
        mocker.patch.object(test_invoicer, 'check_meeting_invoice_status', return_value='sent')
        
        # Find meetings
        customers_with_meetings = test_invoicer.find_customers_with_meetings([customer], [calendar_event])
        
        # Should find the meeting but it should not be selected
        assert len(customers_with_meetings) == 1
        meeting = customers_with_meetings['cus_INVOICED']['meetings'][0]
        assert meeting['invoice_status'] == 'sent'
        assert meeting['selected'] is False
    
    def test_error_recovery_stripe_failure(self, test_invoicer, mocker):
        """Test graceful handling of Stripe API failures"""
        # Mock Stripe error
        mocker.patch('stripe.Customer.list').side_effect = stripe.error.APIError("Stripe is down")
        
        # Should return empty customer list
        customers = test_invoicer.get_stripe_customers()
        assert customers == []
    
    def test_error_recovery_calendar_failure(self, test_invoicer, mocker):
        """Test graceful handling of Calendar API failures"""
        customer = {
            'id': 'cus_TEST',
            'email': 'test@company.com',
            'name': 'Test Customer',
            'metadata': {}
        }
        
        # Test with empty events (simulating calendar fetch failure)
        customers_with_meetings = test_invoicer.find_customers_with_meetings([customer], [])
        assert customers_with_meetings == {}