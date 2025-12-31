#!/bin/bash

# NullRecords Daily Outreach Automation Script
# Add this to your crontab to run daily: 0 10 * * * /path/to/daily_outreach.sh

# Set working directory to project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

# Log file with timestamp
LOG_FILE="daily_outreach_$(date +%Y%m%d).log"

echo "🎵 NullRecords Daily Outreach - $(date)" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"

# Check if Python script exists
if [ ! -f "scripts/music_outreach.py" ]; then
    echo "❌ scripts/music_outreach.py not found!" | tee -a "$LOG_FILE"
    exit 1
fi

# Install/update requirements if needed
if [ -f "requirements.txt" ]; then
    echo "📦 Checking Python dependencies..." | tee -a "$LOG_FILE"
    pip3 install -r requirements.txt >> "$LOG_FILE" 2>&1
fi

# Run daily outreach
echo "🚀 Starting daily outreach..." | tee -a "$LOG_FILE"

# Check if running interactively (terminal attached)
if [ -t 0 ]; then
    echo "🎯 Interactive mode - you'll review emails before sending"
    python3 scripts/music_outreach.py --interactive --notify "greg@nullrecords.com" | tee -a "$LOG_FILE"
else
    echo "🤖 Automated mode - sending pre-approved emails"
    python3 scripts/music_outreach.py --daily --notify "greg@nullrecords.com" >> "$LOG_FILE" 2>&1
fi

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ Daily outreach completed successfully" | tee -a "$LOG_FILE"
else
    echo "❌ Daily outreach failed with exit code $EXIT_CODE" | tee -a "$LOG_FILE"
fi

# Clean up old log files (keep last 7 days)
find . -name "daily_outreach_*.log" -mtime +7 -delete

echo "📊 Outreach complete - $(date)" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# Optional: Send summary email (uncomment and configure)
# python3 -c "
# import json
# from datetime import datetime
# try:
#     with open('daily_outreach_log.json', 'r') as f:
#         log = json.load(f)
#     today = log[-1] if log else {}
#     print(f'Daily Summary: {today.get(\"contacts_reached\", 0)} contacts reached')
# except:
#     print('No daily log found')
# " | tee -a "$LOG_FILE"

exit $EXIT_CODE
