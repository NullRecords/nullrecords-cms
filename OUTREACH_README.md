# NullRecords Music Industry Outreach Tool 🎵

An automated press kit distribution and outreach system for music discovery platforms, AI services, influencers, and publications.

## Overview

This tool helps NullRecords reach out to:
- **Search Engines & AI Services** (Google, Bing, Perplexity, ChatGPT, etc.)
- **Music Publications** (Pitchfork, The Fader, Stereogum, etc.)
- **Electronic/Jazz Focused Media** (Resident Advisor, Jazz Times, etc.)
- **LoFi/Chillhop Curators** (Chillhop Music, LoFi Girl, etc.)
- **YouTube Influencers** (Majestic Casual, Mr. Suicide Sheep, etc.)
- **Music Platforms** (Spotify, Apple Music, Bandcamp, etc.)
- **Playlist Curators** (Indie Shuffle, The Music Ninja, etc.)

## Features

✅ **Comprehensive Contact Database** - 40+ pre-loaded industry contacts  
✅ **Personalized Press Kit Emails** - Dynamic content based on contact type  
✅ **Response Tracking** - Track who responds and when  
✅ **Status Management** - Monitor outreach progress  
✅ **Search Engine Submission** - Automated indexing requests  
✅ **Rate Limiting** - Respectful outreach timing  
✅ **Dry Run Mode** - Test before sending  
✅ **Detailed Reporting** - Track campaign success  

## Installation

```bash
# Install Python dependencies
pip install -r requirements.txt

# Initialize the contact database
python music_outreach.py --init
```

## Usage

### Basic Commands

```bash
# Dry run to see what would be sent (recommended first)
python music_outreach.py --dry-run

# Send outreach to all pending contacts
python music_outreach.py

# Target specific contact types
python music_outreach.py --target-type publication
python music_outreach.py --target-type influencer
python music_outreach.py --target-type ai_service

# Limit number of contacts (for testing)
python music_outreach.py --limit 5 --dry-run

# Generate status report
python music_outreach.py --report

# Export contact list for manual use
python music_outreach.py --export
```

### Contact Types Available

- `search_engine` - Google, Bing, DuckDuckGo
- `ai_service` - ChatGPT, Claude, Perplexity
- `publication` - Music blogs and magazines
- `influencer` - YouTube channels and curators
- `platform` - Spotify, Apple Music, Bandcamp
- `curator` - Playlist curators and music discovery

## Email Configuration

To enable actual email sending, edit the `send_email` method in `music_outreach.py`:

```python
def send_email(self, to_email: str, subject: str, body: str) -> bool:
    try:
        msg = MimeMultipart()
        msg['From'] = "team@nullrecords.com"
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MimeText(body, 'plain'))
        
        # Configure your SMTP server
        server = smtplib.SMTP('smtp.gmail.com', 587)  # Or your provider
        server.starttls()
        server.login("your_email@gmail.com", "your_app_password")
        server.sendmail("team@nullrecords.com", to_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        logging.error(f"Email sending failed: {e}")
        return False
```

## Sample Output

```
INFO - Starting NullRecords outreach campaign...
INFO - Loaded 42 contacts
INFO - Targeting 15 contacts for outreach
INFO - ✅ Emailed Pitchfork
INFO - ✅ Emailed The Fader  
INFO - 📝 Manual submission required for Spotify Editorial
INFO - ✅ Emailed Jazz Times
INFO - Outreach campaign completed!

NULLRECORDS OUTREACH REPORT
Generated: 2025-09-09 15:30:00

TOTAL CONTACTS: 42

STATUS BREAKDOWN:
  contacted: 12
  manual_submission_required: 5
  pending: 25

TYPE BREAKDOWN:
  ai_service: 6
  influencer: 8
  platform: 7
  publication: 12
  search_engine: 3
```

## Press Kit Content

The tool automatically generates personalized emails including:

- **NullRecords introduction** and mission
- **Artist profiles** (My Evil Robot Army, MERA)
- **Genre focus** (LoFi, Jazz Fusion, Electronic Jazz)
- **Website and contact information**
- **Customized relevance** based on contact type
- **Call to action** directing to team@nullrecords.com

## Data Files (Auto-Generated, Git-Ignored)

- `outreach_contacts.json` - Contact database with status tracking
- `outreach_data.json` - Campaign data and metrics  
- `outreach.log` - Detailed activity logs
- `outreach_contacts_export.json` - Exportable contact list

## Contact Management

The tool tracks:
- **Contact Information** - Email, social media, submission URLs
- **Status** - pending, contacted, responded, indexed, rejected
- **Dates** - When contacted, when responded
- **Response Content** - What they said
- **Genre Focus** - What music types they cover

## Best Practices

1. **Always dry-run first** to review content
2. **Start small** with `--limit 5` for testing
3. **Target specific types** based on your strategy
4. **Monitor responses** and update contact status
5. **Respect rate limits** - tool includes automatic delays
6. **Follow up appropriately** - don't spam

## Manual Submissions Required

Some platforms require manual submission:
- **Google Search Console** - Submit sitemap manually
- **Spotify Editorial** - Use Spotify for Artists portal
- **Apple Music** - Use Apple Music for Artists
- **Contact forms** - Many sites only accept submissions via web forms

The tool will log these and provide URLs for manual submission.

## Expanding the Database

To add new contacts, edit the `initialize_contacts()` method or manually add to the JSON file:

```python
Contact("New Publication", "publication",
       email="editor@newpub.com",
       description="Emerging music publication",
       genre_focus=["electronic", "experimental"])
```

## Legal & Ethics

- All outreach is opt-in with clear unsubscribe options
- Emails include full contact information
- Rate limiting prevents spam-like behavior  
- Content is personalized and relevant
- Respects publication submission guidelines

## Support

For questions or issues:
- Email: team@nullrecords.com
- Website: https://nullrecords.com
- Check logs in `outreach.log`

---

**Note**: This tool handles the technical side of outreach. Building relationships with the music industry still requires genuine engagement, quality music, and professional follow-through! 🎶
