# NullRecords Daily Status Report System Setup

## 🚀 Quick Start Guide

### 1. Install Dependencies
```bash
# Install Python packages
pip3 install requests beautifulsoup4 python-dotenv

# Optional: Install Google API packages for real data
pip3 install google-api-python-client google-auth
```

### 2. Environment Configuration
Create a `.env` file with the following configuration:

```bash
# Required: SMTP Configuration for email reports
SMTP_SERVER=smtp-relay.brevo.com
SMTP_PORT=587
SMTP_USERNAME=your_brevo_username
SMTP_PASSWORD=your_brevo_password
SENDER_EMAIL=team@nullrecords.com
DAILY_REPORT_EMAIL=team@nullrecords.com

# Optional: Google Analytics Integration
GOOGLE_SERVICE_ACCOUNT_PATH=/path/to/service-account-key.json
GA_VIEW_ID=your_google_analytics_view_id

# Optional: YouTube Analytics
YOUTUBE_API_KEY=your_youtube_api_key
YOUTUBE_CHANNEL_ID=your_youtube_channel_id

# Optional: Google Sheets Voting Data
GOOGLE_SHEETS_ID=your_google_sheets_id
VOTING_SHEET_NAME=Votes

# Optional: Brevo API for detailed email metrics
BREVO_API_KEY=your_brevo_api_key
```

### 3. Test the System
```bash
# Test report generation (uses mock data)
./daily_report_system.sh test

# Generate HTML report only
./daily_report_system.sh generate

# Generate and email report
./daily_report_system.sh email
```

### 4. Set Up Automation
```bash
# Set up daily automated email reports at 8 AM
./daily_report_system.sh setup-cron
```

## 📊 Data Sources & Metrics

### Website Analytics (Google Analytics)
- **Unique Visitors**: Daily unique users
- **Page Views**: Total pages viewed
- **Sessions**: User sessions with duration
- **Bounce Rate**: Percentage of single-page sessions
- **Top Pages**: Most visited pages
- **Traffic Sources**: Where visitors come from

### YouTube Channel Metrics
- **Subscribers**: Current subscriber count
- **Total Views**: Lifetime channel views
- **New Videos**: Videos published in last 24 hours
- **Watch Time**: Total hours watched
- **Top Videos**: Best performing content

### Email Campaign Performance
- **Emails Sent**: Daily outreach volume
- **Campaign Count**: Number of campaigns run
- **Open Rate**: Email engagement percentage
- **Click Rate**: Link click performance
- **Sources**: Outreach system + news notifications

### Voting & Engagement (Google Sheets)
- **New Votes**: Votes received today
- **Total Votes**: All-time voting count
- **Artist Preferences**: Votes by artist
- **Category Trends**: Popular voting categories
- **Recent Activity**: Latest vote submissions

### News & Content Monitoring
- **New Articles**: Articles discovered today
- **New Releases**: Streaming platform releases found
- **Monitoring Sources**: Number of sources checked
- **Sentiment Analysis**: Positive/negative coverage
- **Content Types**: Reviews, news, interviews, releases

### System Health Metrics
- **Uptime**: System availability percentage
- **Response Times**: API and website performance
- **Error Count**: Daily error occurrences
- **Log Analysis**: System performance indicators

## 📧 Email Report Features

### Professional HTML Design
- **Retro-Cyber Theme**: Matches NullRecords branding
- **Responsive Layout**: Works on mobile and desktop
- **Visual Metrics**: Charts and progress indicators
- **Interactive Elements**: Hover effects and styling

### Report Sections
1. **Executive Summary**: Key highlights and insights
2. **Website Performance**: Traffic and engagement metrics
3. **Content Marketing**: Email and social media performance
4. **Community Engagement**: Voting and interaction data
5. **Content Discovery**: News articles and release monitoring
6. **Technical Health**: System performance and reliability

### Automated Scheduling
- **Daily Reports**: Comprehensive morning briefing
- **Weekly Summaries**: Week-over-week comparisons
- **Monthly Analytics**: Detailed performance analysis
- **Alert System**: Immediate notifications for critical issues

## 🔗 Integration Points

### Music Outreach System
- Tracks emails sent through outreach campaigns
- Monitors campaign success rates
- Reports on contact engagement
- BCC notifications to team

### News Monitoring System
- Counts articles and releases discovered
- Analyzes content sentiment
- Tracks source performance
- Monitors streaming platforms

### Website Analytics
- Real-time traffic data
- User behavior analysis
- Content performance metrics
- SEO and search performance

### Social Media Platforms
- YouTube channel analytics
- Social media engagement
- Content reach and impressions
- Audience growth metrics

## 🎯 Key Performance Indicators (KPIs)

### Growth Metrics
- Daily unique visitors
- Email list growth
- YouTube subscriber increases
- Social media followers

### Engagement Metrics
- Session duration
- Pages per session
- Email open/click rates
- Video watch time

### Content Metrics
- New content published
- Content engagement rates
- Search rankings
- Social media shares

### Business Metrics
- Outreach campaign effectiveness
- Conversion rates
- Community growth
- Brand mention sentiment

## 🛠️ Advanced Configuration

### Google Analytics Setup
1. Create Google Cloud Project
2. Enable Analytics Reporting API
3. Create service account
4. Download JSON key file
5. Add GA_VIEW_ID to environment

### YouTube Analytics Setup
1. Enable YouTube Data API v3
2. Create API key
3. Get channel ID from YouTube Studio
4. Add credentials to environment

### Google Sheets Integration
1. Create Google Sheet for voting data
2. Set up headers: Timestamp, Artist, Category, Vote, Email, Comments
3. Share sheet with service account email
4. Add sheet ID to environment

### Brevo Email Analytics
1. Get Brevo API key from dashboard
2. Configure webhook endpoints
3. Set up campaign tracking
4. Add API key to environment

## 📈 Sample Report Output

```
🎵 NULLRECORDS DAILY REPORT - 2025-09-10

🌐 WEBSITE ANALYTICS
- Unique Visitors: 287 (+12% vs yesterday)
- Page Views: 654 (2.3 pages/session)
- Top Page: /news/ (127 views)
- Top Source: google (156 visits)

📧 EMAIL CAMPAIGNS
- Emails Sent: 45 (3 campaigns)
- Open Rate: 32.4%
- Click Rate: 5.8%

🗳️ VOTING & ENGAGEMENT
- New Votes: 18
- Total Votes: 267
- Top Choice: My Evil Robot Army (67 votes)

📰 NEWS MONITORING
- New Articles: 3 (2 positive sentiment)
- New Releases: 1 (SoundCloud)
- Sources Monitored: 12

📺 YOUTUBE CHANNEL
- Subscribers: 1,347 (+5 today)
- Total Views: 18,942
- New Videos: 1

🔧 SYSTEM HEALTH
- Uptime: 99.8%
- Errors: 0
- Response Time: 245ms
```

## 🚀 Next Steps

1. **Complete Environment Setup**: Add all API keys and credentials
2. **Test with Real Data**: Verify all integrations work correctly  
3. **Customize Metrics**: Add business-specific KPIs
4. **Set Up Alerts**: Configure thresholds for important metrics
5. **Schedule Automation**: Enable daily/weekly reporting
6. **Dashboard Integration**: Consider building web dashboard
7. **Historical Analysis**: Set up trend analysis and comparisons

---

**The daily report system provides comprehensive insights into all aspects of NullRecords operations, from website traffic to music release performance! 📊🎵**
