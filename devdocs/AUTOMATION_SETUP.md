# NullRecords Outreach Automation Setup Guide

## 🚀 Enhanced Features

The outreach system now includes:

✅ **Automatic Source Discovery** - Finds new music blogs, publications, and influencers  
✅ **Smart Frequency Management** - Prevents spam with intelligent retry logic  
✅ **Confidence Scoring** - Prioritizes high-quality prospects  
✅ **Daily Automation** - Scheduled outreach with balanced targeting  
✅ **Comprehensive Tracking** - Full history of all outreach attempts  

## 📅 Setting Up Daily Automation

### Option 1: macOS/Linux Cron Job

1. **Make the script executable:**
```bash
chmod +x daily_outreach.sh
```

2. **Edit your crontab:**
```bash
crontab -e
```

3. **Add this line to run daily at 10 AM:**
```bash
0 10 * * * /Users/greglind/Projects/NullRecords/ob-cms/daily_outreach.sh
```

4. **Alternative times:**
```bash
# Run at 9 AM weekdays only
0 9 * * 1-5 /path/to/daily_outreach.sh

# Run twice daily (9 AM and 3 PM)
0 9,15 * * * /path/to/daily_outreach.sh

# Run every 3 days at 10 AM  
0 10 */3 * * /path/to/daily_outreach.sh
```

### Option 2: Manual Daily Run

```bash
# Run today's outreach (dry run first)
./daily_outreach.sh

# Or run directly with Python
python3 music_outreach.py --daily --dry-run
python3 music_outreach.py --daily  # Actually send
```

## 🎯 Outreach Strategy & Limits

### Daily Distribution (Configurable)
- **Publications (40%)**: Music blogs, magazines, reviews  
- **Influencers (25%)**: YouTube channels, curators
- **Curators (15%)**: Playlist makers, discovery platforms
- **Platforms (10%)**: Streaming services, databases  
- **AI Services (10%)**: AI music discovery, search engines

### Frequency Management
- **Maximum 4 outreach attempts** per contact
- **Minimum 7 days** between attempts to same contact
- **Daily limit**: 20 contacts (adjustable)
- **2-4 outreach per source** as requested

### Smart Discovery
- **Finds 2-5 new sources daily** through web scraping
- **Confidence scoring** (0.0-1.0) prioritizes quality prospects
- **Automatic deduplication** prevents contact spam
- **Source tracking** monitors which sites are most productive

## 📊 Monitoring & Reports

### Daily Logs
```bash
# View today's activity
cat daily_outreach_$(date +%Y%m%d).log

# View outreach history  
python3 music_outreach.py --report

# Export contact database
python3 music_outreach.py --export
```

### Key Metrics Tracked
- **Outreach count** per contact
- **Response rates** by contact type
- **Source discovery** effectiveness  
- **Daily/weekly** performance trends

## 🛠 Advanced Usage

### Target Specific Types
```bash
# Focus on publications only
python3 music_outreach.py --daily --target-type publication

# Discover new sources without outreach
python3 music_outreach.py --discover

# Test specific contact types
python3 music_outreach.py --target-type influencer --limit 3 --dry-run
```

### Custom Configuration
Edit `outreach_schedule.json` to adjust:
- Daily contact limits
- Contact type distribution  
- Follow-up timing
- Discovery settings

```json
{
  "daily_outreach": {
    "enabled": true,
    "max_contacts_per_day": 25,
    "target_distribution": {
      "publication": 0.5,
      "influencer": 0.3,
      "curator": 0.2
    }
  }
}
```

## 🔍 Source Discovery

The system automatically finds new contacts by:

1. **Searching** for music industry terms
2. **Scraping** relevant websites for contact info  
3. **Extracting** email addresses and contact forms
4. **Classifying** site types and genre focus
5. **Scoring** confidence based on relevance

### Discovery Terms Used
- "electronic music blog submit"
- "lofi music submission"  
- "jazz fusion publication contact"
- "independent music blog"
- "chillhop music curator"
- And more...

## 📈 Success Tracking

### Contact Status Flow
```
pending → contacted → responded/indexed
     ↓
manual_submission_required → followed_up
```

### Key Success Indicators
- **Response rate** > 5% is excellent
- **Index/feature rate** > 2% is great success
- **Source discovery** 3-5 new contacts/day ideal
- **Outreach frequency** 15-25 contacts/day sustainable

## 🚨 Best Practices

1. **Always dry-run first** when testing changes
2. **Monitor logs** for errors or blocks  
3. **Update contact info** when responses received
4. **Respect unsubscribe requests** immediately
5. **Keep press kit content** fresh and relevant
6. **Review discovered contacts** for quality
7. **Track what works** and adjust strategy

## 🔧 Troubleshooting

### Common Issues

**No new sources discovered:**
- Check internet connection
- Verify beautifulsoup4 installed: `pip install beautifulsoup4`
- Some sites may block automated access

**Emails not sending:**
- Configure SMTP settings in `send_email()` method
- Currently in placeholder mode for safety

**Cron job not running:**
- Check cron logs: `grep CRON /var/log/syslog`
- Verify absolute paths in crontab
- Check script permissions: `ls -la daily_outreach.sh`

**Rate limiting:**
- Built-in delays prevent most blocking
- Adjust sleep times if needed
- Some discovery may fail - this is normal

## 📧 Email Configuration

To enable actual email sending, edit the `send_email` method:

```python
def send_email(self, to_email: str, subject: str, body: str) -> bool:
    try:
        msg = MimeMultipart()
        msg['From'] = "team@nullrecords.com"
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MimeText(body, 'plain'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login("your_email@gmail.com", "your_app_password")
        server.sendmail("team@nullrecords.com", to_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        logging.error(f"Email sending failed: {e}")
        return False
```

## 📁 File Structure

```
ob-cms/
├── music_outreach.py          # Main outreach script
├── daily_outreach.sh          # Automation shell script  
├── requirements.txt           # Python dependencies
├── OUTREACH_README.md         # Documentation
├── AUTOMATION_SETUP.md        # This file
└── [Generated Files - Git Ignored]
    ├── outreach_contacts.json     # Contact database
    ├── outreach_sources.json      # Source tracking
    ├── outreach_schedule.json     # Configuration  
    ├── daily_outreach_log.json    # Daily summaries
    ├── daily_outreach_*.log       # Daily detailed logs
    └── outreach.log              # General activity log
```

## 🎵 Ready to Rock!

Your NullRecords outreach system is now fully automated and will:

- **Discover new music industry contacts daily**
- **Send personalized press kits** to 15-25 contacts/day  
- **Track all responses and follow-ups**
- **Respect frequency limits** (2-4 contacts per source max)
- **Generate detailed reports** on campaign success
- **Run completely hands-off** once configured

The system learns and improves over time, building a comprehensive database of music industry contacts while maintaining professional outreach standards.

Start with `--dry-run` to see it in action, then let it run daily to build your music's presence across the industry! 🚀🎶
