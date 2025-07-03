"""
Integration tests for Stripe and Google Calendar API interactions
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
import stripe
from datetime import datetime, timedelta


class TestStripeIntegration:
    """Test Stripe API integration with mocked responses"""
    
    def test_get_stripe_customers_success(self, test_invoicer, mocker, mock_stripe_customers):
        """Test successful customer fetching from Stripe"""
        # Convert dict customers to object-like structure
        from types import SimpleNamespace
        customer_objects = []
        for c in mock_stripe_customers:
            obj = SimpleNamespace(**c)
            obj.metadata = c.get('metadata', {})
            customer_objects.append(obj)
        
        # Mock stripe.Customer.list to return our test data
        mock_list = mocker.patch('stripe.Customer.list')
        mock_list.return_value = MagicMock(
            data=customer_objects,
            has_more=False
        )
        
        customers = test_invoicer.get_stripe_customers()
        
        # Verify the call was made
        mock_list.assert_called_once_with(limit=100)
        
        # Verify the returned data
        assert len(customers) == 3
        assert customers[0]['email'] == 'alice@company1.com'
        assert customers[1]['email'] == 'bob@company2.com'
        assert customers[2]['email'] == 'charlie@company3.com'
    
    def test_get_stripe_customers_pagination(self, test_invoicer, mocker):
        """Test customer fetching with pagination"""
        from types import SimpleNamespace
        
        # First page
        first_page_data = [
            SimpleNamespace(id='cus_1', email='customer1@test.com', name='Customer 1', created=1609459200, metadata={}),
            SimpleNamespace(id='cus_2', email='customer2@test.com', name='Customer 2', created=1609459200, metadata={})
        ]
        first_page = MagicMock(
            data=first_page_data,
            has_more=True
        )
        
        # Second page
        second_page_data = [
            SimpleNamespace(id='cus_3', email='customer3@test.com', name='Customer 3', created=1609459200, metadata={})
        ]
        second_page = MagicMock(
            data=second_page_data,
            has_more=False
        )
        
        mock_list = mocker.patch('stripe.Customer.list')
        mock_list.side_effect = [first_page, second_page]
        
        customers = test_invoicer.get_stripe_customers()
        
        # Verify pagination calls
        assert mock_list.call_count == 2
        mock_list.assert_any_call(limit=100)
        mock_list.assert_any_call(limit=100, starting_after='cus_2')
        
        # Verify all customers returned
        assert len(customers) == 3
        assert customers[0]['email'] == 'customer1@test.com'
        assert customers[2]['email'] == 'customer3@test.com'
    
    def test_get_stripe_customers_error_handling(self, test_invoicer, mocker):
        """Test error handling when fetching customers"""
        mock_list = mocker.patch('stripe.Customer.list')
        mock_list.side_effect = stripe.error.APIError("API Error")
        
        customers = test_invoicer.get_stripe_customers()
        
        # Should return empty list on error
        assert customers == []
    
    def test_set_customer_hourly_rate_success(self, test_invoicer, mocker):
        """Test setting customer hourly rate"""
        mock_modify = mocker.patch('stripe.Customer.modify')
        
        result = test_invoicer.set_customer_hourly_rate('cus_TEST123', 250.0)
        
        # Verify the API call
        mock_modify.assert_called_once_with(
            'cus_TEST123',
            metadata={'hourly_rate': '250.0'}
        )
        
        assert result is True
    
    def test_set_customer_hourly_rate_error(self, test_invoicer, mocker):
        """Test error handling when setting customer rate"""
        mock_modify = mocker.patch('stripe.Customer.modify')
        mock_modify.side_effect = stripe.error.InvalidRequestError(
            "Customer not found", None
        )
        
        result = test_invoicer.set_customer_hourly_rate('cus_INVALID', 250.0)
        
        assert result is False
    
    def test_get_customer_invoices_success(self, test_invoicer, mocker, sample_invoice):
        """Test fetching invoices for a customer"""
        mock_list = mocker.patch('stripe.Invoice.list')
        mock_list.return_value = MagicMock(data=[sample_invoice])
        
        invoices = test_invoicer.get_customer_invoices('cus_TEST123')
        
        # Verify the API call
        mock_list.assert_called_once_with(customer='cus_TEST123', limit=100)
        
        # Verify the returned data
        assert len(invoices) == 1
        assert invoices[0]['id'] == 'inv_TEST123'
    
    def test_create_draft_invoice_success(self, test_invoicer, mocker, sample_customer, sample_meeting):
        """Test creating a draft invoice"""
        # Mock invoice creation
        mock_invoice = MagicMock(id='inv_NEW123')
        mock_create = mocker.patch('stripe.Invoice.create')
        mock_create.return_value = mock_invoice
        
        # Mock invoice item creation
        mock_item_create = mocker.patch('stripe.InvoiceItem.create')
        
        # Create invoice with one meeting
        meetings = [sample_meeting]
        meetings[0]['synopsis'] = 'Test meeting discussion'
        
        invoice = test_invoicer.create_draft_invoice(sample_customer, meetings, 200.0)
        
        # Verify invoice creation
        mock_create.assert_called_once_with(
            customer='cus_TEST123',
            auto_advance=False,
            collection_method='send_invoice',
            days_until_due=30,
            description='Consultation services for 1 meeting(s) @ $200.0/hour'
        )
        
        # Verify line item creation
        mock_item_create.assert_called_once()
        call_args = mock_item_create.call_args[1]
        assert call_args['customer'] == 'cus_TEST123'
        assert call_args['invoice'] == 'inv_NEW123'
        assert call_args['amount'] == 20000  # $200 in cents
        assert 'Test meeting discussion' in call_args['description']
        assert '[ID:meet_123]' in call_args['description']
        
        assert invoice.id == 'inv_NEW123'
    
    def test_create_draft_invoice_with_edited_meeting(self, test_invoicer, mocker, sample_customer, sample_edited_meeting):
        """Test creating invoice with edited meeting values"""
        mock_invoice = MagicMock(id='inv_NEW456')
        mock_create = mocker.patch('stripe.Invoice.create')
        mock_create.return_value = mock_invoice
        
        mock_item_create = mocker.patch('stripe.InvoiceItem.create')
        
        # Create invoice with edited meeting
        meetings = [sample_edited_meeting]
        invoice = test_invoicer.create_draft_invoice(sample_customer, meetings, 200.0)
        
        # Verify line item uses edited values
        call_args = mock_item_create.call_args[1]
        # 2.5 hours * $250 custom rate = $625
        assert call_args['amount'] == 62500  # $625 in cents
        assert '2.5h @ $250.0/h' in call_args['description']
        assert '11:30 AM' in call_args['description']  # Edited time


class TestGoogleCalendarIntegration:
    """Test Google Calendar API integration"""
    
    def test_get_calendar_events_success(self, test_invoicer, mocker, mock_calendar_events):
        """Test fetching calendar events"""
        # Mock the calendar service
        mock_service = test_invoicer.calendar_service
        mock_events = Mock()
        mock_service.events.return_value = mock_events
        
        # Mock the list call
        mock_list = Mock()
        mock_events.list.return_value = mock_list
        mock_execute = Mock(return_value={'items': mock_calendar_events})
        mock_list.execute.return_value = {'items': mock_calendar_events}
        
        # Calculate date range
        time_max = datetime.utcnow()
        time_min = time_max - timedelta(days=7)
        
        # Manually call the method with mocked service
        with patch.object(test_invoicer.calendar_service, 'events') as mock_events_method:
            mock_events_api = Mock()
            mock_events_method.return_value = mock_events_api
            
            mock_list_method = Mock()
            mock_events_api.list.return_value = mock_list_method
            
            mock_list_method.execute.return_value = {'items': mock_calendar_events}
            
            events = test_invoicer.get_calendar_events(time_min, time_max)
        
        # Verify the returned data
        assert len(events) == 3
        assert events[0]['summary'] == 'Strategy Session'
        assert events[1]['summary'] == 'Project Review'
        assert events[2]['summary'] == 'Quick Check-in'
    
    def test_get_calendar_events_error_handling(self, test_invoicer, mocker):
        """Test error handling when fetching calendar events"""
        from googleapiclient.errors import HttpError
        
        # Mock the calendar service to raise an error
        with patch.object(test_invoicer.calendar_service, 'events') as mock_events_method:
            # Create a mock that raises HttpError when list() is called
            mock_events_api = Mock()
            mock_events_method.return_value = mock_events_api
            
            mock_list_method = Mock()
            mock_events_api.list.return_value = mock_list_method
            
            # Make execute() raise an HttpError
            import http.client
            resp = Mock(spec=http.client.HTTPResponse)
            resp.status = 500
            resp.reason = 'Internal Server Error'
            mock_list_method.execute.side_effect = HttpError(resp=resp, content=b'API Error')
            
            # Should return empty list on error
            time_max = datetime.utcnow()
            time_min = time_max - timedelta(days=7)
            
            events = test_invoicer.get_calendar_events(time_min, time_max)
            assert events == []
    
    def test_find_customers_with_meetings(self, test_invoicer, mocker, mock_stripe_customers, mock_calendar_events):
        """Test matching calendar events to Stripe customers"""
        # Mock check_meeting_invoice_status to return not_invoiced
        mocker.patch.object(
            test_invoicer,
            'check_meeting_invoice_status',
            return_value='not_invoiced'
        )
        
        # Call with customers and events as parameters
        customers_with_meetings = test_invoicer.find_customers_with_meetings(mock_stripe_customers, mock_calendar_events)
        
        # Verify we found meetings for the right customers
        assert len(customers_with_meetings) == 3
        
        # Check Alice's meetings
        alice_data = customers_with_meetings['cus_ALICE']
        assert alice_data['customer']['name'] == 'Alice Smith'
        assert len(alice_data['meetings']) == 1
        assert alice_data['meetings'][0]['summary'] == 'Strategy Session'
        assert alice_data['meetings'][0]['duration'] == 1.0
        
        # Check Bob's meetings
        bob_data = customers_with_meetings['cus_BOB']
        assert bob_data['customer']['name'] == 'Bob Johnson'
        assert len(bob_data['meetings']) == 1
        assert bob_data['meetings'][0]['summary'] == 'Project Review'
        assert bob_data['meetings'][0]['duration'] == 1.5
        
        # Check Charlie's meetings
        charlie_data = customers_with_meetings['cus_CHARLIE']
        assert charlie_data['customer']['name'] == 'Charlie Brown'
        assert len(charlie_data['meetings']) == 1
        assert charlie_data['meetings'][0]['summary'] == 'Quick Check-in'
        assert charlie_data['meetings'][0]['duration'] == 0.5


