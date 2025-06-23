# Stripe Customer Meeting Invoice Automation

🚀 **Automate your meeting-based invoicing workflow with Google Calendar and Stripe integration**

This Python script automatically identifies meetings with your Stripe customers, tracks which meetings have already been invoiced, and creates detailed draft invoices with custom synopses for each meeting.

## ✨ Features

- **📅 Calendar Integration**: Automatically fetches meetings from Google Calendar
- **👥 Customer Matching**: Cross-references meeting attendees with your Stripe customer list
- **💰 Flexible Pricing**: Support for different hourly rates per customer (stored in Stripe metadata)
- **🔍 Duplicate Prevention**: Tracks which meetings have already been invoiced to prevent double-billing
- **🎯 Interactive Selection**: Visual interface to select which meetings to invoice
- **📝 Custom Synopses**: Add personalized descriptions for each meeting on the invoice
- **📊 Status Tracking**: Shows if meetings are uninvoiced, drafted, or already sent
- **⏱️ Duration-Based Billing**: Automatically calculates meeting duration and invoice amounts

## 🖥️ Interactive Workflow

### 1. Meeting Overview
```
📧 John Smith (john@company.com) - $200/hour
------------------------------------------------------------
 1. [✓] ⭕ Weekly Strategy Review
    📅 2025-06-15 at 2:00 PM (1.0h) - $200.00
    📊 Status: Not invoiced

 2. [ ] ✅ Project Planning Meeting  
    📅 2025-06-17 at 10:30 AM (1.5h) - $300.00
    📊 Status: Invoice sent
```

**Status Icons:**
- ⭕ **Not invoiced** (auto-selected for billing)
- 📄 **Draft created** (invoice drafted but not sent)
- ✅ **Invoice sent** (already invoiced and sent)

### 2. Meeting Selection
- Toggle individual meetings on/off
- Bulk select all uninvoiced meetings
- Cannot select already-invoiced meetings

### 3. Synopsis Entry
```
📅 Weekly Strategy Review - 2025-06-15 at 2:00 PM
   Duration: 1.0h
Synopsis [Weekly Strategy Review]: Discussed Q3 goals and budget planning
✓ Synopsis saved: Discussed Q3 goals and budget planning
```

### 4. Final Confirmation
Review all selected meetings, rates, and total amounts before creating invoices.

## 🛠️ Installation

### Prerequisites
- Python 3.7+
- Stripe account with API access
- Google account with Calendar API access

### Install Dependencies
```bash
pip install stripe google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client python-dateutil
```

## ⚙️ Setup

### 1. Stripe API Setup
1. Get your Stripe Secret Key from the [Stripe Dashboard](https://dashboard.stripe.com/apikeys)
2. Set environment variable:
   ```bash
   export STRIPE_SECRET_KEY="sk_test_..."
   ```

### 2. Google Calendar API Setup
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable the Google Calendar API
4. Create credentials (OAuth 2.0 Client ID)
5. Download the credentials file as `credentials.json`
6. Place `credentials.json` in your script directory

### 3. Customer Hourly Rates (Optional)
Set different hourly rates for different customers in Stripe:

**Option A: Stripe Dashboard**
1. Go to Customers → Select Customer → Edit
2. Add metadata: `hourly_rate` = `200.00`

**Option B: Programmatically**
```python
# Uncomment and modify in main() function
invoicer.set_customer_hourly_rate("cus_ABC123", 200.00)  # Premium client
invoicer.set_customer_hourly_rate("cus_DEF456", 125.00)  # Standard client
```

## 🚀 Usage

### Basic Usage
```bash
python invoice_automation.py
```

### Configuration Options
Edit the configuration section in `main()`:

```python
STRIPE_API_KEY = os.getenv('STRIPE_SECRET_KEY')
DAYS_BACK = 7  # Look back 7 days for meetings
DEFAULT_HOURLY_RATE = 150.00  # Default rate for customers without specific rate
```

### First Run
1. Google will open a browser window for authentication
2. Grant calendar read permissions
3. Credentials will be saved for future runs

## 📋 How It Works

### Meeting Detection
- Scans Google Calendar for events in the specified date range
- Matches meeting attendees/organizers with Stripe customer emails
- Calculates meeting duration from start/end times

### Invoice Status Tracking
- Generates unique IDs for each meeting (hash of customer + date + title)
- Scans existing Stripe invoices for meeting IDs in line item descriptions
- Prevents duplicate invoicing of the same meeting

### Invoice Creation
Each meeting becomes a separate line item:
```
"Discussed Q3 goals and budget planning - 2025-06-15 at 2:00 PM (1.0h @ $200/h) [ID:a1b2c3d4e5f6]"
```

## 💡 Examples

### Sample Meeting Selection Session
```
Commands:
  [number]     - Toggle selection for meeting
  'all'        - Select all uninvoiced meetings  
  'none'       - Deselect all meetings
  'continue'   - Continue to synopsis entry
  'quit'       - Exit program

Enter command: 1
✓ Selected meeting #1

Enter command: all
✓ Selected all uninvoiced meetings

Enter command: continue
```

### Sample Invoice Output
```
📊 SUMMARY:
   Total Meetings: 3
   Total Amount: $675.00

Create 3 draft invoices? (y/n): y
✅ SUCCESS: Created 3 draft invoices!
```

## 🔧 Troubleshooting

### Common Issues

**"No customers found"**
- Verify your Stripe API key is correct
- Check that customers in Stripe have email addresses

**"No calendar events found"**
- Verify Google Calendar authentication
- Check the `DAYS_BACK` setting
- Ensure you have meetings in the specified date range

**"Error fetching calendar events"**
- Re-authenticate Google Calendar (delete `token.json`)
- Check Google Calendar API is enabled in Google Cloud Console

**Missing customer hourly rates**
- The script will use `DEFAULT_HOURLY_RATE` for customers without metadata
- Set customer-specific rates in Stripe metadata: `hourly_rate` = `200.00`

### File Structure
```
your-project/
├── invoice_automation.py
├── credentials.json          # Google Calendar API credentials
├── token.json               # Auto-generated Google OAuth token
└── README.md
```

## 🎯 Best Practices

1. **Test First**: Run the script in a test environment before production
2. **Review Drafts**: Always review draft invoices in Stripe before sending
3. **Regular Backups**: Keep backups of your `credentials.json` and customer rate data
4. **Rate Management**: Use Stripe metadata for customer-specific rates rather than hardcoding
5. **Meeting Names**: Use descriptive meeting titles in Google Calendar for better synopses

## 🔒 Security Notes

- Never commit `credentials.json` or `token.json` to version control
- Use environment variables for sensitive API keys
- Stripe API keys should be kept secure and rotated regularly
- The script only requires read access to Google Calendar

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📞 Support

If you encounter issues:
1. Check the troubleshooting section above
2. Review Stripe and Google Calendar API documentation
3. Open an issue with detailed error logs

---

**⚡ Happy Invoicing!** This script can save hours of manual invoice creation while ensuring nothing falls through the cracks.

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Environment Configuration

Copy the environment template and configure your settings:

```bash
cp config.env.template .env
```

Edit `.env` file with your actual values:

```env
# Stripe Configuration
STRIPE_SECRET_KEY=sk_test_your_actual_stripe_secret_key_here

# Invoice Settings  
DEFAULT_HOURLY_RATE=150.00
DAYS_BACK=7
```

**Environment Variables:**
- `STRIPE_SECRET_KEY` - Your Stripe secret API key (required)
- `DEFAULT_HOURLY_RATE` - Default hourly rate for customers without specific rates (default: 150.00)
- `DAYS_BACK` - Number of days back to check for meetings (default: 7)

### 3. Google Calendar Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable the Google Calendar API
4. Create credentials (OAuth 2.0 Client ID) for a desktop application
5. Download the credentials JSON file and save it as `credentials.json` in the project directory

### 4. Stripe Customer Setup

Set customer hourly rates in Stripe:
- Go to Stripe Dashboard > Customers > [Customer] > Edit
- Add metadata: key="hourly_rate", value="200.00"
- Or use the `set_customer_hourly_rate()` method in the script

For customers without a specific rate, the `DEFAULT_HOURLY_RATE` will be used.

## Usage

Run the automation:

```bash
python invoice_automation.py
```

The script will:
1. Load your environment variables from `.env`
2. Authenticate with Google Calendar (browser will open on first run)
3. Fetch customers from Stripe
4. Find recent meetings and show interactive selection interface
5. Allow you to enter custom synopses for each meeting
6. Create draft invoices in Stripe

## Example: Setting Customer Rates Programmatically

```python
invoicer = StripeCalendarInvoicer(stripe_api_key="sk_...")
invoicer.set_customer_hourly_rate("cus_ABC123", 200.00)  # $200/hour for premium client
invoicer.set_customer_hourly_rate("cus_DEF456", 125.00)  # $125/hour for standard client
invoicer.set_customer_hourly_rate("cus_GHI789", 300.00)  # $300/hour for enterprise client
```

## Security Notes

- Your `.env` file is automatically ignored by git (included in `.gitignore`)
- Never commit your actual Stripe API keys to version control
- Use test keys during development
- The `credentials.json` file is also gitignored for security