# Environment Variables Documentation

All automation scripts load configuration from `dashboard/.env`.

## Required Environment Variables

### Email (Brevo SMTP)
- **SMTP_SERVER**: SMTP server hostname (e.g., `smtp-relay.brevo.com`)
- **SMTP_PORT**: SMTP port (default: `587`)
- **SMTP_USER**: SMTP username/login for authentication
- **SMTP_PASSWORD**: SMTP password for authentication
- **SENDER_EMAIL**: Email address to send from (e.g., `team@nullrecords.com`)

### Google Analytics (GA4)
- **GOOGLE_APPLICATION_CREDENTIALS**: Absolute path to the GA4 service account JSON file (e.g., `/path/to/dashboard/nullrecords-ga4-credentials.json`)
- **GA_PROPERTY_ID**: GA4 property ID (e.g., `308964282`)
- **GA_MEASUREMENT_ID**: GA4 measurement ID (e.g., `G-2WVCJM4NKR`)

## Optional Environment Variables

### Notification Emails
- **BCC_EMAIL**: BCC recipient on outreach emails
- **CC_EMAIL**: CC recipient on outreach emails
- **DAILY_REPORT_EMAIL**: Recipient for daily report emails
- **NOTIFICATION_EMAIL**: Recipient for system notifications

### Outreach Settings
- **MAX_DAILY_OUTREACH**: Daily outreach email limit (default: `10`)
- **RATE_LIMIT_DELAY**: Seconds between outreach emails (default: `2`)

### YouTube
- **YOUTUBE_CHANNEL_ID**: YouTube channel ID for content tracking

### Website (defaults used if unset)
- **WEBSITE_BASE_URL**: Base URL (default: `https://nullrecords.com`)
- **CONTACT_EMAIL**: Contact email (default: `team@nullrecords.com`)

## .env Template

```bash
# --- Required: Email (Brevo SMTP) ---
SMTP_SERVER=smtp-relay.brevo.com
SMTP_PORT=587
SMTP_USER=your_smtp_username
SMTP_PASSWORD=your_smtp_password
SENDER_EMAIL=team@nullrecords.com

# --- Required: Google Analytics ---
GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/dashboard/nullrecords-ga4-credentials.json
GA_PROPERTY_ID=308964282
GA_MEASUREMENT_ID=G-2WVCJM4NKR

# --- Optional: Notification Emails ---
BCC_EMAIL=admin@example.com
CC_EMAIL=admin@example.com
DAILY_REPORT_EMAIL=reports@example.com
NOTIFICATION_EMAIL=alerts@example.com

# --- Optional: Outreach ---
MAX_DAILY_OUTREACH=10
RATE_LIMIT_DELAY=2

# --- Optional: YouTube ---
YOUTUBE_CHANNEL_ID=UC_your_channel_id
```

## Security Notes

- All scripts use `os.getenv()` — no hardcoded secrets
- The `.env` file is gitignored
- GOOGLE_APPLICATION_CREDENTIALS must be an absolute path to the service account JSON
- File paths exist (for Google credentials)