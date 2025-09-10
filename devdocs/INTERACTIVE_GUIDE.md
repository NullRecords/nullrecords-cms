# 🎵 NullRecords Interactive Outreach System

## 🚀 New Features Added

✅ **Brevo SMTP Integration** - Professional email sending  
✅ **Interactive Preview System** - Review every email before sending  
✅ **Daily Push Notifications** - Get summaries sent to your email  
✅ **CLI Email Editor** - Edit subjects on the fly  
✅ **Smart Approval Workflow** - Skip, send, or quit at any point  

## 📧 Quick Start

### Daily Interactive Session
```bash
# Run the friendly interactive script
./interactive_outreach.sh

# Or run directly with Python
python3 music_outreach.py --interactive --notify "greg@nullrecords.com"
```

### What You'll See
```
🎵 NullRecords Daily Outreach Preview
==================================================
📅 Date: 2025-09-09 16:45
📊 Contacts Ready: 12
==================================================

📧 Email Preview 1/12
────────────────────────────────────────
👤 To: Pitchfork (publication)
📧 Email: tips@pitchfork.com
🎯 Confidence: 0.75
🔄 Attempt: #1
🌐 Website: https://pitchfork.com
📝 Subject: 🎵 Introducing NullRecords: LoFi, Jazz Fusion, Electronic Jazz Music Collective
────────────────────────────────────────
📄 Message Preview:
Hello Pitchfork team,
I hope this message finds you well! I'm reaching out to introduce you to NullRecords, an independent music collective creating innovative sounds at the junction of music, art, and technology...
────────────────────────────────────────

[s]end, [skip], [edit subject], [view full], [quit]: 
```

### Interactive Commands
- **`s` or `send`** - Approve this email for sending
- **`skip`** - Skip this contact for today  
- **`edit subject`** - Modify the email subject line
- **`view full`** - See the complete email body
- **`quit`** - Cancel the entire session

## 📱 Push Notifications

After each session, you'll receive an email summary:
```
🎵 NullRecords Daily Outreach Summary
Date: 2025-09-09 16:45

📊 RESULTS:
✅ Emails Successfully Sent: 8
📝 Emails Approved: 10  
❌ Failed Sends: 2

📈 CAMPAIGN STATS:
Total Contacts: 47
Responses Received: 3
Recent Activity: 8 contacts

🔗 Next Steps:
- Monitor responses in your email
- Update contact status when responses received
- Review tomorrow's outreach queue
```

## ⚙️ Configuration

### Email Settings (outreach_config.json)
```json
{
  "notification_settings": {
    "recipient_email": "greg@nullrecords.com",
    "daily_summary": true,
    "send_on_completion": true
  },
  "interactive_settings": {
    "default_mode": "interactive",
    "preview_length": 300
  }
}
```

### SMTP Configuration
Already configured with your Brevo settings:
- **Server**: smtp-relay.brevo.com
- **Port**: 587  
- **Username**: 96afc8001@smtp-brevo.com
- **From**: team@nullrecords.com

## 📅 Daily Workflow Options

### Option 1: Manual Interactive (Recommended)
```bash
# Run when you have 10-15 minutes to review emails
./interactive_outreach.sh
```

### Option 2: Scheduled with Review
Add to crontab for daily notification, then run interactively:
```bash
# Cron sends you notification at 9 AM
0 9 * * * /path/to/daily_outreach.sh

# Then run interactively when ready
./interactive_outreach.sh
```

### Option 3: Fully Automated (Advanced)
```bash  
# For fully automated sending (use with caution)
python3 music_outreach.py --daily --notify "greg@nullrecords.com"
```

## 🎯 Usage Examples

### Review Only High-Confidence Contacts
```bash
python3 music_outreach.py --interactive --target-type publication --limit 5
```

### Test New Email Templates
```bash
python3 music_outreach.py --interactive --dry-run --limit 3
```

### Focus on Specific Contact Types
```bash
python3 music_outreach.py --interactive --target-type influencer --notify "greg@nullrecords.com"
```

## 📊 Monitoring & Reports

### Daily Activity
```bash
# Get current campaign status
python3 music_outreach.py --report

# View contact database
python3 music_outreach.py --export
```

### Log Files
- **`outreach.log`** - Detailed activity log
- **`daily_outreach_log.json`** - Daily summaries  
- **`daily_outreach_YYYYMMDD.log`** - Daily detailed logs

## 🔄 Email Workflow

### Email Approval Process
1. **Discover** new contacts (2-5 daily)
2. **Prepare** personalized emails based on contact type
3. **Preview** each email with full details
4. **Edit** subjects if needed  
5. **Approve** or skip each contact
6. **Send** all approved emails with rate limiting
7. **Notify** you with summary via email

### Smart Features
- **Rate Limiting**: 2-5 second delays between sends
- **Confidence Scoring**: Prioritizes high-quality contacts
- **Frequency Management**: Respects 7-day minimums  
- **Response Tracking**: Updates contact status
- **Error Handling**: Logs failed sends for retry

## 🎵 Best Practices

### Daily Routine
1. **Morning**: Check your notification email for yesterday's results
2. **Mid-day**: Run `./interactive_outreach.sh` when you have 15 minutes
3. **Review**: Quickly approve/skip contacts based on quality
4. **Monitor**: Watch for responses in your main email

### Email Quality Tips
- **Edit subjects** to be more specific if needed
- **Skip low-confidence** contacts (< 0.5 score)
- **View full emails** for important contacts
- **Focus on publications** first, then influencers

### Response Management
- **Reply promptly** to any responses received
- **Update contact status** manually when responses come in
- **Build relationships** - don't just send and forget
- **Track what works** - note which approaches get responses

## 🚨 Safety Features

- **Interactive approval** prevents accidental spam
- **Rate limiting** protects your sender reputation
- **Dry run mode** for testing changes
- **Quit anytime** to cancel sessions
- **Comprehensive logging** for troubleshooting

## 🎉 Ready to Rock!

Your interactive outreach system is now:
- ✅ **Connected to Brevo** for professional email delivery
- ✅ **Sending daily notifications** to greg@nullrecords.com
- ✅ **Interactive preview system** for full control
- ✅ **Smart discovery** finding new contacts daily
- ✅ **Fully documented** and ready to use

Start with: `./interactive_outreach.sh` and begin building your music industry network with confidence! 🚀🎶
