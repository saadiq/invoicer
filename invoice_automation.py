#!/usr/bin/env python3
"""
Stripe Customer Meeting Invoice Automation Script

This script:
1. Fetches customer list from Stripe
2. Checks Google Calendar for recent meetings with those customers
3. Shows interactive interface to select meetings to invoice
4. Tracks which meetings have already been invoiced
5. Creates draft invoices for selected meetings with custom synopses

Required packages:
pip install stripe google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client python-dateutil

Setup Instructions:
1. Set customer hourly rates in Stripe:
   - Go to Stripe Dashboard > Customers > [Customer] > Edit
   - Add metadata: key="hourly_rate", value="200.00"
   - Or use the set_customer_hourly_rate() method in this script
   
2. For customers without a specific rate, the DEFAULT_HOURLY_RATE will be used

Example usage to set rates:
invoicer = StripeCalendarInvoicer(stripe_api_key="sk_...")
invoicer.set_customer_hourly_rate("cus_ABC123", 200.00)  # $200/hour for premium client
invoicer.set_customer_hourly_rate("cus_DEF456", 125.00)  # $125/hour for standard client
"""

import stripe
import os
from datetime import datetime, timedelta
from dateutil import parser
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import json
import logging
import hashlib
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class StripeCalendarInvoicer:
    def __init__(self, stripe_api_key, calendar_credentials_file='credentials.json', 
                 token_file='token.json', days_back=7):
        """
        Initialize the invoicing automation
        
        Args:
            stripe_api_key: Your Stripe secret API key
            calendar_credentials_file: Path to Google Calendar API credentials JSON
            token_file: Path to store Google OAuth token
            days_back: Number of days back to check for meetings
        """
        self.stripe_api_key = stripe_api_key
        self.calendar_credentials_file = calendar_credentials_file
        self.token_file = token_file
        self.days_back = days_back
        self.calendar_scopes = ['https://www.googleapis.com/auth/calendar.readonly']
        
        # Initialize Stripe
        stripe.api_key = self.stripe_api_key
        
        # Initialize Google Calendar service
        self.calendar_service = self._get_calendar_service()
    
    def _get_calendar_service(self):
        """Authenticate and return Google Calendar service"""
        creds = None
        
        # Load existing token
        if os.path.exists(self.token_file):
            creds = Credentials.from_authorized_user_file(self.token_file, self.calendar_scopes)
        
        # If no valid credentials, get new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.calendar_credentials_file, self.calendar_scopes)
                creds = flow.run_local_server(port=0)
            
            # Save credentials for next run
            with open(self.token_file, 'w') as token:
                token.write(creds.to_json())
        
        return build('calendar', 'v3', credentials=creds)
    
    def generate_meeting_id(self, customer_email, start_time, summary):
        """Generate a unique identifier for a meeting"""
        # Create a hash from customer email, start time, and summary
        meeting_string = f"{customer_email}|{start_time}|{summary}"
        return hashlib.md5(meeting_string.encode()).hexdigest()[:12]
    
    def get_customer_invoices(self, customer_id):
        """Get all invoices for a customer"""
        try:
            invoices = stripe.Invoice.list(customer=customer_id, limit=100)
            return invoices.data
        except Exception as e:
            logger.error(f"Error fetching invoices for customer {customer_id}: {e}")
            return []
    
    def check_meeting_invoice_status(self, customer_id, meeting_id):
        """Check if a meeting has been invoiced and return status"""
        invoices = self.get_customer_invoices(customer_id)
        
        for invoice in invoices:
            # Check line items for this meeting ID
            line_items = stripe.InvoiceLineItem.list(invoice=invoice.id, limit=100)
            for item in line_items.data:
                if meeting_id in (item.description or ""):
                    if invoice.status == 'draft':
                        return 'drafted'
                    elif invoice.status in ['open', 'paid', 'uncollectible']:
                        return 'sent'
        
        return 'not_invoiced'
    
    def set_customer_hourly_rate(self, customer_id, hourly_rate):
        """Set hourly rate for a specific customer in Stripe metadata"""
        try:
            stripe.Customer.modify(
                customer_id,
                metadata={'hourly_rate': str(hourly_rate)}
            )
            logger.info(f"Set hourly rate for customer {customer_id}: ${hourly_rate}/hour")
            return True
        except Exception as e:
            logger.error(f"Error setting hourly rate for customer {customer_id}: {e}")
            return False
    
    def get_customer_hourly_rate(self, customer, default_rate):
        """Get hourly rate for a customer from metadata or use default"""
        try:
            # Check for hourly_rate in customer metadata
            rate = customer.get('metadata', {}).get('hourly_rate')
            if rate:
                return float(rate)
            
            # Fallback to default rate
            logger.info(f"No hourly rate set for {customer.get('name', 'Unknown')}, using default: ${default_rate}")
            return default_rate
            
        except (ValueError, TypeError):
            logger.warning(f"Invalid hourly rate in metadata for {customer.get('name', 'Unknown')}, using default: ${default_rate}")
            return default_rate
    
    def get_stripe_customers(self):
        """Fetch all customers from Stripe with email addresses"""
        logger.info("Fetching Stripe customers...")
        customers = []
        
        try:
            # Fetch customers in batches
            has_more = True
            starting_after = None
            
            while has_more:
                params = {'limit': 100}
                if starting_after:
                    params['starting_after'] = starting_after
                
                response = stripe.Customer.list(**params)
                
                for customer in response.data:
                    if customer.email:  # Only include customers with email addresses
                        customers.append({
                            'id': customer.id,
                            'email': customer.email.lower(),
                            'name': customer.name or 'Unknown',
                            'created': customer.created,
                            'metadata': customer.metadata or {}
                        })
                
                has_more = response.has_more
                if has_more:
                    starting_after = response.data[-1].id
            
            logger.info(f"Found {len(customers)} customers with email addresses")
            return customers
            
        except Exception as e:
            logger.error(f"Error fetching Stripe customers: {e}")
            return []
    
    def get_calendar_events(self, start_date, end_date):
        """Fetch calendar events within date range"""
        logger.info(f"Fetching calendar events from {start_date} to {end_date}")
        
        try:
            events_result = self.calendar_service.events().list(
                calendarId='primary',
                timeMin=start_date.isoformat() + 'Z',
                timeMax=end_date.isoformat() + 'Z',
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            logger.info(f"Found {len(events)} calendar events")
            return events
            
        except HttpError as e:
            logger.error(f"Error fetching calendar events: {e}")
            return []
    
    def calculate_meeting_duration(self, start_time, end_time):
        """Calculate meeting duration in hours"""
        try:
            start = parser.parse(start_time)
            end = parser.parse(end_time)
            duration = end - start
            return round(duration.total_seconds() / 3600, 2)  # Convert to hours
        except:
            return 1.0  # Default to 1 hour if calculation fails
    
    def find_customers_with_meetings(self, customers, events):
        """Find customers who had meetings and return meeting details with invoice status"""
        customers_with_meetings = {}
        
        # Create a mapping of email to customer
        customer_by_email = {customer['email']: customer for customer in customers}
        
        for event in events:
            # Extract meeting details
            start_time = event.get('start', {}).get('dateTime', event.get('start', {}).get('date'))
            end_time = event.get('end', {}).get('dateTime', event.get('end', {}).get('date'))
            summary = event.get('summary', 'Meeting')
            
            if not start_time or not end_time:
                continue
            
            # Calculate duration
            duration = self.calculate_meeting_duration(start_time, end_time)
            
            # Format date for display
            try:
                meeting_date = parser.parse(start_time).strftime('%Y-%m-%d')
                meeting_time = parser.parse(start_time).strftime('%I:%M %p')
            except:
                meeting_date = start_time[:10] if len(start_time) >= 10 else start_time
                meeting_time = "Unknown time"
            
            # Check all attendees and organizer
            participant_emails = set()
            
            # Check attendees
            attendees = event.get('attendees', [])
            for attendee in attendees:
                if attendee.get('email'):
                    participant_emails.add(attendee['email'].lower())
            
            # Check organizer
            organizer = event.get('organizer', {})
            if organizer.get('email'):
                participant_emails.add(organizer['email'].lower())
            
            # Find matching customers
            for email in participant_emails:
                if email in customer_by_email:
                    customer = customer_by_email[email]
                    customer_id = customer['id']
                    
                    # Generate unique meeting ID
                    meeting_id = self.generate_meeting_id(email, start_time, summary)
                    
                    # Check invoice status
                    invoice_status = self.check_meeting_invoice_status(customer_id, meeting_id)
                    
                    if customer_id not in customers_with_meetings:
                        customers_with_meetings[customer_id] = {
                            'customer': customer,
                            'meetings': []
                        }
                    
                    # Add meeting details
                    meeting_info = {
                        'id': meeting_id,
                        'summary': summary,
                        'date': meeting_date,
                        'time': meeting_time,
                        'duration': duration,
                        'start_time': start_time,
                        'end_time': end_time,
                        'invoice_status': invoice_status,
                        'selected': invoice_status == 'not_invoiced',  # Default selection
                        'synopsis': ''  # Will be filled in during interactive session
                    }
                    customers_with_meetings[customer_id]['meetings'].append(meeting_info)
        
        # Log results
        for customer_id, data in customers_with_meetings.items():
            customer = data['customer']
            meeting_count = len(data['meetings'])
            logger.info(f"Found {meeting_count} meeting(s) for customer: {customer['name']} ({customer['email']})")
        
        logger.info(f"Total customers with recent meetings: {len(customers_with_meetings)}")
        return customers_with_meetings
    
    def display_meetings_interactive(self, customers_with_meetings, default_hourly_rate):
        """Interactive session to select meetings and enter synopses"""
        print("\n" + "="*80)
        print("CUSTOMER MEETINGS - INVOICE SELECTION")
        print("="*80)
        
        # Display all meetings with status
        meeting_index = 0
        meeting_map = {}  # Map index to (customer_id, meeting_index)
        
        for customer_id, data in customers_with_meetings.items():
            customer = data['customer']
            hourly_rate = self.get_customer_hourly_rate(customer, default_hourly_rate)
            
            print(f"\n📧 {customer['name']} ({customer['email']}) - ${hourly_rate}/hour")
            print("-" * 60)
            
            for i, meeting in enumerate(data['meetings']):
                meeting_index += 1
                meeting_map[meeting_index] = (customer_id, i)
                
                # Status symbols
                status_symbol = {
                    'not_invoiced': '⭕',
                    'drafted': '📄',
                    'sent': '✅'
                }[meeting['invoice_status']]
                
                status_text = {
                    'not_invoiced': 'Not invoiced',
                    'drafted': 'Draft created',
                    'sent': 'Invoice sent'
                }[meeting['invoice_status']]
                
                selected_symbol = '[✓]' if meeting['selected'] else '[ ]'
                amount = meeting['duration'] * hourly_rate
                
                print(f"{meeting_index:2}. {selected_symbol} {status_symbol} {meeting['summary']}")
                print(f"    📅 {meeting['date']} at {meeting['time']} ({meeting['duration']}h) - ${amount:.2f}")
                print(f"    📊 Status: {status_text}")
                print()
        
        # Interactive selection
        print("\nCommands:")
        print("  [number]     - Toggle selection for meeting")
        print("  'all'        - Select all uninvoiced meetings")  
        print("  'none'       - Deselect all meetings")
        print("  'continue'   - Continue to synopsis entry")
        print("  'quit'       - Exit program")
        
        while True:
            command = input("\nEnter command: ").strip().lower()
            
            if command == 'quit':
                print("Exiting...")
                exit(0)
            elif command == 'continue':
                break
            elif command == 'all':
                for customer_id, data in customers_with_meetings.items():
                    for meeting in data['meetings']:
                        if meeting['invoice_status'] == 'not_invoiced':
                            meeting['selected'] = True
                print("✓ Selected all uninvoiced meetings")
            elif command == 'none':
                for customer_id, data in customers_with_meetings.items():
                    for meeting in data['meetings']:
                        meeting['selected'] = False
                print("✓ Deselected all meetings")
            elif command.isdigit():
                meeting_num = int(command)
                if meeting_num in meeting_map:
                    customer_id, meeting_idx = meeting_map[meeting_num]
                    meeting = customers_with_meetings[customer_id]['meetings'][meeting_idx]
                    
                    if meeting['invoice_status'] != 'not_invoiced':
                        print(f"❌ Cannot select meeting #{meeting_num} - already invoiced")
                    else:
                        meeting['selected'] = not meeting['selected']
                        action = "Selected" if meeting['selected'] else "Deselected"
                        print(f"✓ {action} meeting #{meeting_num}")
                else:
                    print(f"❌ Invalid meeting number: {meeting_num}")
            else:
                print("❌ Invalid command")
        
        return self.get_synopsis_for_selected_meetings(customers_with_meetings)
    
    def get_synopsis_for_selected_meetings(self, customers_with_meetings):
        """Get synopsis for each selected meeting"""
        print("\n" + "="*80)
        print("MEETING SYNOPSIS ENTRY")
        print("="*80)
        print("Enter a brief synopsis for each selected meeting.")
        print("This will be included in the invoice line item description.")
        print("Press Enter for default synopsis based on meeting title.")
        
        for customer_id, data in customers_with_meetings.items():
            customer = data['customer']
            selected_meetings = [m for m in data['meetings'] if m['selected']]
            
            if not selected_meetings:
                continue
                
            print(f"\n📧 {customer['name']} ({customer['email']})")
            print("-" * 60)
            
            for meeting in selected_meetings:
                print(f"\n📅 {meeting['summary']} - {meeting['date']} at {meeting['time']}")
                print(f"   Duration: {meeting['duration']}h")
                
                default_synopsis = meeting['summary']
                synopsis = input(f"Synopsis [{default_synopsis}]: ").strip()
                
                if not synopsis:
                    synopsis = default_synopsis
                
                meeting['synopsis'] = synopsis
                print(f"✓ Synopsis saved: {synopsis}")
        
        return customers_with_meetings
    
    def show_invoice_confirmation(self, customers_with_meetings, default_hourly_rate):
        """Show confirmation of invoices to be created"""
        print("\n" + "="*80)
        print("INVOICE CONFIRMATION")
        print("="*80)
        
        total_amount = 0
        total_meetings = 0
        
        for customer_id, data in customers_with_meetings.items():
            customer = data['customer']
            selected_meetings = [m for m in data['meetings'] if m['selected']]
            
            if not selected_meetings:
                continue
            
            hourly_rate = self.get_customer_hourly_rate(customer, default_hourly_rate)
            customer_total = sum(m['duration'] * hourly_rate for m in selected_meetings)
            customer_hours = sum(m['duration'] for m in selected_meetings)
            
            print(f"\n📧 {customer['name']} ({customer['email']})")
            print(f"   Hourly Rate: ${hourly_rate}/hour")
            print(f"   Total: {len(selected_meetings)} meetings, {customer_hours}h, ${customer_total:.2f}")
            print("   " + "-" * 50)
            
            for meeting in selected_meetings:
                amount = meeting['duration'] * hourly_rate
                print(f"   • {meeting['synopsis']}")
                print(f"     {meeting['date']} at {meeting['time']} ({meeting['duration']}h) - ${amount:.2f}")
            
            total_amount += customer_total
            total_meetings += len(selected_meetings)
        
        print(f"\n📊 SUMMARY:")
        print(f"   Total Meetings: {total_meetings}")
        print(f"   Total Amount: ${total_amount:.2f}")
        
        while True:
            confirm = input(f"\nCreate {total_meetings} draft invoices? (y/n): ").strip().lower()
            if confirm in ['y', 'yes']:
                return True
            elif confirm in ['n', 'no']:
                print("❌ Invoice creation cancelled")
                return False
            else:
                print("Please enter 'y' or 'n'")
    
    def create_draft_invoice(self, customer, meetings, hourly_rate):
        """Create a draft invoice for a customer with meetings as line items"""
        try:
            # Create the invoice
            invoice_data = {
                'customer': customer['id'],
                'auto_advance': False,  # Keep as draft
                'collection_method': 'send_invoice',
                'days_until_due': 30,
                'description': f"Consultation services for {len(meetings)} meeting(s) @ ${hourly_rate}/hour"
            }
            
            invoice = stripe.Invoice.create(**invoice_data)
            
            # Add line item for each meeting
            total_amount = 0
            for meeting in meetings:
                # Calculate amount based on duration and customer's hourly rate
                amount = meeting['duration'] * hourly_rate
                total_amount += amount
                
                # Create description with meeting ID and synopsis
                description = f"{meeting['synopsis']} - {meeting['date']} at {meeting['time']} ({meeting['duration']}h @ ${hourly_rate}/h) [ID:{meeting['id']}]"
                
                stripe.InvoiceItem.create(
                    customer=customer['id'],
                    invoice=invoice.id,
                    amount=int(amount * 100),  # Convert to cents
                    currency='usd',
                    description=description
                )
                
                logger.info(f"Added line item: {meeting['synopsis']} - ${amount:.2f}")
            
            logger.info(f"Created draft invoice {invoice.id} for {customer['name']} - Total: ${total_amount:.2f}")
            return invoice
            
        except Exception as e:
            logger.error(f"Error creating invoice for {customer['name']}: {e}")
            return None
    
    def run_automation(self, default_hourly_rate=250.00):
        """
        Run the complete automation process with interactive selection
        
        Args:
            default_hourly_rate: Default hourly rate for customers without a specific rate set
        """
        logger.info("Starting invoice automation...")
        
        # Step 1: Get Stripe customers
        customers = self.get_stripe_customers()
        if not customers:
            logger.error("No customers found. Exiting.")
            return
        
        # Step 2: Get calendar events from the last X days
        end_date = datetime.now()
        start_date = end_date - timedelta(days=self.days_back)
        
        events = self.get_calendar_events(start_date, end_date)
        if not events:
            logger.info("No calendar events found in the specified period.")
            return
        
        # Step 3: Find customers who had meetings and get meeting details with invoice status
        customers_with_meetings = self.find_customers_with_meetings(customers, events)
        
        if not customers_with_meetings:
            logger.info("No customers with recent meetings found.")
            return
        
        # Step 4: Interactive meeting selection and synopsis entry
        customers_with_meetings = self.display_meetings_interactive(customers_with_meetings, default_hourly_rate)
        
        # Step 5: Show confirmation and create invoices
        if not self.show_invoice_confirmation(customers_with_meetings, default_hourly_rate):
            return
        
        # Step 6: Create draft invoices for selected meetings
        created_invoices = []
        
        for customer_id, data in customers_with_meetings.items():
            customer = data['customer']
            selected_meetings = [m for m in data['meetings'] if m['selected']]
            
            if not selected_meetings:
                continue
            
            # Get customer-specific hourly rate
            customer_hourly_rate = self.get_customer_hourly_rate(customer, default_hourly_rate)
            
            invoice = self.create_draft_invoice(customer, selected_meetings, customer_hourly_rate)
            if invoice:
                created_invoices.append(invoice)
        
        print(f"\n✅ SUCCESS: Created {len(created_invoices)} draft invoices!")
        print("You can review and send them from your Stripe dashboard.")
        
        return created_invoices

def main():
    """Main function to run the automation"""
    
    # Load environment variables from .env file
    load_dotenv()
    
    # Configuration - loads from environment variables with defaults
    STRIPE_API_KEY = os.getenv('STRIPE_SECRET_KEY')
    DAYS_BACK = int(os.getenv('DAYS_BACK', '7'))  # Default to 7 days
    DEFAULT_HOURLY_RATE = float(os.getenv('DEFAULT_HOURLY_RATE', '250.00'))  # Default to $250/hour
    
    if not STRIPE_API_KEY:
        logger.error("Please set STRIPE_SECRET_KEY environment variable in your .env file")
        logger.error("Copy config.env.template to .env and fill in your values")
        return
    
    print("🚀 Stripe Customer Meeting Invoice Automation")
    print(f"📅 Checking meetings from the last {DAYS_BACK} days...")
    print(f"💰 Default hourly rate: ${DEFAULT_HOURLY_RATE}/hour")
    print()
    
    # Initialize the automation
    invoicer = StripeCalendarInvoicer(
        stripe_api_key=STRIPE_API_KEY,
        days_back=DAYS_BACK
    )
    
    # OPTIONAL: Set customer-specific hourly rates (uncomment and modify as needed)
    # invoicer.set_customer_hourly_rate("cus_ABC123", 200.00)  # Premium client
    # invoicer.set_customer_hourly_rate("cus_DEF456", 125.00)  # Standard client
    # invoicer.set_customer_hourly_rate("cus_GHI789", 300.00)  # Enterprise client
    
    # Run the automation with interactive interface
    invoicer.run_automation(default_hourly_rate=DEFAULT_HOURLY_RATE)

if __name__ == "__main__":
    main()