# NullRecords Google Analytics GA4 Configuration

## 🎯 **Your Specific Setup Details**

### ✅ **Google Analytics GA4 Stream Information**
```
Property Name: Null Records
Stream URL: https://www.nullrecords.com
Stream ID: 3376868194
Measurement ID: G-2WVCJM4NKR
```

### ✅ **Frontend Tracking Status**
- **Status**: ✅ **ACTIVE** 
- **Implementation**: Shared header system (`shared-header.js`)
- **Tracking ID**: `G-2WVCJM4NKR` ✅ Already configured
- **Pages covered**: All pages with shared header include

### ⚠️ **Backend Reporting Status**
- **Status**: ❌ **MOCK DATA** (needs service account setup)
- **Implementation**: Daily report script (`scripts/daily_report.py`)
- **Required**: Google Cloud service account JSON file

---

## 🚀 **Quick Setup Guide**

### 1. **Install Dependencies** (5 minutes)
```bash
cd /Users/greglind/Projects/NullRecords/ob-cms
./setup-ga4.sh
```

### 2. **Configure Service Account** (10 minutes)

#### A. Create Google Cloud Project
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create new project: "nullrecords-analytics"
3. Enable "Google Analytics Data API"

#### B. Create Service Account
1. Go to "APIs & Services" → "Credentials"
2. Create Credentials → Service Account
3. Name: "nullrecords-ga4-reader"
4. Role: "Viewer"
5. Download JSON key file

#### C. Add Service Account to Analytics
1. Copy service account email from JSON file
2. Go to [Google Analytics](https://analytics.google.com/)
3. Admin → Property Access Management
4. Add service account email with "Viewer" permissions

### 3. **Configure Environment** (2 minutes)
```bash
# Edit your .env file
nano .env

# Add these lines (replace with your actual file path):
GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/nullrecords-ga4-service-account.json
GA_PROPERTY_ID=3376868194
GA_MEASUREMENT_ID=G-2WVCJM4NKR
```

### 4. **Test Configuration** (1 minute)
```bash
# Test the setup
python3 scripts/daily_report.py

# Should see: "✅ GA4 data collected" instead of "using mock data"
```

---

## 📊 **Current Implementation Status**

### ✅ **What's Working Now**
- **Frontend Tracking**: Real visitor data being collected
- **Google Analytics Dashboard**: Live data available
- **Shared Header System**: Consistent tracking across all pages
- **Performance Optimization**: Preconnect links for faster loading

### ⏳ **What Needs Service Account**
- **Daily Email Reports**: Currently using mock data
- **Analytics API Access**: Backend data collection
- **Historical Data**: Access to past analytics data

---

## 🔧 **Environment Configuration**

### **Required Variables**
```bash
# GA4 Configuration (your specific values)
GA_PROPERTY_ID=3376868194
GA_MEASUREMENT_ID=G-2WVCJM4NKR
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
```

### **Optional Variables** (for other features)
```bash
# YouTube API (for channel metrics in reports)
YOUTUBE_API_KEY=your_youtube_api_key
YOUTUBE_CHANNEL_ID=your_channel_id

# Email Configuration (for sending reports)
SMTP_SERVER=your_smtp_server
SMTP_USER=your_smtp_username
SMTP_PASSWORD=your_smtp_password
SENDER_EMAIL=your_sender_email
DAILY_REPORT_EMAIL=reports@nullrecords.com
```

---

## 🧪 **Testing Your Setup**

### **1. Test Frontend Tracking**
```javascript
// Open browser console on nullrecords.com
console.log('gtag loaded:', typeof window.gtag === 'function');

// Send test event
gtag('event', 'test_setup', {
  'custom_parameter': 'ga4_configuration_test'
});
```

### **2. Test Backend API**
```bash
# Run daily report and check output
python3 scripts/daily_report.py

# Look for these messages:
# ✅ "GA4 data collected: X users, Y pageviews"  = WORKING
# ⚠️  "using mock data"                          = NEEDS SETUP
```

### **3. Verify Google Analytics Dashboard**
1. Go to [Google Analytics](https://analytics.google.com/)
2. Select "Null Records" property
3. Check "Realtime" report for live visitors
4. Verify data matches your website activity

---

## 📈 **Expected Data Flow**

### **Frontend (gtag.js)**
```
Website Visitor → gtag.js → Google Analytics → Real-time Dashboard
```

### **Backend (Daily Reports)**
```
Daily Report Script → GA4 Data API → Yesterday's Analytics → Email Report
```

---

## 🚨 **Troubleshooting**

### **"Permission denied" Error**
```bash
# Check service account permissions in Google Analytics
# Ensure service account email has "Viewer" role
```

### **"Property not found" Error**
```bash
# Verify GA_PROPERTY_ID is exactly: 3376868194
echo $GA_PROPERTY_ID
```

### **"Import errors" in Python**
```bash
# Install missing dependencies
pip3 install google-analytics-data google-auth
```

### **"gtag is not defined" Error**
```javascript
// Verify shared-header.js is loading
console.log('NullRecords header loaded:', window.NullRecordsHeader);
```

---

## 📋 **Configuration Checklist**

- [ ] ✅ Frontend tracking active (gtag.js via shared-header.js)
- [ ] ⏳ Google Cloud project created
- [ ] ⏳ Analytics Data API enabled
- [ ] ⏳ Service account created and JSON downloaded
- [ ] ⏳ Service account added to GA property permissions
- [ ] ⏳ GOOGLE_APPLICATION_CREDENTIALS set in .env
- [ ] ⏳ Daily report test shows "GA4 data collected"

Once all items are checked, your NullRecords analytics will provide real data for both live tracking and daily reports!

---

## 🎵 **NullRecords-Specific Notes**

- **Website**: https://www.nullrecords.com (matches GA4 stream URL ✅)
- **Measurement ID**: G-2WVCJM4NKR (already in shared-header.js ✅)
- **Property ID**: 3376868194 (for backend API access)
- **Pages tracked**: All pages with `<script src="/shared-header.js"></script>`

Your analytics setup is designed to provide comprehensive data for your music collective's digital presence, including visitor behavior, popular content, and traffic sources to help optimize your promotional strategy.