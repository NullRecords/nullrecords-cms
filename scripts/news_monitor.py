#!/usr/bin/env python3
"""
NullRecords News Monitoring System
=================================

Automated news collection, management, and website integration for NullRecords artists.
Searches for reviews, posts, mentions, and new releases across the web including 
SoundCloud and Spotify.

Usage: python news_monitor.py [--collect] [--generate] [--update-site]
"""

import json
import time
import random
import re
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
import logging
from dataclasses import dataclass, asdict, field
from pathlib import Path
import argparse
from urllib.parse import urljoin, urlparse, quote
import hashlib

# Load environment variables
try:
    from dotenv import load_dotenv
    if os.path.exists('.env'):
        load_dotenv('.env')
        logging.info("✅ Environment variables loaded from .env file")
except ImportError:
    logging.warning("⚠️  python-dotenv not installed - using system environment variables only")

# Optional dependencies
try:
    import requests
    from bs4 import BeautifulSoup
    SCRAPING_AVAILABLE = True
except ImportError:
    SCRAPING_AVAILABLE = False
    logging.warning("⚠️  Scraping libraries not available - install requests and beautifulsoup4")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('news_monitor.log'),
        logging.StreamHandler()
    ]
)

@dataclass
class NewsArticle:
    """News article data structure"""
    id: str
    title: str
    content: str
    source: str
    url: str
    author: Optional[str] = None
    published_date: Optional[str] = None
    discovered_date: str = field(default_factory=lambda: datetime.now().isoformat())
    artist_mentioned: List[str] = field(default_factory=list)
    sentiment: str = "neutral"  # positive, negative, neutral
    article_type: str = "review"  # review, news, interview, feature
    status: str = "new"  # new, processed, published, needs_verification, verified
    tags: List[str] = field(default_factory=list)
    excerpt: Optional[str] = None
    
    def __post_init__(self):
        if not self.id:
            self.id = hashlib.md5(f"{self.title}{self.url}{self.source}".encode()).hexdigest()[:12]
        if not self.excerpt and self.content:
            self.excerpt = self.content[:200] + "..." if len(self.content) > 200 else self.content

class NewsMonitor:
    """Main news monitoring and management system"""
    
    def __init__(self):
        self.articles: List[NewsArticle] = []
        self.data_file = "news_articles.json"
        self.artists = [
            "NullRecords",
            "My Evil Robot Army", 
            "MERA",
            "Null Records",
            "My Evil Robot Army - Space Jazz",
            "Evil Robot Army"
        ]
        self.search_sources = self._initialize_sources()
        self.load_articles()
        
    def _initialize_sources(self) -> List[Dict]:
        """Initialize news sources for monitoring real content"""
        return [
            # Music Publications & Reviews
            {
                "name": "Pitchfork",
                "search_url": "https://pitchfork.com/search/?query={query}",
                "type": "publication",
                "selector": ".search-results-list article"
            },
            {
                "name": "The Fader",
                "search_url": "https://www.thefader.com/search?q={query}",
                "type": "publication", 
                "selector": ".post-item"
            },
            {
                "name": "Bandcamp Daily",
                "search_url": "https://daily.bandcamp.com/?s={query}",
                "type": "publication",
                "selector": ".post"
            },
            {
                "name": "AllMusic",
                "search_url": "https://www.allmusic.com/search/all/{query}",
                "type": "database",
                "selector": ".search-result"
            },
            # Focus on sites that discuss playlists and music discovery
            {
                "name": "Google Site Search for Spotify",
                "search_url": "https://www.google.com/search?q=site:open.spotify.com+{query}+playlist",
                "type": "playlist",
                "selector": ".g"
            },
            # Music Discovery & Playlist Sites
            {
                "name": "MusicBrainz",
                "search_url": "https://musicbrainz.org/search?query={query}&type=artist",
                "type": "database",
                "selector": ".search-result"
            },
            # Social Media & Communities
            {
                "name": "Reddit LoFi",
                "search_url": "https://www.reddit.com/r/LofiHipHop/search/?q={query}",
                "type": "social",
                "selector": ".Post"
            },
            {
                "name": "Reddit Ambient",
                "search_url": "https://www.reddit.com/r/ambientmusic/search/?q={query}",
                "type": "social",
                "selector": ".Post"
            },
            {
                "name": "Reddit Electronic Music",
                "search_url": "https://www.reddit.com/r/electronicmusic/search/?q={query}",
                "type": "social",
                "selector": ".Post"
            },
            # Alternative Search Engines for Music
            {
                "name": "DuckDuckGo Music Search",
                "search_url": "https://duckduckgo.com/?q={query}+spotify+playlist",
                "type": "search",
                "selector": ".result"
            },
            {
                "name": "Google News",
                "search_url": "https://news.google.com/search?q={query}",
                "type": "aggregator",
                "selector": "article"
            },
            {
                "name": "Hype Machine",
                "search_url": "https://hypem.com/search/{query}",
                "type": "aggregator",
                "selector": ".track-item"
            },
            # Streaming Platforms
            {
                "name": "SoundCloud",
                "search_url": "https://soundcloud.com/search?q={query}",
                "type": "streaming",
                "selector": ".soundList__item",
                "api_endpoint": "https://api.soundcloud.com/tracks"
            },
            {
                "name": "Spotify Web",
                "search_url": "https://open.spotify.com/search/{query}",
                "type": "streaming", 
                "selector": "[data-testid='tracklist-row']",
                "api_endpoint": "https://api.spotify.com/v1/search"
            },
            {
                "name": "Bandcamp",
                "search_url": "https://bandcamp.com/search?q={query}",
                "type": "streaming",
                "selector": ".searchresult"
            },
            {
                "name": "YouTube Music Search",
                "search_url": "https://music.youtube.com/search?q={query}",
                "type": "streaming",
                "selector": ".ytmusic-shelf-renderer"
            }
        ]
    
    def load_articles(self):
        """Load existing articles from JSON file"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.articles = [NewsArticle(**article) for article in data]
                logging.info(f"📰 Loaded {len(self.articles)} existing articles")
            except Exception as e:
                logging.error(f"❌ Error loading articles: {e}")
                self.articles = []
        else:
            self.articles = []
    
    def save_articles(self):
        """Save articles to JSON file"""
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump([asdict(article) for article in self.articles], f, indent=2, ensure_ascii=False)
            logging.info(f"💾 Saved {len(self.articles)} articles")
        except Exception as e:
            logging.error(f"❌ Error saving articles: {e}")
    
    def search_for_mentions(self, artist: str, limit: int = 5) -> List[NewsArticle]:
        """Search web for mentions of artist"""
        if not SCRAPING_AVAILABLE:
            logging.warning("⚠️  Scraping not available - install requests and beautifulsoup4")
            return []
        
        found_articles = []
        
        for source in self.search_sources:  # Search all real sources
            try:
                logging.info(f"🔍 Searching {source['name']} for '{artist}'...")
                
                # Format search query
                query = quote(artist)
                search_url = source['search_url'].format(query=query)
                
                # Add headers to appear more like a browser
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                }
                
                # Make request with timeout
                response = requests.get(search_url, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    # Parse with BeautifulSoup
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Generic article extraction (would need customization per site)
                    articles = soup.find_all(['article', 'div'], class_=re.compile(r'(post|article|item|result)'))[:limit]
                    
                    for article_elem in articles:
                        try:
                            # Extract basic info (simplified)
                            title_elem = article_elem.find(['h1', 'h2', 'h3', 'h4', 'a'])
                            title = title_elem.get_text(strip=True) if title_elem else "No title found"
                            
                            # Check if content is relevant and verify it's about us
                            content_text = article_elem.get_text(strip=True)
                            confidence_score = self._calculate_relevance_confidence(title, content_text, artist)
                            
                            if confidence_score > 0.3:  # Only include if reasonably confident
                                # Try to extract actual article URL
                                link_elem = article_elem.find('a', href=True)
                                article_url = link_elem['href'] if link_elem else search_url
                                
                                # Make URL absolute if relative
                                if article_url.startswith('/'):
                                    base_url = f"{urlparse(search_url).scheme}://{urlparse(search_url).netloc}"
                                    article_url = urljoin(base_url, article_url)
                                
                                # Determine status based on confidence
                                status = "verified" if confidence_score > 0.8 else "needs_verification"
                                
                                # Determine article type based on content
                                article_type = "news"
                                title_lower = title.lower()
                                content_lower = content_text.lower()
                                
                                if any(word in title_lower for word in ["playlist", "featured in", "added to"]):
                                    article_type = "playlist"
                                elif any(word in title_lower for word in ["review", "rating", "critique"]):
                                    article_type = "review"
                                elif any(word in content_lower for word in ["playlist", "curated", "spotify"]):
                                    article_type = "playlist"
                                elif any(word in content_lower for word in ["interview", "talks with", "speaks to"]):
                                    article_type = "interview"
                                
                                article = NewsArticle(
                                    id="",  # Will be generated
                                    title=title,
                                    content=content_text[:500],
                                    source=source['name'],
                                    url=article_url,
                                    artist_mentioned=[artist],
                                    article_type=article_type,
                                    status=status
                                )
                                found_articles.append(article)
                                
                                confidence_emoji = "✅" if confidence_score > 0.8 else "❓" if confidence_score > 0.6 else "⚠️"
                                logging.info(f"{confidence_emoji} Found ({confidence_score:.2f}): {title[:50]}...")
                        
                        except Exception as e:
                            logging.debug(f"Error parsing article: {e}")
                            continue
                
                # Rate limiting
                time.sleep(random.uniform(2, 5))
                
            except Exception as e:
                logging.error(f"❌ Error searching {source['name']}: {e}")
                continue
        
        return found_articles

    def _calculate_relevance_confidence(self, title: str, content: str, artist: str) -> float:
        """Calculate confidence that content is actually about our artist"""
        confidence = 0.0
        
        # Combine title and content for analysis
        text = f"{title} {content}".lower()
        artist_lower = artist.lower()
        
        # Base score for artist name mention
        if artist_lower in text:
            confidence += 0.5
        
        # Higher score if artist name is in title
        if artist_lower in title.lower():
            confidence += 0.3
        
        # Look for music-related keywords
        music_keywords = [
            'music', 'album', 'track', 'song', 'release', 'artist', 'musician',
            'band', 'playlist', 'review', 'listen', 'stream', 'electronic',
            'lofi', 'lo-fi', 'jazz', 'ambient', 'instrumental', 'experimental'
        ]
        
        music_score = sum(1 for keyword in music_keywords if keyword in text) / len(music_keywords)
        confidence += music_score * 0.3
        
        # Specific to our label and artists
        nullrecords_keywords = [
            'nullrecords', 'null records', 'my evil robot army', 'mera',
            'space jazz', 'explorations in blue', 'electronic jazz fusion'
        ]
        
        # Playlist-specific keywords that indicate real playlist placements
        playlist_keywords = [
            'playlist', 'featured in', 'added to', 'curated', 'included in',
            'now playing', 'discover', 'spotify playlist', 'lofi playlist',
            'chill playlist', 'study playlist', 'ambient playlist'
        ]
        
        specific_score = sum(1 for keyword in nullrecords_keywords if keyword in text) / len(nullrecords_keywords)
        confidence += specific_score * 0.4
        
        # Bonus for playlist-related content
        playlist_score = sum(1 for keyword in playlist_keywords if keyword in text) / len(playlist_keywords)
        confidence += playlist_score * 0.3
        
        # Penalty for generic/spam content and user accounts
        spam_indicators = [
            'lorem ipsum', 'example.com', 'test article', 'placeholder',
            'buy now', 'click here', 'advertisement', 'user profile',
            'personal account', 'my music', 'follow me', 'check out my'
        ]
        
        if any(indicator in text for indicator in spam_indicators):
            confidence *= 0.1  # Heavily penalize spam
        
        # Cap at 1.0
        return min(confidence, 1.0)

    def get_verification_summary(self) -> Dict:
        """Get summary of articles needing verification for daily report"""
        needs_verification = [a for a in self.articles if a.status == "needs_verification"]
        verified = [a for a in self.articles if a.status == "verified"]
        
        return {
            "needs_verification": len(needs_verification),
            "verified": len(verified),
            "pending_articles": [
                {
                    "title": article.title,
                    "source": article.source,
                    "url": article.url,
                    "artist": ", ".join(article.artist_mentioned),
                    "type": article.article_type,
                    "excerpt": article.excerpt
                }
                for article in needs_verification[:5]  # Show top 5 needing verification
            ]
        }
    
    def collect_news(self, max_per_artist: int = 3):
        """Collect news for all artists"""
        logging.info("🔍 Starting news collection...")
        
        new_articles = []
        
        for artist in self.artists:
            logging.info(f"📰 Collecting news for: {artist}")
            articles = self.search_for_mentions(artist, limit=max_per_artist)
            
            for article in articles:
                # Check if we already have this article
                existing = next((a for a in self.articles if a.title == article.title and a.source == article.source), None)
                if not existing:
                    new_articles.append(article)
                    logging.info(f"✅ New article: {article.title[:50]}...")
        
        # Only add real articles - no more mock content
        self.articles.extend(new_articles)
        self.save_articles()
        
        # Send email notifications for new articles
        if new_articles:
            self._send_new_article_notification(new_articles)
        
        logging.info(f"🎉 Collected {len(new_articles)} new real articles")
        return len(new_articles)
    
    def _send_new_article_notification(self, new_articles: List[NewsArticle]):
        """Send email notification for new articles found"""
        try:
            # Get SMTP credentials from environment
            smtp_server = os.getenv('SMTP_SERVER')
            smtp_port = int(os.getenv('SMTP_PORT', '587'))
            smtp_username = os.getenv('SMTP_USER')  # Use same variable as outreach system
            smtp_password = os.getenv('SMTP_PASSWORD')
            sender_email = os.getenv('SENDER_EMAIL')
            notification_email = os.getenv('BCC_EMAIL')
            
            if not smtp_username or not smtp_password or not smtp_server or not sender_email or not notification_email:
                logging.warning("⚠️  SMTP credentials not configured - skipping email notification")
                logging.warning("Required: SMTP_SERVER, SMTP_USER, SMTP_PASSWORD, SENDER_EMAIL, BCC_EMAIL")
                return
            
            # Create email content
            subject = f"🔥 {len(new_articles)} New Articles Found - NullRecords News Monitor"
            
            # Create HTML email body
            html_body = """
            <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: linear-gradient(135deg, #1a1a2e, #16213e); padding: 20px; border-radius: 10px;">
                    <h2 style="color: #00ffff; margin-bottom: 20px;">🔥 New Articles Discovered</h2>
                    <p style="color: #ffffff; margin-bottom: 20px;">
                        The NullRecords News Monitor has discovered <strong>{}</strong> new articles about our artists!
                    </p>
            """.format(len(new_articles))
            
            for article in new_articles:
                artists_str = ", ".join(article.artist_mentioned)
                sentiment_icon = "🔥" if article.sentiment == "positive" else "⚠️" if article.sentiment == "negative" else "📰"
                
                html_body += f"""
                    <div style="background: rgba(255,255,255,0.1); padding: 15px; margin: 10px 0; border-radius: 8px; border-left: 4px solid #00ffff;">
                        <h3 style="color: #00ffff; margin: 0 0 10px 0;">{sentiment_icon} {article.title}</h3>
                        <p style="color: #cccccc; margin: 5px 0;"><strong>Source:</strong> {article.source}</p>
                        <p style="color: #cccccc; margin: 5px 0;"><strong>Artists:</strong> {artists_str}</p>
                        <p style="color: #cccccc; margin: 5px 0;"><strong>Type:</strong> {article.article_type.title()}</p>
                        <p style="color: #dddddd; margin: 10px 0;">{article.excerpt or article.content[:200]}...</p>
                        <a href="{article.url}" style="color: #ff0080; text-decoration: none;">Read More →</a>
                    </div>
                """
            
            html_body += """
                    <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid rgba(255,255,255,0.2);">
                        <p style="color: #cccccc; text-align: center; margin: 0;">
                            <a href="https://nullrecords.com/news/" style="color: #00ffff; text-decoration: none;">
                                View All Articles on NullRecords.com →
                            </a>
                        </p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Create and send email
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = sender_email
            msg['To'] = notification_email
            
            # Add HTML content
            html_part = MIMEText(html_body, 'html')
            msg.attach(html_part)
            
            # Send via SMTP
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(smtp_username, smtp_password)
                server.send_message(msg)
            
            logging.info(f"📧 Sent new article notification to {notification_email}")
            
        except Exception as e:
            logging.error(f"❌ Failed to send email notification: {e}")
    
    def monitor_streaming_releases(self):
        """Monitor streaming platforms for new releases"""
        logging.info("🎵 Monitoring streaming platforms for new releases...")
        
        new_releases = []
        
        for artist in self.artists:
            # Check SoundCloud
            soundcloud_releases = self._check_soundcloud_releases(artist)
            new_releases.extend(soundcloud_releases)
            
            # Check Bandcamp
            bandcamp_releases = self._check_bandcamp_releases(artist)
            new_releases.extend(bandcamp_releases)
            
            # Rate limiting between artists
            time.sleep(random.uniform(3, 6))
        
        # Add new releases as articles
        for release in new_releases:
            existing = next((a for a in self.articles if a.title == release.title and a.source == release.source), None)
            if not existing:
                self.articles.append(release)
                logging.info(f"🎵 New release found: {release.title}")
        
        if new_releases:
            self.save_articles()
            self._send_new_release_notification(new_releases)
        
        return len(new_releases)
    
    def _check_soundcloud_releases(self, artist: str) -> List[NewsArticle]:
        """Check SoundCloud for new releases"""
        releases = []
        
        if not SCRAPING_AVAILABLE:
            return releases
        
        try:
            query = quote(artist)
            search_url = f"https://soundcloud.com/search?q={query}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            
            response = requests.get(search_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for recent tracks (simplified extraction)
                track_elements = soup.find_all('div', class_=re.compile(r'sound.*item|track.*item'))[:3]
                
                for track_elem in track_elements:
                    try:
                        title_elem = track_elem.find(['h2', 'h3', 'a'])
                        if title_elem and artist.lower() in title_elem.get_text().lower():
                            title = title_elem.get_text(strip=True)
                            
                            release = NewsArticle(
                                id="",
                                title=f"New SoundCloud Release: {title}",
                                content=f"New track '{title}' by {artist} has been released on SoundCloud. Check out this latest release from the NullRecords artist.",
                                source="SoundCloud",
                                url=search_url,
                                artist_mentioned=[artist],
                                article_type="release",
                                sentiment="positive",
                                tags=["release", "soundcloud", "new music"]
                            )
                            releases.append(release)
                            
                    except Exception as e:
                        logging.debug(f"Error parsing SoundCloud track: {e}")
                        continue
                        
        except Exception as e:
            logging.error(f"❌ Error checking SoundCloud for {artist}: {e}")
        
        return releases
    
    def _check_bandcamp_releases(self, artist: str) -> List[NewsArticle]:
        """Check Bandcamp for new releases"""
        releases = []
        
        if not SCRAPING_AVAILABLE:
            return releases
        
        try:
            query = quote(artist)
            search_url = f"https://bandcamp.com/search?q={query}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            
            response = requests.get(search_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for recent releases
                release_elements = soup.find_all('div', class_=re.compile(r'searchresult|result.*item'))[:3]
                
                for release_elem in release_elements:
                    try:
                        title_elem = release_elem.find(['div', 'a'], class_=re.compile(r'heading|title'))
                        if title_elem and artist.lower() in release_elem.get_text().lower():
                            title = title_elem.get_text(strip=True)
                            
                            release = NewsArticle(
                                id="",
                                title=f"New Bandcamp Release: {title}",
                                content=f"New release '{title}' by {artist} is now available on Bandcamp. This latest offering from the NullRecords catalog is ready for streaming and purchase.",
                                source="Bandcamp",
                                url=search_url,
                                artist_mentioned=[artist],
                                article_type="release",
                                sentiment="positive",
                                tags=["release", "bandcamp", "new music"]
                            )
                            releases.append(release)
                            
                    except Exception as e:
                        logging.debug(f"Error parsing Bandcamp release: {e}")
                        continue
                        
        except Exception as e:
            logging.error(f"❌ Error checking Bandcamp for {artist}: {e}")
        
        return releases
    
    def _send_new_release_notification(self, new_releases: List[NewsArticle]):
        """Send email notification for new releases found"""
        try:
            # Get SMTP credentials from environment
            smtp_server = os.getenv('SMTP_SERVER')
            smtp_port = int(os.getenv('SMTP_PORT', '587'))
            smtp_username = os.getenv('SMTP_USER')  # Use same variable as outreach system
            smtp_password = os.getenv('SMTP_PASSWORD')
            sender_email = os.getenv('SENDER_EMAIL')
            notification_email = os.getenv('BCC_EMAIL')
            
            if not smtp_username or not smtp_password or not smtp_server or not sender_email or not notification_email:
                logging.warning("⚠️  SMTP credentials not configured - skipping release notification")
                logging.warning("Required: SMTP_SERVER, SMTP_USER, SMTP_PASSWORD, SENDER_EMAIL, BCC_EMAIL")
                return
            
            # Create email content
            subject = f"🎵 {len(new_releases)} New Releases Detected - NullRecords Music Monitor"
            
            # Create HTML email body
            html_body = """
            <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: linear-gradient(135deg, #1a1a2e, #16213e); padding: 20px; border-radius: 10px;">
                    <h2 style="color: #ff0080; margin-bottom: 20px;">🎵 New Releases Detected</h2>
                    <p style="color: #ffffff; margin-bottom: 20px;">
                        The NullRecords Music Monitor has discovered <strong>{}</strong> new releases from our artists!
                    </p>
            """.format(len(new_releases))
            
            for release in new_releases:
                artists_str = ", ".join(release.artist_mentioned)
                platform_icon = "🎧" if release.source == "SoundCloud" else "🎼" if release.source == "Bandcamp" else "🎵"
                
                html_body += f"""
                    <div style="background: rgba(255,0,128,0.1); padding: 15px; margin: 10px 0; border-radius: 8px; border-left: 4px solid #ff0080;">
                        <h3 style="color: #ff0080; margin: 0 0 10px 0;">{platform_icon} {release.title}</h3>
                        <p style="color: #cccccc; margin: 5px 0;"><strong>Platform:</strong> {release.source}</p>
                        <p style="color: #cccccc; margin: 5px 0;"><strong>Artist:</strong> {artists_str}</p>
                        <p style="color: #dddddd; margin: 10px 0;">{release.content[:200]}...</p>
                        <a href="{release.url}" style="color: #00ffff; text-decoration: none;">Listen Now →</a>
                    </div>
                """
            
            html_body += """
                    <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid rgba(255,255,255,0.2);">
                        <p style="color: #cccccc; text-align: center; margin: 0;">
                            <a href="https://nullrecords.com/news/" style="color: #ff0080; text-decoration: none;">
                                Promote These Releases →
                            </a>
                        </p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Create and send email
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = sender_email
            msg['To'] = notification_email
            
            # Add HTML content
            html_part = MIMEText(html_body, 'html')
            msg.attach(html_part)
            
            # Send via SMTP
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(smtp_username, smtp_password)
                server.send_message(msg)
            
            logging.info(f"📧 Sent new release notification to {notification_email}")
            
        except Exception as e:
            logging.error(f"❌ Failed to send release notification: {e}")
    

    
    def generate_news_pages(self):
        """Generate HTML pages for news articles"""
        logging.info("📄 Generating news pages...")
        
        # Create news directory
        news_dir = Path("news")
        news_dir.mkdir(exist_ok=True)
        
        # Generate individual article pages
        for article in self.articles:
            self._generate_article_page(article, news_dir)
        
        # Generate news index page
        self._generate_news_index(news_dir)
        
        logging.info(f"✅ Generated {len(self.articles)} article pages and index")
    
    def _generate_article_page(self, article: NewsArticle, news_dir: Path):
        """Generate individual article page"""
        filename = f"{article.id}.html"
        filepath = news_dir / filename
        
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{article.title} - NullRecords News</title>
    <link rel="stylesheet" href="/assets/css/tailwind.css">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Press+Start+2P&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
    <link rel="icon" type="image/x-icon" href="/favicon.ico">
</head>
<body class="bg-dark-bg text-gray-100 font-mono">
    <!-- Header -->
    <nav class="border-b border-dark-border bg-dark-card/80 backdrop-blur-sm sticky top-0 z-50">
        <div class="container mx-auto px-4">
            <div class="flex items-center justify-between h-16">
                <div class="flex items-center">
                    <img src="/assets/logos/logo.png" alt="NullRecords Logo" class="h-10 w-auto animate-float">
                </div>
                <div class="flex items-center space-x-8">
                    <a href="/" class="text-cyber-blue hover:text-cyber-red transition-colors duration-300 text-sm font-pixel">HOME</a>
                    <a href="/news/" class="text-cyber-red text-sm font-pixel">NEWS</a>
                </div>
            </div>
        </div>
    </nav>

    <!-- Article Content -->
    <main class="container mx-auto px-4 py-12">
        <div class="max-w-4xl mx-auto">
            <!-- Breadcrumb -->
            <div class="mb-8">
                <a href="/" class="text-cyber-blue hover:text-cyber-red text-sm">HOME</a>
                <span class="text-gray-500 mx-2">/</span>
                <a href="/news/" class="text-cyber-blue hover:text-cyber-red text-sm">NEWS</a>
                <span class="text-gray-500 mx-2">/</span>
                <span class="text-gray-400 text-sm">{article.id}</span>
            </div>

            <!-- Article Header -->
            <header class="mb-8 retro-card p-8 rounded-lg">
                <div class="flex items-center gap-2 mb-4">
                    <span class="text-cyber-green font-pixel text-xs">[{article.article_type.upper()}]</span>
                    <span class="text-gray-500">•</span>
                    <span class="text-cyber-blue font-pixel text-xs">{article.source}</span>
                </div>
                
                <h1 class="font-pixel text-cyber-red text-xl md:text-2xl mb-4 leading-relaxed">
                    {article.title}
                </h1>
                
                <div class="flex flex-wrap gap-4 text-sm text-gray-400">
                    <span>📅 {datetime.fromisoformat(article.published_date or article.discovered_date).strftime('%Y-%m-%d') if article.published_date or article.discovered_date else 'Unknown date'}</span>
                    <span>🎵 {', '.join(article.artist_mentioned)}</span>
                    <span>📝 {article.sentiment.title()}</span>
                </div>
            </header>

            <!-- Article Content -->
            <article class="retro-card p-8 rounded-lg mb-8">
                <div class="prose prose-invert max-w-none">
                    <p class="text-gray-300 leading-relaxed mb-6">
                        {article.content}
                    </p>
                    
                    {f'<p class="text-sm text-gray-500 border-t border-dark-border pt-4"><strong>Source:</strong> <a href="{article.url}" target="_blank" rel="noopener" class="text-cyber-blue hover:text-cyber-red">{article.source}</a></p>' if article.url else ''}
                </div>
            </article>

            <!-- Related Articles -->
            <div class="retro-card p-6 rounded-lg">
                <h3 class="font-pixel text-cyber-blue text-sm mb-4">RELATED_ARTICLES.LOG</h3>
                <div class="space-y-2">
                    <a href="/news/" class="block text-cyber-green hover:text-cyber-red text-sm transition-colors">
                        → VIEW ALL NEWS ENTRIES
                    </a>
                    <a href="/" class="block text-cyber-green hover:text-cyber-red text-sm transition-colors">
                        → RETURN TO MAIN SYSTEM
                    </a>
                </div>
            </div>
        </div>
    </main>

    <!-- Footer -->
    <footer class="border-t border-dark-border bg-dark-card/50 py-8 mt-16">
        <div class="container mx-auto px-4 text-center">
            <p class="text-gray-500 text-sm font-pixel">
                © 2025 NULLRECORDS • THE INTERSECTION OF MUSIC, ART & TECHNOLOGY
            </p>
        </div>
    </footer>
</body>
</html>"""
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
    
    def _generate_news_index(self, news_dir: Path):
        """Generate news index page"""
        filepath = news_dir / "index.html"
        
        # Sort articles by date (newest first)
        sorted_articles = sorted(
            self.articles, 
            key=lambda x: x.published_date or x.discovered_date,
            reverse=True
        )
        
        # Generate article entries HTML
        articles_html = ""
        for article in sorted_articles:
            date_str = datetime.fromisoformat(article.published_date or article.discovered_date).strftime('%Y.%m.%d') if article.published_date or article.discovered_date else 'UNKNOWN'
            
            articles_html += f"""
                        <article class="border-b border-dark-border pb-6 mb-6">
                            <div class="flex items-center gap-2 mb-2">
                                <span class="text-cyber-green font-pixel text-xs">[{article.article_type.upper()}]</span>
                                <span class="text-gray-500">•</span>
                                <span class="text-cyber-blue font-pixel text-xs">{article.source}</span>
                                <span class="text-gray-500">•</span>
                                <span class="text-xs text-cyber-red">{date_str}</span>
                            </div>
                            
                            <h3 class="text-cyber-blue text-lg font-pixel mb-3 hover:text-cyber-red transition-colors">
                                <a href="/news/{article.id}.html">{article.title}</a>
                            </h3>
                            
                            <p class="text-gray-400 text-sm mb-3 leading-relaxed">
                                {article.excerpt or article.content[:150] + '...'}
                            </p>
                            
                            <div class="flex flex-wrap gap-3 text-xs">
                                <span class="text-gray-500">🎵 {', '.join(article.artist_mentioned)}</span>
                                <span class="text-gray-500">📝 {article.sentiment.title()}</span>
                                <a href="/news/{article.id}.html" class="text-cyber-green hover:text-cyber-red transition-colors">
                                    READ_MORE →
                                </a>
                            </div>
                        </article>"""
        
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>System Update Log - NullRecords News</title>
    <link rel="stylesheet" href="/assets/css/tailwind.css">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Press+Start+2P&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
    <link rel="icon" type="image/x-icon" href="/favicon.ico">
</head>
<body class="bg-dark-bg text-gray-100 font-mono">
    <!-- Header -->
    <nav class="border-b border-dark-border bg-dark-card/80 backdrop-blur-sm sticky top-0 z-50">
        <div class="container mx-auto px-4">
            <div class="flex items-center justify-between h-16">
                <div class="flex items-center">
                    <img src="/assets/logos/logo.png" alt="NullRecords Logo" class="h-10 w-auto animate-float">
                </div>
                <div class="flex items-center space-x-8">
                    <a href="/" class="text-cyber-blue hover:text-cyber-red transition-colors duration-300 text-sm font-pixel">HOME</a>
                    <a href="/news/" class="text-cyber-red text-sm font-pixel">NEWS</a>
                </div>
            </div>
        </div>
    </nav>

    <!-- News Content -->
    <main class="container mx-auto px-4 py-12">
        <div class="max-w-4xl mx-auto">
            <!-- Page Header -->
            <header class="retro-card p-8 rounded-lg mb-8">
                <h1 class="font-pixel text-cyber-red text-2xl md:text-3xl mb-4">
                    SYSTEM_UPDATE.LOG
                </h1>
                <p class="text-gray-400 text-sm leading-relaxed">
                    Latest news, reviews, and mentions from across the digital music landscape. 
                    Automated monitoring system tracking NullRecords artists and releases.
                </p>
                <div class="mt-4 text-xs text-cyber-green">
                    📡 LAST_SCAN: {datetime.now().strftime('%Y-%m-%d %H:%M')} • 
                    📰 TOTAL_ENTRIES: {len(self.articles)} • 
                    🔄 AUTO_UPDATE: ENABLED
                </div>
            </header>

            <!-- News Articles -->
            <div class="retro-card p-8 rounded-lg">
                <div class="space-y-8">
                    {articles_html}
                </div>
                
                {f'<div class="text-center py-8"><p class="text-gray-500 text-sm font-pixel">END_OF_LOG • {len(self.articles)} ENTRIES_DISPLAYED</p></div>' if self.articles else '<div class="text-center py-12"><p class="text-gray-500 font-pixel">NO_ENTRIES_FOUND • RUN_NEWS_SCAN</p></div>'}
            </div>

            <!-- System Info -->
            <div class="retro-card p-6 rounded-lg mt-8">
                <h3 class="font-pixel text-cyber-blue text-sm mb-4">SYSTEM_INFO.TXT</h3>
                <div class="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs text-gray-400">
                    <div>
                        <div class="text-cyber-green">MONITORED_ARTISTS:</div>
                        <div>• NullRecords</div>
                        <div>• My Evil Robot Army</div>
                        <div>• MERA</div>
                    </div>
                    <div>
                        <div class="text-cyber-green">SOURCE_TYPES:</div>
                        <div>• Music Publications</div>
                        <div>• Social Media</div>
                        <div>• Blog Networks</div>
                    </div>
                    <div>
                        <div class="text-cyber-green">UPDATE_FREQUENCY:</div>
                        <div>• Daily Automated Scans</div>
                        <div>• Real-time Processing</div>
                        <div>• Manual Override Available</div>
                    </div>
                </div>
            </div>
        </div>
    </main>

    <!-- Footer -->
    <footer class="border-t border-dark-border bg-dark-card/50 py-8 mt-16">
        <div class="container mx-auto px-4 text-center">
            <p class="text-gray-500 text-sm font-pixel">
                © 2025 NULLRECORDS • THE INTERSECTION OF MUSIC, ART & TECHNOLOGY
            </p>
        </div>
    </footer>
</body>
</html>"""
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
    
    def update_main_site_news(self):
        """Update the news section in index.html"""
        logging.info("🔄 Updating main site news section...")
        
        # Get latest 3 articles
        latest_articles = sorted(
            self.articles,
            key=lambda x: x.published_date or x.discovered_date,
            reverse=True
        )[:3]
        
        # Generate news HTML for main site
        news_html = ""
        for article in latest_articles:
            date_str = datetime.fromisoformat(article.published_date or article.discovered_date).strftime('%Y.%m.%d') if article.published_date or article.discovered_date else 'UNKNOWN'
            
            news_html += f"""
                        <article class="border-b border-dark-border pb-4">
                            <h4 class="text-cyber-green text-sm mb-2">{article.title[:60]}{'...' if len(article.title) > 60 else ''}</h4>
                            <p class="text-gray-400 text-xs mb-2">{article.excerpt or article.content[:100] + '...'}</p>
                            <div class="flex justify-between items-center">
                                <span class="text-xs text-cyber-red">{date_str}</span>
                                <a href="/news/{article.id}.html" class="text-xs text-cyber-blue hover:text-cyber-red transition-colors">READ_MORE</a>
                            </div>
                        </article>"""
        
        # Read current index.html
        with open('index.html', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find and replace the news section
        # This is a simplified approach - in production you'd want more robust HTML parsing
        news_section_pattern = r'(<div class="space-y-4">.*?)(</div>\s*</div>\s*<!-- Featured Music -->)'
        
        new_content = f"""<div class="space-y-4">
                    {news_html}
                    <div class="text-center pt-4">
                        <a href="/news/" class="text-cyber-blue hover:text-cyber-red text-xs font-pixel transition-colors">
                            VIEW_ALL_UPDATES →
                        </a>
                    </div>
                </div>
            </div>

            <!-- Featured Music -->"""
        
        updated_content = re.sub(news_section_pattern, new_content, content, flags=re.DOTALL)
        
        # Write back to file
        with open('index.html', 'w', encoding='utf-8') as f:
            f.write(updated_content)
        
        logging.info("✅ Updated main site news section")
    
    def generate_report(self):
        """Generate news monitoring report"""
        total_articles = len(self.articles)
        by_type = {}
        by_source = {}
        by_artist = {}
        by_sentiment = {}
        
        for article in self.articles:
            # Count by type
            by_type[article.article_type] = by_type.get(article.article_type, 0) + 1
            
            # Count by source
            by_source[article.source] = by_source.get(article.source, 0) + 1
            
            # Count by artist
            for artist in article.artist_mentioned:
                by_artist[artist] = by_artist.get(artist, 0) + 1
            
            # Count by sentiment
            by_sentiment[article.sentiment] = by_sentiment.get(article.sentiment, 0) + 1
        
        report = f"""
NULLRECORDS NEWS MONITORING REPORT
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

TOTAL ARTICLES: {total_articles}

ARTICLE TYPES:
{chr(10).join([f"  {k}: {v}" for k, v in sorted(by_type.items())])}

TOP SOURCES:
{chr(10).join([f"  {k}: {v}" for k, v in sorted(by_source.items(), key=lambda x: x[1], reverse=True)])}

ARTIST MENTIONS:
{chr(10).join([f"  {k}: {v}" for k, v in sorted(by_artist.items(), key=lambda x: x[1], reverse=True)])}

SENTIMENT ANALYSIS:
{chr(10).join([f"  {k}: {v}" for k, v in sorted(by_sentiment.items())])}

RECENT ACTIVITY (Last 7 days): {len([a for a in self.articles if datetime.fromisoformat(a.discovered_date) > datetime.now() - timedelta(days=7)])} articles
"""
        
        print(report)
        return report

def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(description='NullRecords News Monitoring System')
    parser.add_argument('--collect', action='store_true', help='Collect new news articles')
    parser.add_argument('--releases', action='store_true', help='Monitor streaming platforms for new releases')
    parser.add_argument('--generate', action='store_true', help='Generate news pages')
    parser.add_argument('--update-site', action='store_true', help='Update main site news section')
    parser.add_argument('--report', action='store_true', help='Generate monitoring report')
    parser.add_argument('--all', action='store_true', help='Run all operations')
    parser.add_argument('--limit', type=int, default=5, help='Limit articles per artist')
    
    args = parser.parse_args()
    
    # Initialize news monitor
    monitor = NewsMonitor()
    
    # Run operations based on arguments
    if args.all or args.collect:
        monitor.collect_news(max_per_artist=args.limit)
    
    if args.all or args.releases:
        monitor.monitor_streaming_releases()
    
    if args.all or args.generate:
        monitor.generate_news_pages()
    
    if args.all or args.update_site:
        monitor.update_main_site_news()
    
    if args.all or args.report:
        monitor.generate_report()
    
    if not any([args.collect, args.releases, args.generate, args.update_site, args.report, args.all]):
        print("🎵 NullRecords News Monitoring System")
        print("=====================================")
        print("Available commands:")
        print("  --collect      Collect new articles")
        print("  --releases     Monitor streaming platforms for new releases")
        print("  --generate     Generate HTML pages")
        print("  --update-site  Update main site")
        print("  --report       Show monitoring report")
        print("  --all          Run all operations")
        print("")
        print("Example: python news_monitor.py --all")

if __name__ == "__main__":
    main()
