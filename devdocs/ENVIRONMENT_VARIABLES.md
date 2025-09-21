# Environment Variables Documentation

## Required Environment Variables

### Email Configuration
- **SMTP_SERVER**: SMTP server hostname (e.g., smtp-relay.brevo.com)
- **SMTP_USER**: SMTP username/login for authentication
- **SMTP_PASSWORD**: SMTP password for authentication
- **SENDER_EMAIL**: Email address to send from
- **BCC_EMAIL**: Email address for BCC notifications

## Optional Environment Variables

### Basic Configuration
- **SMTP_PORT**: SMTP port (default: 587)
- **DAILY_REPORT_EMAIL**: Email for daily reports
- **NOTIFICATION_EMAIL**: Email for notifications

### Website Configuration
- **WEBSITE_BASE_URL**: Base URL for the website (default: https://nullrecords.com)
- **CONTACT_EMAIL**: Contact email address (default: team@nullrecords.com)

### Google Services
- **GOOGLE_APPLICATION_CREDENTIALS**: Path to Google service account JSON file
- **GA_PROPERTY_ID**: Google Analytics GA4 property ID
- **GA_VIEW_ID**: Google Analytics view ID (legacy)
- **YOUTUBE_API_KEY**: YouTube Data API key
- **YOUTUBE_CHANNEL_ID**: YouTube channel ID

### Google Sheets
- **GOOGLE_SHEETS_ID**: Google Sheets ID for voting data
- **VOTING_SHEET_NAME**: Name of voting sheet tab (default: Votes)

### Additional Services
- **BREVO_API_KEY**: Brevo API key for detailed metrics
- **MAX_DAILY_OUTREACH**: Daily outreach email limit (default: 10)

## Security Best Practices

### ✅ What's Properly Configured
- All scripts use `os.getenv()` for sensitive data
- No hardcoded passwords, API keys, or secrets
- Website URLs and contact emails use environment variables
- SMTP credentials properly externalized
- Google service credentials path configurable

### 🔧 Environment Variable Usage
Scripts automatically fall back to sensible defaults for optional configuration:
- Website URL defaults to `https://nullrecords.com`
- Contact email defaults to `team@nullrecords.com`
- SMTP port defaults to `587`

### 📝 .env File Format
```bash
# Required
SMTP_SERVER=smtp-relay.brevo.com
SMTP_USER=your_username
SMTP_PASSWORD=your_password
SENDER_EMAIL=your_email@domain.com
BCC_EMAIL=admin@domain.com

# Optional
WEBSITE_BASE_URL=https://your-website.com
CONTACT_EMAIL=contact@your-domain.com
DAILY_REPORT_EMAIL=reports@your-domain.com
GA_PROPERTY_ID=308964282
YOUTUBE_CHANNEL_ID=UC_your_channel_id
```

## Validation

Run the environment validator to check your configuration:
```bash
python3 scripts/validate_env.py
```

This will verify:
- All required variables are set
- Email addresses have valid formats
- SMTP connection works
- File paths exist (for Google credentials)