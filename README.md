# Stripe Customer Meeting Invoice Automation

🚀 **Automate your meeting-based invoicing workflow with Google Calendar and Stripe integration**

Transform your consulting workflow by automatically identifying meetings with Stripe customers, tracking invoicing status, and creating detailed draft invoices with custom synopses.

## 📖 Table of Contents

- [Quick Start](#-quick-start)
- [Key Features](#-key-features)
- [Installation](#-installation)
- [Setup Guide](#-setup-guide)
- [Basic Usage](#-basic-usage)
- [Interactive Workflow](#-interactive-workflow)
- [Advanced Features](#-advanced-features)
- [Testing & Development](#-testing--development)
- [Troubleshooting](#-troubleshooting)
- [Security & Best Practices](#-security--best-practices)
- [Contributing](#-contributing)

## ⚡ Quick Start

Get up and running in 5 minutes:

1. **Install dependencies:**
   ```bash
   pip install stripe google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client python-dateutil
   ```

2. **Set your Stripe API key:**
   ```bash
   # Option A: .env file (recommended)
   echo "STRIPE_SECRET_KEY=sk_test_..." > .env
   
   # Option B: Environment variable
   export STRIPE_SECRET_KEY="sk_test_..."
   ```

3. **Get Google Calendar credentials:**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Enable Calendar API → Create OAuth credentials → Download as `credentials.json`

4. **Run the automation:**
   ```bash
   python invoice_automation.py
   ```

That's it! The script will guide you through Google authentication and show your meetings ready for invoicing.

## ✨ Key Features

### 🎯 **Core Automation**
- **Smart Calendar Integration**: Automatically fetches meetings with robust token management
- **Customer Matching**: Cross-references attendees with your Stripe customer list
- **Duplicate Prevention**: Tracks invoiced meetings to prevent double-billing
- **Flexible Pricing**: Different hourly rates per customer (stored in Stripe metadata)

### 🖥️ **Interactive Experience**
- **Visual Meeting Selection**: Clear status indicators (⭕ uninvoiced, 📄 drafted, ✅ sent)
- **Meeting Editing**: Adjust start times and durations if actual differs from scheduled
- **Custom Rate Override**: Set special rates for specific meetings or update customer defaults
- **Personalized Synopses**: Add custom descriptions for each meeting on invoices

### 🔐 **Reliability & Security**
- **Smart Token Management**: Handles Google OAuth expiration with user-friendly prompts
- **Comprehensive Testing**: 66 tests with 75% code coverage
- **Error Recovery**: Graceful handling of API failures and authentication issues

## 🛠️ Installation

### Prerequisites
- Python 3.7+
- Stripe account with API access
- Google account with Calendar API access

### Install Dependencies
```bash
# Option 1: Direct installation
pip install stripe google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client python-dateutil

# Option 2: From requirements file (if available)
pip install -r requirements.txt
```

## ⚙️ Setup Guide

### 1. Stripe API Configuration

**Get your API key:**
1. Visit [Stripe Dashboard → API Keys](https://dashboard.stripe.com/apikeys)
2. Copy your Secret Key (starts with `sk_test_` or `sk_live_`)
3. **Configure environment variables** (choose one method):

   **Option A: .env file (recommended)**
   ```bash
   # Create .env file in project directory
   echo "STRIPE_SECRET_KEY=sk_test_your_actual_key_here" > .env
   echo "DEFAULT_HOURLY_RATE=150.00" >> .env
   echo "DAYS_BACK=7" >> .env
   ```

   **Option B: Shell environment**
   ```bash
   export STRIPE_SECRET_KEY="sk_test_your_actual_key_here"
   export DEFAULT_HOURLY_RATE="150.00"
   export DAYS_BACK="7"
   ```

**Optional: Set up customer hourly rates**
- **Via Stripe Dashboard**: Customers → [Customer] → Edit → Add metadata: `hourly_rate` = `200.00`
- **Programmatically**: Use `invoicer.set_customer_hourly_rate("cus_ABC123", 200.00)` in the script

### 2. Google Calendar API Setup

1. **Enable the API:**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create/select a project → Enable Google Calendar API

2. **Create OAuth credentials:**
   - Go to Credentials → Create → OAuth 2.0 Client ID
   - Choose "Desktop application"
   - Download the JSON file

3. **Install credentials:**
   - Rename downloaded file to `credentials.json`
   - Place in your script directory

### 3. Configuration Options

The script automatically loads configuration from environment variables or a `.env` file:

**Environment Variables:**
- `STRIPE_SECRET_KEY` - Your Stripe secret API key (required)
- `DEFAULT_HOURLY_RATE` - Default hourly rate for customers without specific rates (default: 150.00)
- `DAYS_BACK` - Number of days back to check for meetings (default: 7)

**Using .env file (recommended):**
```env
# .env file in project directory
STRIPE_SECRET_KEY=sk_test_your_actual_key_here
DEFAULT_HOURLY_RATE=150.00
DAYS_BACK=7
```

**Manual configuration in code:**
```python
# Edit these settings in main() function if not using .env
STRIPE_API_KEY = os.getenv('STRIPE_SECRET_KEY')
DAYS_BACK = int(os.getenv('DAYS_BACK', 7))
DEFAULT_HOURLY_RATE = float(os.getenv('DEFAULT_HOURLY_RATE', 150.00))
```

## 🚀 Basic Usage

### First Run
```bash
python invoice_automation.py
```

**What happens:**
1. Google opens browser for Calendar authentication (first time only)
2. Script scans for meetings with your Stripe customers
3. Shows interactive interface for meeting selection
4. Guides you through synopsis entry
5. Creates draft invoices in Stripe

### File Structure After Setup
```
your-project/
├── invoice_automation.py
├── credentials.json          # Google Calendar API credentials
├── token.json               # Auto-generated OAuth token (don't commit!)
├── .env                     # Environment variables (don't commit!)
└── README.md
```

## 🖥️ Interactive Workflow

### 1. Meeting Overview
The script displays meetings organized by customer with clear status indicators:

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

### 2. Interactive Commands

**Selection Commands:**
- `[number]` - Toggle meeting selection
- `all` - Select all uninvoiced meetings  
- `none` - Deselect all meetings
- `continue` - Proceed to synopsis entry

**Editing Commands:**
- `edit [number]` - Edit meeting time and duration
- `time [number]` - Quick shortcut for editing
- `rate [number] [amount]` - Set custom rate for specific meeting
- `setrate [email] [amount]` - Update customer's default hourly rate

**Help Commands:**
- `?` - Show command help
- `quit` - Exit program

### 3. Meeting Editing Example

```
Enter command: edit 1

📝 EDITING MEETING: Weekly Strategy Review
📅 Original: 2025-06-15 at 2:00 PM (1.0h)

Enter new values (press Enter to keep current):
Start time [2:00 PM]: 2:30 PM
Duration in hours [1.0]: 1.5

✅ Meeting updated:
📅 2025-06-15 at 2:30 PM (1.5h)
✏️ This meeting has been edited
```

**Visual Indicators:**
- ✏️ = Meeting time/duration has been edited
- 💰$X/h = Custom rate applied to meeting

### 4. Synopsis Entry & Final Review

After selecting meetings, you'll add custom descriptions:

```
📅 Weekly Strategy Review - 2025-06-15 at 2:30 PM ✏️
   Duration: 1.5h
Synopsis [Weekly Strategy Review]: Discussed Q3 goals and budget planning
✓ Synopsis saved
```

Then review and confirm before creating invoices:

```
📊 SUMMARY:
   Total Meetings: 2
   Total Amount: $475.00
   
   • Weekly Strategy Review ✏️
     2025-06-15 at 2:30 PM (1.5h) - $300.00
   • Project Planning Meeting 💰$250/h
     2025-06-17 at 10:30 AM (1.0h) - $250.00

Create 2 draft invoices? (y/n): y
✅ SUCCESS: Created 2 draft invoices!
```

## 🔧 Advanced Features

### Meeting Detection Algorithm
- Scans Google Calendar events in specified date range
- Matches attendees/organizers with Stripe customer emails
- Calculates duration from start/end times
- Generates unique meeting IDs (hash of customer + date + title)

### Invoice Status Tracking
- Scans existing Stripe invoices for meeting IDs in descriptions
- Prevents duplicate invoicing with persistent tracking
- Each meeting becomes a line item: `"Description - Date at Time (Duration @ Rate) [ID:abc123]"`

### Customer Rate Management
Set rates programmatically:
```python
invoicer = StripeCalendarInvoicer(stripe_api_key="sk_...")
invoicer.set_customer_hourly_rate("cus_ABC123", 200.00)  # Premium client
invoicer.set_customer_hourly_rate("cus_DEF456", 125.00)  # Standard client
```

## 🧪 Testing & Development

The project includes comprehensive testing with **66 tests** achieving **75% code coverage**.

### Running Tests

```bash
# Install test dependencies
pip install -r test_requirements.txt

# Run all tests with coverage
python run_tests.py all --coverage

# Run specific test suites
python run_tests.py unit        # Unit tests for core functions
python run_tests.py integration # Integration tests (Stripe/Google)
python run_tests.py commands    # Interactive command tests
python run_tests.py e2e        # End-to-end workflow tests
```

### Test Coverage Areas
- **Authentication Logic**: Token handling, expiration, refresh failures
- **Display Formatting**: Visual indicators, time formatting, error fallbacks  
- **Input Validation**: Command parsing, malformed inputs, edge cases
- **Core Business Logic**: Meeting detection, invoice creation, rate management
- **Integration Testing**: Mocked Stripe and Google Calendar API interactions
- **End-to-End Workflows**: Complete user scenarios with error recovery

See [TESTING.md](TESTING.md) for detailed testing documentation.

## 🔧 Troubleshooting

### Authentication Issues

**❌ "Google Calendar token has expired and cannot be refreshed"**
- Happens after ~6 months of token inactivity
- Script prompts to remove expired token automatically
- Choose 'y' to delete `token.json` and re-authenticate
- Or manually delete `token.json` and run script again

**❌ "Failed to initialize Google Calendar service"**
- Check `credentials.json` exists and is valid
- Ensure Calendar API is enabled in Google Cloud Console
- Verify OAuth credentials are for "Desktop application"
- Try downloading fresh credentials from Google Cloud

### Data Issues

**❌ "No customers found"**
- Verify Stripe API key is correct and has read permissions
- Check customers in Stripe have email addresses
- Ensure you're using the right API key (test vs live)

**❌ "No calendar events found"**
- Check `DAYS_BACK` setting (default: 7 days)
- Verify you have meetings in the specified date range
- Ensure meeting attendees match Stripe customer emails

**❌ "Missing customer hourly rates"**
- Script uses `DEFAULT_HOURLY_RATE` for customers without metadata
- Set rates in Stripe: Customer → Edit → Metadata: `hourly_rate` = `200.00`
- Or use `setrate` command during meeting selection

### Technical Issues

**❌ "Error fetching calendar events"**
- Re-authenticate by deleting `token.json`
- Check Google Calendar API quotas in Cloud Console
- Verify internet connection and firewall settings

**❌ "Stripe API errors"**
- Check API key permissions and rate limits
- Verify customer IDs are valid
- Review Stripe Dashboard for additional error details

## 🔒 Security & Best Practices

### Security Guidelines
- **Never commit** `credentials.json` or `token.json` to version control
- **Use environment variables** for Stripe API keys
- **Rotate API keys** regularly and use test keys during development
- **Grant minimal permissions**: Script only needs Calendar read access
- **Review draft invoices** in Stripe before sending to customers

### Recommended Practices
1. **Test First**: Run in test environment before production use
2. **Backup Credentials**: Keep secure backups of `credentials.json`
3. **Descriptive Meetings**: Use clear meeting titles for better synopses
4. **Time Accuracy**: Use edit feature for meetings that ran over/under scheduled time
5. **Rate Management**: Store rates in Stripe metadata rather than hardcoding
6. **Regular Reviews**: Check invoice drafts before sending to customers

### File Security
```bash
# Add to .gitignore
credentials.json
token.json
.env
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Run tests to ensure nothing breaks (`python run_tests.py all`)
4. Commit your changes (`git commit -m 'Add amazing feature'`)
5. Push to the branch (`git push origin feature/amazing-feature`)
6. Open a Pull Request

### Development Setup
```bash
# Install dev dependencies
pip install -r test_requirements.txt

# Run tests before committing
python run_tests.py all --coverage

# Check coverage is maintained
# Target: 75%+ coverage
```

## 📞 Support

If you encounter issues:

1. **Check troubleshooting section** above for common solutions
2. **Review logs** - the script provides detailed error messages
3. **Verify setup** - ensure API keys and credentials are correct
4. **Consult documentation** - [Stripe API](https://stripe.com/docs/api) and [Google Calendar API](https://developers.google.com/calendar)
5. **Open an issue** with detailed error logs and setup information

---

**⚡ Happy Invoicing!** This automation can save hours of manual work while ensuring accurate billing and nothing falls through the cracks.