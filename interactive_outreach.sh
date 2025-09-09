#!/bin/bash

# NullRecords Interactive Daily Outreach
# Run this manually each day to review and approve outreach emails

clear
echo "🎵 NullRecords Interactive Outreach System"
echo "=========================================="
echo ""
echo "This will:"
echo "1. 🔍 Discover new music industry contacts"  
echo "2. 📧 Prepare personalized outreach emails"
echo "3. 🔍 Let you preview each email before sending"
echo "4. 📱 Send you a summary notification"
echo ""

# Check if config exists
if [ ! -f "outreach_config.json" ]; then
    echo "⚠️  Configuration file not found"
    echo "Creating default config..."
fi

# Check dependencies
echo "📦 Checking dependencies..."
python3 -c "import requests, smtplib" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ Missing dependencies. Installing..."
    pip3 install -r requirements.txt
fi

echo ""
echo "🚀 Starting interactive outreach session..."
echo "   (You'll review each email before it's sent)"
echo ""

# Run interactive outreach
python3 music_outreach.py --interactive --notify "greg@nullrecords.com"

RESULT=$?

echo ""
if [ $RESULT -eq 0 ]; then
    echo "✅ Outreach session completed successfully!"
    echo "📱 Check your email for the daily summary"
else
    echo "❌ Outreach session encountered errors"
    echo "📋 Check the logs for details"
fi

echo ""
echo "📊 Current campaign status:"
python3 music_outreach.py --report

echo ""
echo "🎵 Thank you for promoting NullRecords!"
echo "Run this script daily to build your music industry network."
