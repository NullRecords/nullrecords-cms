# Streamlined News Monitoring System

## Overview

The streamlined news monitoring system focuses on reliable, tested sources that consistently provide results without timeouts or connection issues. This approach prioritizes quality and reliability over quantity.

## Current Reliable Sources

### ✅ Tested & Working Sources

1. **Google Spotify Playlists**
   - Search: Google site search for Spotify playlists
   - Focus: Playlist inclusions and features
   - Reliability: Excellent

2. **Google Apple Music Playlists**
   - Search: Google site search for Apple Music playlists
   - Focus: Apple Music playlist features
   - Reliability: Excellent

3. **Google YouTube Playlists**
   - Search: Google site search for YouTube playlists
   - Focus: YouTube playlist inclusions
   - Reliability: Excellent

4. **Bandcamp Search**
   - Search: Direct Bandcamp search
   - Focus: Artist pages, album features
   - Reliability: Very Good

5. **SoundCloud Search**
   - Search: Direct SoundCloud search
   - Focus: Track uploads, playlist inclusions
   - Reliability: Very Good

6. **Reddit LoFi Community**
   - Search: Reddit /r/LofiHipHop search
   - Focus: Community discussions, playlist shares
   - Reliability: Good

7. **DuckDuckGo Playlist Search**
   - Search: DuckDuckGo with playlist keywords
   - Focus: Alternative search engine results
   - Reliability: Good

## Performance Metrics

### Recent Test Results (September 11, 2025)
- **Sources Tested**: 7/7 working (100% success rate)
- **Average Response Time**: ~2-3 seconds per source
- **Articles Found**: 2 new articles in single collection run
- **No Timeouts**: All sources responded within 10-second limit
- **No Failed Sources**: Zero sources marked as failed

### Collection Results
- **Total Articles**: 50 articles in database
- **New Articles Found**: 2 in most recent run
- **Search Coverage**: 6 artists × 7 sources = 42 searches per collection
- **Processing Time**: ~2 minutes for full collection

## Enhanced Confidence Scoring

### Scoring Algorithm (0.0 - 1.0 scale)

```
Base Score:
- Artist name in content: +0.6
- Artist name in title: +0.3

Playlist Keywords (+0.4 max):
- "playlist", "featured in", "added to", "curated"
- "spotify playlist", "lofi playlist", "study playlist"

Music Keywords (+0.2 max):
- "music", "album", "track", "song", "artist"
- "electronic", "lofi", "jazz", "stream"

Penalties:
- Spam indicators: ×0.1 (severe penalty)
- Lorem ipsum, fake content: ×0.1
```

### Status Classification
- **✅ Verified** (>0.8 confidence): High confidence, auto-approved
- **❓ Needs Verification** (0.4-0.8 confidence): Moderate confidence, human review
- **❌ Rejected** (<0.4 confidence): Low confidence, filtered out

## Potential Additional Sources

### Phase 2 Expansion (To Test)
```python
# Additional sources to test for Phase 2
additional_sources = [
    {
        "name": "Last.fm Artist Search",
        "search_url": "https://www.last.fm/search/artists?q={query}",
        "type": "music_database"
    },
    {
        "name": "Discogs Search",
        "search_url": "https://www.discogs.com/search/?q={query}&type=all",
        "type": "music_database"
    },
    {
        "name": "MusicBrainz",
        "search_url": "https://musicbrainz.org/search?query={query}&type=artist",
        "type": "database"
    },
    {
        "name": "Reddit Ambient Music",
        "search_url": "https://www.reddit.com/r/ambientmusic/search/?q={query}",
        "type": "social"
    }
]
```

### Previously Problematic Sources (Avoid)
- ❌ Playlist Push (gzip decompression errors)
- ❌ Indiemono (connection refused)
- ❌ Stereogum (timeout issues)
- ❌ Earmilk (timeout issues)
- ❌ Dancing Astronaut (timeout issues)

## Usage Instructions

### Basic Commands
```bash
# Test all sources for connectivity
python3 scripts/news_monitor_streamlined.py --test

# Collect news with default limit (2 per artist)
python3 scripts/news_monitor_streamlined.py --collect

# Collect with custom limit
python3 scripts/news_monitor_streamlined.py --collect --limit 3
```

### Integration with Main System
The streamlined monitor can be used alongside or as a replacement for the main news monitor:

```bash
# Use streamlined for reliable daily collection
python3 scripts/news_monitor_streamlined.py --collect --limit 2

# Use main system for comprehensive but slower searches
python3 scripts/news_monitor.py --collect --limit 1
```

## Monitoring & Maintenance

### Daily Operations
1. **Automated Collection**: Run streamlined version for daily reliable collection
2. **Source Health Check**: Weekly testing of all sources with `--test` flag
3. **Performance Monitoring**: Track response times and success rates
4. **Database Growth**: Monitor article database size and quality

### Quality Assurance
- **Confidence Threshold**: 0.4 minimum for inclusion
- **Duplicate Detection**: Title + source matching
- **Spam Filtering**: Multiple spam indicators checked
- **Manual Review**: Articles with 0.4-0.8 confidence require verification

## Technical Implementation

### Rate Limiting
- 1-3 second delays between requests
- Conservative timeout (10 seconds)
- Identity encoding to avoid compression issues

### Error Handling
- Failed sources marked and skipped in subsequent runs
- Graceful degradation when sources are unavailable
- Detailed logging for troubleshooting

### Data Management
- JSON-based article storage
- Incremental additions to existing database
- Automatic ID generation using content hash

## Future Enhancements

### Planned Improvements
1. **Source Rotation**: Gradually test and add new reliable sources
2. **API Integration**: Add official APIs where available (Spotify, Last.fm)
3. **Machine Learning**: Improve confidence scoring with ML models
4. **Real-time Monitoring**: WebSocket connections for real-time updates

### Integration Opportunities
- **Daily Reports**: Include streamlined results in email summaries
- **Website Updates**: Auto-populate news sections with verified articles
- **Social Media**: Share high-confidence playlist discoveries
- **Analytics**: Track playlist inclusion trends over time

This streamlined approach ensures reliable, consistent news discovery while maintaining the quality standards required for authentic music industry monitoring.
