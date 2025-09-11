# News Sources Expansion

## Overview

This document details the comprehensive expansion of news monitoring sources for NullRecords' automated discovery system. The system now monitors 50+ sources across multiple categories to find legitimate playlist placements, reviews, and mentions of NullRecords artists.

## Source Categories

### 1. Music Publications & Reviews
- **Pitchfork** - Leading indie music publication
- **The Fader** - Contemporary music and culture
- **Stereogum** - Independent music blog
- **Consequence of Sound** - Music news and reviews
- **Line of Best Fit** - UK-based music publication

### 2. Playlist Curators & Aggregators
- **Playlist Push** - Playlist submission platform
- **SubmitHub** - Music submission service
- **Indiemono** - Independent music platform
- **8Tracks** - User-generated playlists
- **Soundplate** - Music discovery platform

### 3. Music Discovery Platforms
- **Last.fm** - Music database and recommendations
- **RateYourMusic** - Community music database
- **Discogs** - Music marketplace and database
- **MusicBrainz** - Open music encyclopedia
- **AllMusic** - Comprehensive music database

### 4. Streaming & Distribution Platforms
- **SoundCloud** - Audio sharing platform
- **Spotify** - Music streaming service
- **Bandcamp** - Independent music platform
- **YouTube Music** - Google's music service
- **Audiomack** - Hip-hop focused streaming
- **Mixcloud** - DJ mix platform
- **ReverbNation** - Artist platform
- **Jamendo** - Free music platform

### 5. Electronic & Genre-Specific Publications
- **XLR8R** - Electronic music magazine
- **Resident Advisor** - Electronic music platform
- **Attack Magazine** - Electronic music production
- **Dancing Astronaut** - Electronic music blog
- **EDM.com** - Electronic dance music news
- **Your EDM** - Electronic music blog

### 6. Music Blogs & Influencers
- **Indie Shuffle** - Music discovery blog
- **Earmilk** - Music blog and playlist curator
- **This Song Is Sick** - Electronic music blog
- **Run The Trap** - Trap and electronic music
- **Obscure Sound** - Indie music blog

### 7. YouTube Channels & Influencers
- **Majestic Casual** - Chill electronic music channel
- **ChillHop Music** - Lo-fi hip hop channel
- **YouTube General Search** - Broad video platform search
- **Lofi Hip Hop Radio** - Genre-specific searches

### 8. Social Media Platforms
- **TikTok** - Short-form video platform
- **Twitter** - Microblogging platform
- **Instagram** - Photo and video sharing
- **Reddit** - Community discussions (LoFi, Ambient, Electronic Music)

### 9. News Aggregators
- **Google News** - News aggregation service
- **Hype Machine** - Music blog aggregator
- **Music News Net** - Music industry news
- **Prefix Magazine** - Alternative music magazine

### 10. Specialized Search Strategies
- **Spotify Playlist Search via Google** - Targeted playlist discovery
- **Apple Music Playlist Search** - Apple's playlist ecosystem
- **YouTube Playlist Search** - Video playlist discovery

## Enhanced Confidence Scoring

The system now uses sophisticated scoring to distinguish between:

### High-Value Content (Confidence Boost)
- **Playlist Features**: "featured in", "added to", "curated playlist"
- **Influencer Mentions**: "recommended by", "curator pick", "handpicked"
- **Editorial Content**: "new music friday", "weekly playlist", "editor choice"
- **Quality Publications**: "review", "interview", "feature article"

### Platform Legitimacy Indicators
- **Official Platforms**: spotify:, apple music:, youtube:, soundcloud:
- **Curator Mentions**: "tastemaker", "influencer", "championed by"
- **Discovery Context**: "fresh finds", "hidden gems", "underground gems"

### Content Filtering
- **Spam Detection**: lorem ipsum, example.com, fake content
- **User Account Filtering**: "my playlist", "personal mix", amateur content
- **Quality Assurance**: Distinguishes editorial content from user uploads

## Search Strategy

### Multi-Tier Approach
1. **Tier 1**: High-authority music publications and official platforms
2. **Tier 2**: Specialized genre blogs and playlist curators
3. **Tier 3**: Social media and community platforms
4. **Tier 4**: General search engines with targeted queries

### Rate Limiting & Ethics
- 2-5 second delays between requests
- Respectful crawling practices
- User-Agent headers for transparency
- Timeout protection (10 seconds max)

### Verification Workflow
- **Automated Scoring**: 0.0-1.0 confidence rating
- **Status Classification**:
  - `verified` (>0.8 confidence)
  - `needs_verification` (0.3-0.8 confidence)
  - `rejected` (<0.3 confidence)
- **Human Review**: Daily email summaries for uncertain content

## Expected Outcomes

### Playlist Discovery
- Spotify playlist inclusions
- Apple Music editorial playlists
- YouTube music channel features
- Independent curator selections

### Publication Features
- Album/track reviews
- Artist interviews
- News coverage
- Blog mentions

### Social Media Buzz
- TikTok music usage
- Twitter mentions
- Instagram posts
- Reddit discussions

### Industry Recognition
- Playlist submission acceptances
- Influencer endorsements
- Curator recommendations
- Editorial selections

## Monitoring & Maintenance

### Daily Operations
- Automated searches across all sources
- Confidence scoring and filtering
- Email summaries with verification requests
- Database updates and archiving

### Quality Control
- Regular source effectiveness review
- Confidence threshold adjustments
- New source integration
- Spam/fake content elimination

### Performance Metrics
- Sources yielding high-quality results
- Confidence score distribution
- Verification accuracy rates
- Discovery volume trends

## Usage Instructions

```bash
# Run with expanded source collection
python3 scripts/news_monitor.py --collect --limit 3

# Test specific source categories
python3 scripts/news_monitor.py --collect --sources playlist_curator --limit 2

# Generate verification report
python3 scripts/news_monitor.py --verification-report
```

## Integration with Daily Reports

The expanded monitoring system integrates with the daily report system to:
- Include verification requests in email summaries
- Track approval/rejection patterns
- Adjust confidence thresholds based on feedback
- Maintain quality over quantity focus

## Future Expansions

### Potential Additional Sources
- Regional music publications
- Genre-specific communities
- Emerging social platforms
- International music databases
- Podcast platforms
- Music festival lineups

### API Integrations
- Spotify Web API for playlist data
- Last.fm API for scrobble data
- YouTube Data API for video metrics
- SoundCloud API for track data

This comprehensive approach ensures maximum coverage while maintaining quality and relevance for NullRecords' music discovery needs.
