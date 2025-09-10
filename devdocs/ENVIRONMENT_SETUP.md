# Secure Environment Variables Setup for NullRecords Outreach

## 🔒 Security Implementation

Your SMTP credentials are now secured using environment variables instead of hardcoded values in the source code.

## 📋 Setup Instructions

### 1. Environment Variables Required

```bash
# Required SMTP Configuration
SMTP_USER=your_brevo_username@smtp-brevo.com
SMTP_PASSWORD=your_brevo_api_key
SMTP_SERVER=smtp-relay.brevo.com
SMTP_PORT=587

# Email Configuration
SENDER_EMAIL=team@nullrecords.com
NOTIFICATION_EMAIL=your-email@example.com
```

### 2. Local Development Setup

1. **Copy the example file:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` with your credentials:**
   ```bash
   nano .env
   # Or use your preferred editor
   ```

3. **Install python-dotenv (recommended):**
   ```bash
   pip install python-dotenv
   ```

### 3. Production Deployment

#### Option A: System Environment Variables
```bash
export SMTP_USER="96afc8001@smtp-brevo.com"
export SMTP_PASSWORD="hW0ABk75sbJqwD9K"
export SENDER_EMAIL="team@nullrecords.com"
export NOTIFICATION_EMAIL="team@nullrecords.com"
```

#### Option B: Server .env File
- Upload `.env` file to your server
- Ensure proper file permissions: `chmod 600 .env`
- Never commit `.env` to version control

### 4. Cron Job Updates

Update your cron jobs to load environment variables:

```bash
# Edit crontab
crontab -e

# Add environment loading to daily script
0 10 * * * cd /path/to/project && source .env && python music_outreach.py --interactive
```

## 🛡️ Security Features

✅ **Credentials Removed from Source Code**  
✅ **Environment Variable Support**  
✅ **Flexible SMTP Configuration**  
✅ **Error Handling for Missing Credentials**  
✅ **Example Template Provided**

## ⚠️ Important Security Notes

1. **Never commit `.env` files** - Add to `.gitignore`
2. **Set proper file permissions** - `chmod 600 .env`
3. **Use different credentials** for development vs production
4. **Rotate API keys regularly**
5. **Monitor SMTP usage** in Brevo dashboard

## 🧪 Testing

Test the secure configuration:

```bash
# Set environment variables
export SMTP_USER="your_username"
export SMTP_PASSWORD="your_password"

# Run outreach system
python music_outreach.py --dry-run

# Should show: "✅ Environment variables loaded from .env file"
```

## 📂 File Structure

```
ob-cms/
├── .env                 # Your actual credentials (DON'T COMMIT)
├── .env.example         # Template file (safe to commit)
├── music_outreach.py    # Now uses environment variables
├── .gitignore           # Should include .env
└── ENVIRONMENT_SETUP.md # This guide
```

Your outreach system is now secure and production-ready! 🎵🔒
