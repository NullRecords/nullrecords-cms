# NullRecords Daily Automation System

## Overview
The daily automation system now runs activities in the correct sequence to show real progress in daily reports:

1. **🔍 Outreach Discovery** - Find new music industry contacts
2. **📧 Daily Outreach** - Send emails to pending contacts  
3. **📊 Daily Report** - Send comprehensive report with REAL activity results

## Usage

### Complete Daily Automation (Recommended)
```bash
# Run full automation sequence
python3 scripts/daily_automation.py

# Run with limited outreach (e.g., 5 emails max)
python3 scripts/daily_automation.py --outreach-limit 5
```

### Partial Automation
```bash
# Skip discovery (just outreach + report)
python3 scripts/daily_automation.py --skip-discovery

# Skip outreach (just discovery + report) 
python3 scripts/daily_automation.py --skip-outreach

# Only send report (not recommended - won't show progress)
python3 scripts/daily_automation.py --skip-discovery --skip-outreach
```

### Testing
```bash
# See what would run without executing
python3 scripts/daily_automation.py --dry-run
```

## Key Improvements

### ✅ **Real Data Instead of Placeholders**
- Fixed environment variable loading in daily_report.py
- Now shows actual Google Analytics, YouTube, and outreach data
- "0 visitors" means real zero data, not mock data

### ✅ **Correct Automation Sequence** 
- **OLD**: Daily report first (shows zeros) → Outreach activities
- **NEW**: Outreach activities first → Daily report (shows progress)

### ✅ **Activity Tracking**
The daily report now shows:
- New sources discovered today (with details)
- Emails sent during outreach (real count)
- Responses received (tracked)
- Real website and YouTube analytics
- Progress toward outreach goals

## Environment Configuration

Make sure your `.env` file is properly configured:

```properties
# Outreach Limits
MAX_DAILY_OUTREACH=10
RATE_LIMIT_DELAY=2

# Email Configuration  
CC_EMAIL=greg@buildly.io
DAILY_REPORT_EMAIL=team@nullrecords.com

# Analytics
GA_PROPERTY_ID=308964282
YOUTUBE_CHANNEL_ID=UC_ZC9UiWcjyOLGp4iQwyv2w
```

## Daily Workflow

### Morning Automation
```bash
# Run complete daily sequence (recommended)
python3 scripts/daily_automation.py --outreach-limit 10
```

This will:
1. Search for new lofi/nu-jazz/indie contacts
2. Send up to 10 outreach emails
3. Email you comprehensive results

### Manual Outreach (Optional)
```bash
# Just run outreach without discovery or report
python3 scripts/music_outreach.py --daily --limit 5

# Then manually send report later
python3 scripts/daily_report.py --send-email
```

## Expected Results

With the new sequence, your daily emails will show:
- **Real progress**: "3 new sources found", "5 emails sent"  
- **Genre targeting**: Focus on LoFi • Nu Jazz • Jazz Fusion • Indie
- **Actual analytics**: Real visitor counts and YouTube metrics
- **Response tracking**: Any replies from music industry contacts

The automation now demonstrates real business activity and progress toward your music industry outreach goals! 🎵