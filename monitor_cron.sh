#!/bin/bash
# NullRecords Cron Job Monitor

echo "🔍 NullRecords Cron Job Status - $(date)"
echo "========================================"

# Check if cron service is running
if pgrep cron > /dev/null; then
    echo "✅ Cron service is running"
else
    echo "❌ Cron service is not running"
fi

# Show recent log entries
if [[ -f ~/nullrecords_cron.log ]]; then
    echo ""
    echo "📋 Recent Log Entries (last 20 lines):"
    tail -20 ~/nullrecords_cron.log
else
    echo "⚠️  No cron log file found at ~/nullrecords_cron.log"
fi

# Show active NullRecords cron jobs
echo ""
echo "⏰ Active NullRecords Cron Jobs:"
crontab -l | grep -E "(music_outreach|daily_report|news_system)" || echo "No NullRecords cron jobs found"

# Check disk space
echo ""
echo "💾 Disk Space:"
df -h . | tail -1

# Check last git commit
echo ""
echo "📦 Last Git Commit:"
git log -1 --oneline 2>/dev/null || echo "No git repository"

