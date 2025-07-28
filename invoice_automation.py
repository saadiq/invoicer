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
import argparse
import re
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
        if not self.calendar_service:
            raise Exception("Failed to initialize Google Calendar service. Please check your credentials and try again.")
    
    def _get_calendar_service(self):
        """Authenticate and return Google Calendar service"""
        creds = None
        
        # Load existing token
        if os.path.exists(self.token_file):
            try:
                creds = Credentials.from_authorized_user_file(self.token_file, self.calendar_scopes)
            except Exception as e:
                logger.warning(f"Error loading existing token: {e}")
                creds = None
        
        # If no valid credentials, get new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    logger.error(f"Token refresh failed: {e}")
                    print(f"\n❌ Google Calendar token has expired and cannot be refreshed.")
                    print(f"This usually happens when the token has been expired for too long.")
                    print(f"Current token file: {self.token_file}")
                    
                    while True:
                        choice = input("\nWould you like to remove the expired token and re-authenticate? (y/n): ").strip().lower()
                        if choice in ['y', 'yes']:
                            try:
                                os.remove(self.token_file)
                                print(f"✅ Removed expired token file: {self.token_file}")
                                print("🔄 Starting fresh authentication...")
                                creds = None
                                break
                            except Exception as remove_error:
                                logger.error(f"Error removing token file: {remove_error}")
                                print(f"❌ Could not remove token file. Please manually delete: {self.token_file}")
                                return None
                        elif choice in ['n', 'no']:
                            print("❌ Authentication cancelled. Cannot proceed without valid credentials.")
                            return None
                        else:
                            print("Please enter 'y' or 'n'")
            
            # If we still don't have valid credentials, initiate fresh authentication
            if not creds or not creds.valid:
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.calendar_credentials_file, self.calendar_scopes)
                    creds = flow.run_local_server(port=0)
                except Exception as e:
                    logger.error(f"Authentication failed: {e}")
                    print(f"\n❌ Google Calendar authentication failed.")
                    print(f"Please ensure your credentials.json file is valid and try again.")
                    return None
            
            # Save credentials for next run
            try:
                with open(self.token_file, 'w') as token:
                    token.write(creds.to_json())
                logger.info(f"✅ Saved new authentication token to: {self.token_file}")
            except Exception as e:
                logger.error(f"Error saving token file: {e}")
                print(f"❌ Could not save authentication token. You may need to re-authenticate next time.")
        
        try:
            return build('calendar', 'v3', credentials=creds)
        except Exception as e:
            logger.error(f"Error building calendar service: {e}")
            print(f"❌ Failed to initialize Google Calendar service.")
            return None
    
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
            # Check line items for this meeting ID - line items are in the lines property
            if hasattr(invoice, 'lines') and invoice.lines:
                for item in invoice.lines.data:
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
    
    def parse_time_input(self, time_str):
        """Parse various time formats into datetime object"""
        if not time_str or time_str.strip() == "":
            return None
            
        time_str = time_str.strip()
        
        # Try different time formats
        formats = [
            "%I:%M %p",      # 2:30 PM
            "%I:%M%p",       # 2:30PM
            "%H:%M",         # 14:30
            "%I %p",         # 2 PM
            "%I%p",          # 2PM
            "%H"             # 14
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(time_str, fmt).time()
            except ValueError:
                continue
        
        raise ValueError(f"Unable to parse time: {time_str}")
    
    def parse_duration_input(self, duration_str):
        """Parse duration input into hours (float)"""
        if not duration_str or duration_str.strip() == "":
            return None
            
        duration_str = duration_str.strip().lower()
        
        # Remove common suffixes (order matters - longer patterns first)
        duration_str = duration_str.replace('hours', '').replace('hour', '').replace('hr', '').replace('h', '').strip()
        
        try:
            # Handle formats like "1.5", "2", "0.5"
            duration = float(duration_str)
            if duration <= 0 or duration > 24:
                raise ValueError("Duration must be between 0 and 24 hours")
            return duration
        except ValueError as e:
            # Re-raise our specific error messages
            if "Duration must be between" in str(e):
                raise
            # Otherwise it's a parsing error
            raise ValueError(f"Unable to parse duration: {duration_str}")
    
    def validate_hourly_rate(self, rate_str):
        """Validate and parse hourly rate input"""
        if not rate_str or rate_str.strip() == "":
            return None
            
        rate_str = rate_str.strip().replace('$', '').replace(',', '')
        
        try:
            rate = float(rate_str)
            if rate <= 0 or rate > 10000:
                raise ValueError("Rate must be between $0 and $10,000")
            return rate
        except ValueError as e:
            # Re-raise our specific error messages
            if "Rate must be between" in str(e):
                raise
            # Otherwise it's a parsing error
            raise ValueError(f"Unable to parse rate: {rate_str}")
    
    def extract_emails_from_text(self, text):
        """Extract email addresses from text using regex"""
        if not text:
            return set()
        
        # Email regex pattern
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text, re.IGNORECASE)
        
        # Return lowercase set of unique emails
        return set(email.lower() for email in emails)
    
    def find_customer_mentions_in_text(self, text, customers):
        """Find customer names mentioned in text along with their emails"""
        if not text:
            return set()
        
        found_emails = set()
        text_lower = text.lower()
        
        # Check for each customer's name and email in the text
        for customer in customers:
            customer_name = customer.get('name', '').lower()
            customer_email = customer.get('email', '').lower()
            
            # Skip if no name
            if not customer_name or customer_name == 'unknown':
                continue
                
            # Check if both name and email appear close to each other
            # Look for patterns like "Name email@domain.com" or "email@domain.com (Name)"
            if customer_name in text_lower and customer_email in text_lower:
                # Simple proximity check - if both exist in text, consider it a match
                name_pos = text_lower.find(customer_name)
                email_pos = text_lower.find(customer_email)
                
                # If name and email are within 100 characters of each other
                if abs(name_pos - email_pos) < 100:
                    found_emails.add(customer_email)
        
        return found_emails
    
    def search_customers(self, customers, query):
        """Search customers by name or email
        
        Args:
            customers: List of customer dictionaries
            query: Search query string
            
        Returns:
            List of matching customers
        """
        if not query:
            return []
        
        query_lower = query.lower()
        matches = []
        
        for customer in customers:
            customer_email = customer.get('email', '').lower()
            customer_name = customer.get('name', '').lower()
            
            if query_lower in customer_email or query_lower in customer_name:
                matches.append(customer)
        
        return matches
    
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
    
    def find_customers_with_meetings(self, customers, events, include_all_meetings=False):
        """Find customers who had meetings and return meeting details with invoice status
        
        Args:
            customers: List of Stripe customers
            events: List of calendar events
            include_all_meetings: If True, also return unassociated meetings
            
        Returns:
            Tuple of (customers_with_meetings, unassociated_meetings)
        """
        customers_with_meetings = {}
        unassociated_meetings = []
        
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
            detection_sources = {}  # Track where each email was found
            
            # Check attendees
            attendees = event.get('attendees', [])
            for attendee in attendees:
                if attendee.get('email'):
                    email = attendee['email'].lower()
                    participant_emails.add(email)
                    detection_sources[email] = 'attendee'
            
            # Check organizer
            organizer = event.get('organizer', {})
            if organizer.get('email'):
                email = organizer['email'].lower()
                participant_emails.add(email)
                detection_sources[email] = 'organizer'
            
            # Check description for customer emails
            description = event.get('description', '')
            if description:
                # Extract all emails from description
                description_emails = self.extract_emails_from_text(description)
                
                # Also check for customer name mentions
                name_mention_emails = self.find_customer_mentions_in_text(description, customers)
                
                # Add all found emails from description
                for email in description_emails.union(name_mention_emails):
                    if email not in participant_emails:  # Only add if not already found
                        participant_emails.add(email)
                        detection_sources[email] = 'description'
            
            # Find matching customers
            customer_found = False
            for email in participant_emails:
                if email in customer_by_email:
                    customer_found = True
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
                        'synopsis': '',  # Will be filled in during interactive session
                        # New fields for override functionality
                        'edited_start_time': None,
                        'edited_duration': None,
                        'custom_rate': None,
                        'is_edited': False,
                        'detection_source': detection_sources.get(email, 'unknown')
                    }
                    customers_with_meetings[customer_id]['meetings'].append(meeting_info)
            
            # If no customer found and include_all_meetings is True, add to unassociated list
            if not customer_found and include_all_meetings:
                # Generate unique ID for unassociated meeting
                meeting_id = self.generate_meeting_id('unassociated', start_time, summary)
                
                unassociated_meeting = {
                    'id': meeting_id,
                    'summary': summary,
                    'date': meeting_date,
                    'time': meeting_time,
                    'duration': duration,
                    'start_time': start_time,
                    'end_time': end_time,
                    'attendees': list(participant_emails),
                    'description': description[:200] if description else '',  # Truncate long descriptions
                    'selected': False,
                    'synopsis': '',
                    'assigned_customer': None,  # Will be set during assignment
                    'is_manually_assigned': False
                }
                unassociated_meetings.append(unassociated_meeting)
        
        # Log results
        for customer_id, data in customers_with_meetings.items():
            customer = data['customer']
            meeting_count = len(data['meetings'])
            logger.info(f"Found {meeting_count} meeting(s) for customer: {customer['name']} ({customer['email']})")
        
        logger.info(f"Total customers with recent meetings: {len(customers_with_meetings)}")
        
        if include_all_meetings:
            logger.info(f"Total unassociated meetings: {len(unassociated_meetings)}")
        
        return customers_with_meetings, unassociated_meetings
    
    def edit_meeting_details(self, meeting, customer_data):
        """Interactive function to edit meeting start time and duration"""
        print(f"\n📝 EDITING MEETING: {meeting['summary']}")
        print(f"📅 Original: {meeting['date']} at {meeting['time']} ({meeting['duration']}h)")
        
        if meeting['is_edited']:
            try:
                current_time = meeting['edited_start_time'].strftime("%I:%M %p") if meeting['edited_start_time'] else meeting['time']
            except (AttributeError, ValueError):
                current_time = meeting['time']
            current_duration = meeting['edited_duration'] if meeting['edited_duration'] else meeting['duration']
            print(f"📅 Current: {meeting['date']} at {current_time} ({current_duration}h)")
        
        print("\nEnter new values (press Enter to keep current):")
        
        # Edit start time
        while True:
            try:
                try:
                    current_time_display = meeting['edited_start_time'].strftime("%I:%M %p") if meeting['edited_start_time'] else meeting['time']
                except (AttributeError, ValueError):
                    current_time_display = meeting['time']
                time_input = input(f"Start time [{current_time_display}]: ").strip()
                
                if not time_input:
                    # Keep current time
                    break
                elif time_input.lower() == 'original':
                    # Reset to original
                    meeting['edited_start_time'] = None
                    break
                else:
                    # Parse new time
                    parsed_time = self.parse_time_input(time_input)
                    meeting['edited_start_time'] = parsed_time
                    break
                    
            except ValueError as e:
                print(f"❌ {e}")
                print("Examples: '2:30 PM', '14:30', '2 PM', or 'original' to reset")
        
        # Edit duration
        while True:
            try:
                current_duration = meeting['edited_duration'] if meeting['edited_duration'] else meeting['duration']
                duration_input = input(f"Duration in hours [{current_duration}]: ").strip()
                
                if not duration_input:
                    # Keep current duration
                    break
                elif duration_input.lower() == 'original':
                    # Reset to original
                    meeting['edited_duration'] = None
                    break
                else:
                    # Parse new duration
                    parsed_duration = self.parse_duration_input(duration_input)
                    meeting['edited_duration'] = parsed_duration
                    break
                    
            except ValueError as e:
                print(f"❌ {e}")
                print("Examples: '1.5', '2', '0.5', or 'original' to reset")
        
        # Update is_edited flag
        meeting['is_edited'] = (meeting['edited_start_time'] is not None or 
                               meeting['edited_duration'] is not None)
        
        # Show final result
        try:
            display_time = meeting['edited_start_time'].strftime("%I:%M %p") if meeting['edited_start_time'] else meeting['time']
        except (AttributeError, ValueError):
            display_time = meeting['time']
        display_duration = meeting['edited_duration'] if meeting['edited_duration'] else meeting['duration']
        
        print(f"\n✅ Meeting updated:")
        print(f"📅 {meeting['date']} at {display_time} ({display_duration}h)")
        if meeting['is_edited']:
            print("✏️ This meeting has been edited")
        
        return True
    
    def display_meetings_interactive(self, customers_with_meetings, default_hourly_rate, unassociated_meetings=None, all_customers=None):
        """Interactive session to select meetings and enter synopses
        
        Args:
            customers_with_meetings: Dict of customers with their meetings
            default_hourly_rate: Default hourly rate
            unassociated_meetings: List of meetings not associated with any customer
            all_customers: List of all customers (for assignment)
        """
        if unassociated_meetings is None:
            unassociated_meetings = []
        
        def display_meeting_list():
            """Helper function to display the current meeting list with selection status"""
            print("\n" + "="*80)
            print("CUSTOMER MEETINGS - INVOICE SELECTION")
            print("="*80)
            
            # Display all meetings with status
            meeting_index = 0
            meeting_map = {}  # Map index to (customer_id, meeting_index)
            unassociated_map = {}  # Map Ux index to unassociated meeting index
            
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
                    
                    # Use edited values if available
                    display_duration = meeting['edited_duration'] if meeting['edited_duration'] is not None else meeting['duration']
                    try:
                        display_time = meeting['edited_start_time'].strftime("%I:%M %p") if meeting['edited_start_time'] else meeting['time']
                    except (AttributeError, ValueError):
                        display_time = meeting['time']  # Fallback to original time
                    
                    # Use custom rate if available
                    rate_to_use = meeting['custom_rate'] if meeting['custom_rate'] is not None else hourly_rate
                    amount = display_duration * rate_to_use
                    
                    # Build meeting title with indicators
                    meeting_title = f"{meeting['summary']}"
                    if meeting['is_edited']:
                        meeting_title += " ✏️"
                    if meeting['custom_rate'] is not None:
                        meeting_title += f" 💰${meeting['custom_rate']}/h"
                    if meeting.get('detection_source') == 'description':
                        meeting_title += " 📝"
                    if meeting.get('is_manually_assigned'):
                        meeting_title += " 🔗"
                    
                    print(f"{meeting_index:2}. {selected_symbol} {status_symbol} {meeting_title}")
                    print(f"    📅 {meeting['date']} at {display_time} ({display_duration}h) - ${amount:.2f}")
                    
                    # Show original values if meeting was edited
                    if meeting['is_edited']:
                        print(f"    📅 Original: {meeting['date']} at {meeting['time']} ({meeting['duration']}h)")
                    
                    print(f"    📊 Status: {status_text}")
                    print()
            
            # Display unassociated meetings if any
            if unassociated_meetings:
                print(f"\n🔍 UNASSOCIATED MEETINGS ({len(unassociated_meetings)} found)")
                print("-" * 60)
                
                for i, meeting in enumerate(unassociated_meetings):
                    unassociated_index = f"U{i+1}"
                    unassociated_map[unassociated_index] = i
                    
                    selected_symbol = '[✓]' if meeting['selected'] else '[ ]'
                    
                    # Show assigned customer if any
                    if meeting.get('assigned_customer'):
                        customer = meeting['assigned_customer']
                        print(f"{unassociated_index:3}. {selected_symbol} {meeting['summary']} 🔗")
                        print(f"     📅 {meeting['date']} at {meeting['time']} ({meeting['duration']}h)")
                        print(f"     👤 Assigned to: {customer['name']} ({customer['email']})")
                    else:
                        print(f"{unassociated_index:3}. {selected_symbol} {meeting['summary']}")
                        print(f"     📅 {meeting['date']} at {meeting['time']} ({meeting['duration']}h)")
                        
                        # Show attendees
                        if meeting['attendees']:
                            attendee_list = ', '.join(meeting['attendees'][:3])
                            if len(meeting['attendees']) > 3:
                                attendee_list += f" (+{len(meeting['attendees']) - 3} more)"
                            print(f"     👥 Attendees: {attendee_list}")
                        
                        # Show description preview if available
                        if meeting['description']:
                            desc_preview = meeting['description'][:60] + "..." if len(meeting['description']) > 60 else meeting['description']
                            print(f"     📝 Description: {desc_preview}")
                    
                    print()
            
            return meeting_map, unassociated_map
        
        # Initial display
        meeting_map, unassociated_map = display_meeting_list()
        
        # Interactive selection
        def show_commands():
            """Helper function to display available commands"""
            print("\nCommands:")
            print("  [number]                      - Toggle selection for meeting")
            print("  'all'                         - Select all uninvoiced meetings")  
            print("  'none'                        - Deselect all meetings")
            print("  'edit [number]'               - Edit meeting time/duration")
            print("  'time [number]'               - Quick edit meeting time/duration")
            print("  'rate [number] [amount]'      - Set custom rate for meeting")
            print("  'setrate [email] [amount]'    - Update customer's default rate")
            
            if unassociated_meetings:
                print("\nUnassociated Meeting Commands:")
                print("  'U[number]'                   - Toggle selection for unassociated meeting")
                print("  'assign U[number] [email]'    - Assign meeting to customer")
                print("  'search [query]'              - Search for customer by name or email")
            
            print("\nGeneral Commands:")
            print("  'continue'                    - Continue to synopsis entry")
            print("  'quit'                        - Exit program")
            print("  '?'                           - Show this help message")
            print("\nIcons:")
            print("  ✏️ = Meeting time/duration edited")
            print("  💰 = Custom rate applied")
            print("  📝 = Customer found in meeting description")
            print("  🔗 = Manually assigned to customer")
        
        show_commands()
        
        while True:
            command = input("\nEnter command: ").strip().lower()
            
            if command == 'quit':
                print("Exiting...")
                exit(0)
            elif command == 'continue':
                break
            elif command == '?' or command == 'help':
                show_commands()
            elif command == 'all':
                for customer_id, data in customers_with_meetings.items():
                    for meeting in data['meetings']:
                        if meeting['invoice_status'] == 'not_invoiced':
                            meeting['selected'] = True
                print("✓ Selected all uninvoiced meetings")
                # Refresh display after change
                meeting_map, unassociated_map = display_meeting_list()
            elif command == 'none':
                for customer_id, data in customers_with_meetings.items():
                    for meeting in data['meetings']:
                        meeting['selected'] = False
                print("✓ Deselected all meetings")
                # Refresh display after change
                meeting_map, unassociated_map = display_meeting_list()
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
                        # Refresh display after change
                        meeting_map, unassociated_map = display_meeting_list()
                else:
                    print(f"❌ Invalid meeting number: {meeting_num}")
                    show_commands()
            elif command.startswith('edit '):
                # Edit meeting details (time/duration)
                try:
                    meeting_num = int(command.split()[1])
                    if meeting_num in meeting_map:
                        customer_id, meeting_idx = meeting_map[meeting_num]
                        meeting = customers_with_meetings[customer_id]['meetings'][meeting_idx]
                        customer_data = customers_with_meetings[customer_id]
                        self.edit_meeting_details(meeting, customer_data)
                        # Refresh display after edit
                        meeting_map, unassociated_map = display_meeting_list()
                    else:
                        print(f"❌ Invalid meeting number: {meeting_num}")
                except (ValueError, IndexError):
                    print("❌ Usage: edit [meeting_number]")
                    print("Example: edit 1")
            elif command.startswith('time '):
                # Quick time edit shortcut
                try:
                    meeting_num = int(command.split()[1])
                    if meeting_num in meeting_map:
                        customer_id, meeting_idx = meeting_map[meeting_num]
                        meeting = customers_with_meetings[customer_id]['meetings'][meeting_idx]
                        customer_data = customers_with_meetings[customer_id]
                        self.edit_meeting_details(meeting, customer_data)
                        # Refresh display after edit
                        meeting_map, unassociated_map = display_meeting_list()
                    else:
                        print(f"❌ Invalid meeting number: {meeting_num}")
                except (ValueError, IndexError):
                    print("❌ Usage: time [meeting_number]")
                    print("Example: time 1")
            elif command.startswith('rate '):
                # Set per-meeting rate override
                try:
                    parts = command.split()
                    if len(parts) >= 3:
                        meeting_num = int(parts[1])
                        rate_str = ' '.join(parts[2:])
                        if meeting_num in meeting_map:
                            customer_id, meeting_idx = meeting_map[meeting_num]
                            meeting = customers_with_meetings[customer_id]['meetings'][meeting_idx]
                            try:
                                rate = self.validate_hourly_rate(rate_str)
                                meeting['custom_rate'] = rate
                                print(f"✓ Set custom rate for meeting #{meeting_num}: ${rate}/hour")
                                # Refresh display after change
                                meeting_map, unassociated_map = display_meeting_list()
                            except ValueError as e:
                                print(f"❌ {e}")
                        else:
                            print(f"❌ Invalid meeting number: {meeting_num}")
                    else:
                        print("❌ Usage: rate [meeting_number] [rate]")
                        print("Example: rate 1 250")
                except (ValueError, IndexError):
                    print("❌ Usage: rate [meeting_number] [rate]")
                    print("Example: rate 1 250")
            elif command.startswith('setrate '):
                # Set customer default rate
                try:
                    parts = command.split()
                    if len(parts) >= 3:
                        customer_email = parts[1]
                        rate_str = ' '.join(parts[2:])
                        # Find customer by email
                        customer_found = False
                        for customer_id, data in customers_with_meetings.items():
                            if data['customer']['email'].lower() == customer_email.lower():
                                try:
                                    rate = self.validate_hourly_rate(rate_str)
                                    # Update customer rate in Stripe
                                    if self.set_customer_hourly_rate(customer_id, rate):
                                        print(f"✓ Updated hourly rate for {customer_email}: ${rate}/hour")
                                        # Refresh display after change
                                        meeting_map, unassociated_map = display_meeting_list()
                                    else:
                                        print(f"❌ Failed to update rate for {customer_email}")
                                    customer_found = True
                                    break
                                except ValueError as e:
                                    print(f"❌ {e}")
                                    customer_found = True
                                    break
                        if not customer_found:
                            print(f"❌ Customer not found: {customer_email}")
                    else:
                        print("❌ Usage: setrate [customer_email] [rate]")
                        print("Example: setrate john@company.com 250")
                except (ValueError, IndexError):
                    print("❌ Usage: setrate [customer_email] [rate]")
                    print("Example: setrate john@company.com 250")
            elif command.upper().startswith('U') and command[1:].isdigit():
                # Toggle unassociated meeting selection
                unassoc_idx = command.upper()
                if unassoc_idx in unassociated_map:
                    meeting_idx = unassociated_map[unassoc_idx]
                    meeting = unassociated_meetings[meeting_idx]
                    
                    # Can only select if assigned to a customer
                    if meeting.get('assigned_customer'):
                        meeting['selected'] = not meeting['selected']
                        action = "Selected" if meeting['selected'] else "Deselected"
                        print(f"✓ {action} unassociated meeting {unassoc_idx}")
                    else:
                        print(f"❌ Cannot select meeting {unassoc_idx} - must assign to customer first")
                    
                    # Refresh display after change
                    meeting_map, unassociated_map = display_meeting_list()
                else:
                    print(f"❌ Invalid unassociated meeting number: {unassoc_idx}")
            elif command.startswith('assign '):
                # Assign unassociated meeting to customer
                try:
                    parts = command.split()
                    if len(parts) >= 3:
                        unassoc_idx = parts[1].upper()
                        customer_email = parts[2].lower()
                        
                        if unassoc_idx in unassociated_map:
                            meeting_idx = unassociated_map[unassoc_idx]
                            meeting = unassociated_meetings[meeting_idx]
                            
                            # Find customer by email
                            customer_found = None
                            for cust in all_customers:
                                if cust['email'].lower() == customer_email:
                                    customer_found = cust
                                    break
                            
                            if customer_found:
                                # Assign the meeting
                                meeting['assigned_customer'] = customer_found
                                meeting['is_manually_assigned'] = True
                                
                                # Move meeting to customer's meeting list
                                customer_id = customer_found['id']
                                if customer_id not in customers_with_meetings:
                                    customers_with_meetings[customer_id] = {
                                        'customer': customer_found,
                                        'meetings': []
                                    }
                                
                                # Create proper meeting structure for customer
                                customer_meeting = {
                                    'id': meeting['id'],
                                    'summary': meeting['summary'],
                                    'date': meeting['date'],
                                    'time': meeting['time'],
                                    'duration': meeting['duration'],
                                    'start_time': meeting['start_time'],
                                    'end_time': meeting['end_time'],
                                    'invoice_status': 'not_invoiced',
                                    'selected': True,  # Auto-select assigned meetings
                                    'synopsis': meeting['synopsis'],
                                    'edited_start_time': None,
                                    'edited_duration': None,
                                    'custom_rate': None,
                                    'is_edited': False,
                                    'detection_source': 'manual_assignment',
                                    'is_manually_assigned': True
                                }
                                customers_with_meetings[customer_id]['meetings'].append(customer_meeting)
                                
                                print(f"✅ Assigned '{meeting['summary']}' to {customer_found['name']} ({customer_email})")
                                
                                # Refresh display
                                meeting_map, unassociated_map = display_meeting_list()
                            else:
                                print(f"❌ Customer not found: {customer_email}")
                                print("Use 'search' command to find customers")
                        else:
                            print(f"❌ Invalid unassociated meeting: {unassoc_idx}")
                    else:
                        print("❌ Usage: assign U[number] [customer_email]")
                        print("Example: assign U1 john@company.com")
                except (ValueError, IndexError):
                    print("❌ Usage: assign U[number] [customer_email]")
                    print("Example: assign U1 john@company.com")
            elif command.startswith('search '):
                # Search for customers
                query = command[7:].strip()
                if query and all_customers:
                    matches = self.search_customers(all_customers, query)
                    if matches:
                        print(f"\nFound {len(matches)} customer(s):")
                        for i, customer in enumerate(matches, 1):
                            print(f"{i}. {customer['name']} ({customer['email']})")
                    else:
                        print(f"No customers found matching '{query}'")
                else:
                    print("❌ Usage: search [query]")
                    print("Example: search smith")
            else:
                print(f"❌ Invalid command: '{command}'")
                show_commands()
        
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
            
            # Calculate total using override values
            customer_total = 0
            customer_hours = 0
            for m in selected_meetings:
                duration = m['edited_duration'] if m['edited_duration'] is not None else m['duration']
                rate = m['custom_rate'] if m['custom_rate'] is not None else hourly_rate
                customer_total += duration * rate
                customer_hours += duration
            
            print(f"\n📧 {customer['name']} ({customer['email']})")
            print(f"   Hourly Rate: ${hourly_rate}/hour")
            print(f"   Total: {len(selected_meetings)} meetings, {customer_hours}h, ${customer_total:.2f}")
            print("   " + "-" * 50)
            
            for meeting in selected_meetings:
                duration = meeting['edited_duration'] if meeting['edited_duration'] is not None else meeting['duration']
                rate = meeting['custom_rate'] if meeting['custom_rate'] is not None else hourly_rate
                amount = duration * rate
                try:
                    display_time = meeting['edited_start_time'].strftime("%I:%M %p") if meeting['edited_start_time'] else meeting['time']
                except (AttributeError, ValueError):
                    display_time = meeting['time']  # Fallback to original time
                
                meeting_line = f"   • {meeting['synopsis']}"
                if meeting['is_edited']:
                    meeting_line += " ✏️"
                if meeting['custom_rate'] is not None:
                    meeting_line += f" 💰${meeting['custom_rate']}/h"
                
                print(meeting_line)
                print(f"     {meeting['date']} at {display_time} ({duration}h) - ${amount:.2f}")
            
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
                # Use override values if available
                duration = meeting['edited_duration'] if meeting['edited_duration'] is not None else meeting['duration']
                rate = meeting['custom_rate'] if meeting['custom_rate'] is not None else hourly_rate
                amount = duration * rate
                total_amount += amount
                
                # Use edited time if available
                try:
                    display_time = meeting['edited_start_time'].strftime("%I:%M %p") if meeting['edited_start_time'] else meeting['time']
                except (AttributeError, ValueError):
                    display_time = meeting['time']  # Fallback to original time
                
                # Create description with meeting ID and synopsis
                description = f"{meeting['synopsis']} - {meeting['date']} at {display_time} ({duration}h @ ${rate}/h) [ID:{meeting['id']}]"
                
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
    
    def run_automation(self, default_hourly_rate=250.00, include_all_meetings=False, force_interactive=False):
        """
        Run the complete automation process with interactive selection
        
        Args:
            default_hourly_rate: Default hourly rate for customers without a specific rate set
            include_all_meetings: If True, show all meetings including unassociated ones
            force_interactive: If True, enter interactive mode even if no customer meetings found
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
        customers_with_meetings, unassociated_meetings = self.find_customers_with_meetings(
            customers, events, include_all_meetings
        )
        
        # Check if we should enter interactive mode
        if not customers_with_meetings and not unassociated_meetings and not force_interactive:
            logger.info("No meetings found.")
            return
        elif not customers_with_meetings and not force_interactive:
            logger.info(f"No customers with recent meetings found, but found {len(unassociated_meetings)} unassociated meetings.")
            if not include_all_meetings:
                logger.info("Use --include-all-meetings flag to see unassociated meetings.")
                return
        
        # Step 4: Interactive meeting selection and synopsis entry
        customers_with_meetings = self.display_meetings_interactive(
            customers_with_meetings, 
            default_hourly_rate,
            unassociated_meetings=unassociated_meetings if include_all_meetings else None,
            all_customers=customers
        )
        
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
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Stripe Customer Meeting Invoice Automation')
    parser.add_argument('--days-back', '-d', type=int, 
                        help='Number of days back to check for meetings (overrides environment variable)')
    parser.add_argument('--hourly-rate', '-r', type=float,
                        help='Default hourly rate (overrides environment variable)')
    parser.add_argument('--include-all-meetings', '-a', action='store_true',
                        help='Include all calendar meetings, not just those with known customers')
    parser.add_argument('--interactive', '-i', action='store_true',
                        help='Force interactive mode even if no customer meetings are found')
    
    args = parser.parse_args()
    
    # Load environment variables from .env file
    load_dotenv()
    
    # Configuration - loads from environment variables with defaults, can be overridden by command line
    STRIPE_API_KEY = os.getenv('STRIPE_SECRET_KEY')
    DAYS_BACK = args.days_back if args.days_back is not None else int(os.getenv('DAYS_BACK', '7'))
    DEFAULT_HOURLY_RATE = args.hourly_rate if args.hourly_rate is not None else float(os.getenv('DEFAULT_HOURLY_RATE', '250.00'))
    
    if not STRIPE_API_KEY:
        logger.error("Please set STRIPE_SECRET_KEY environment variable in your .env file")
        logger.error("Copy config.env.template to .env and fill in your values")
        return
    
    print("🚀 Stripe Customer Meeting Invoice Automation")
    print(f"📅 Checking meetings from the last {DAYS_BACK} days...")
    print(f"💰 Default hourly rate: ${DEFAULT_HOURLY_RATE}/hour")
    print()
    
    # Initialize the automation
    try:
        invoicer = StripeCalendarInvoicer(
            stripe_api_key=STRIPE_API_KEY,
            days_back=DAYS_BACK
        )
    except Exception as e:
        logger.error(f"Failed to initialize automation: {e}")
        print(f"\n❌ Initialization failed: {e}")
        return
    
    # OPTIONAL: Set customer-specific hourly rates (uncomment and modify as needed)
    # invoicer.set_customer_hourly_rate("cus_ABC123", 200.00)  # Premium client
    # invoicer.set_customer_hourly_rate("cus_DEF456", 125.00)  # Standard client
    # invoicer.set_customer_hourly_rate("cus_GHI789", 300.00)  # Enterprise client
    
    # Run the automation with interactive interface
    invoicer.run_automation(
        default_hourly_rate=DEFAULT_HOURLY_RATE,
        include_all_meetings=args.include_all_meetings,
        force_interactive=args.interactive
    )

if __name__ == "__main__":
    main()