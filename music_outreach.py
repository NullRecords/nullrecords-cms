#!/usr/bin/env python3
"""
NullRecords Music Industry Outreach Tool
=========================================

Automated press kit distribution and outreach system for music discovery platforms,
AI services, influencers, and publications.

Usage: python music_outreach.py [--dry-run] [--target-type TYPE]
"""

import json
import time
import random
import smtplib
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
import logging
from dataclasses import dataclass, asdict, field
from pathlib import Path
import argparse
from urllib.parse import urljoin, urlparse
import hashlib

# Optional imports for web scraping and email functionality
try:
    import requests
    from bs4 import BeautifulSoup
    SCRAPING_AVAILABLE = True
except ImportError:
    requests = None
    BeautifulSoup = None
    SCRAPING_AVAILABLE = False

try:
    from email.mime.text import MimeText
    from email.mime.multipart import MimeMultipart
    EMAIL_AVAILABLE = True
except ImportError:
    EMAIL_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('outreach.log'),
        logging.StreamHandler()
    ]
)

@dataclass
class Contact:
    """Represents a contact for outreach"""
    name: str
    type: str  # 'search_engine', 'ai_service', 'influencer', 'publication', 'playlist', 'blog'
    email: Optional[str] = None
    twitter: Optional[str] = None
    instagram: Optional[str] = None
    website: Optional[str] = None
    submission_url: Optional[str] = None
    contact_form_url: Optional[str] = None
    description: str = ""
    genre_focus: List[str] = field(default_factory=list)
    contacted_date: Optional[str] = None
    response_received: bool = False
    response_date: Optional[str] = None
    response_content: str = ""
    status: str = "pending"  # pending, contacted, responded, indexed, rejected
    outreach_count: int = 0  # Track how many times we've reached out
    last_outreach: Optional[str] = None
    discovered_date: Optional[str] = None
    source_url: Optional[str] = None  # Where we found this contact
    confidence_score: float = 0.5  # How confident we are this is relevant (0-1)
    contact_hash: Optional[str] = None  # Unique identifier to prevent duplicates
    
    def __post_init__(self):
        if not self.contact_hash:
            # Create unique hash based on name and website/email
            identifier = f"{self.name}_{self.website or self.email or ''}"
            self.contact_hash = hashlib.md5(identifier.lower().encode()).hexdigest()[:12]
        if not self.discovered_date:
            self.discovered_date = datetime.now().isoformat()

@dataclass 
class SourceTracker:
    """Track sources we've scraped and their status"""
    url: str
    last_scraped: Optional[str] = None
    contacts_found: int = 0
    success_rate: float = 0.0
    scrape_count: int = 0
    status: str = "active"  # active, exhausted, blocked, error

class MusicOutreach:
    """Main outreach automation class"""
    
    def __init__(self):
        self.contacts_file = Path("outreach_contacts.json")
        self.data_file = Path("outreach_data.json")
        self.sources_file = Path("outreach_sources.json")
        self.contacts: List[Contact] = []
        self.sources: List[SourceTracker] = []
        self.session = requests.Session() if requests else None
        self.max_outreach_per_contact = 4  # Maximum times to contact same entity
        self.min_outreach_interval = 7  # Minimum days between outreach to same contact
        self.daily_outreach_limit = 20  # Maximum outreach per day
        
        self.load_contacts()
        self.load_sources()
        
        # Configure session for web scraping
        if self.session:
            self.session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'DNT': '1',
                'Connection': 'keep-alive',
            })
        
        # Discovery search terms for finding new sources
        self.discovery_terms = [
            "electronic music blog submit",
            "lofi music submission",
            "jazz fusion publication contact",
            "independent music blog",
            "chillhop music curator",
            "ambient music reviews",
            "experimental music publication",
            "electronic jazz blog",
            "music discovery platform",
            "playlist curator electronic",
            "indie music submission",
            "new music blog 2024",
            "music journalist contact",
            "underground music publication",
            "netlabel submissions"
        ]
        
        # Seed URLs for discovering new sources
        self.discovery_sources = [
            "https://www.hypebot.com",
            "https://www.musicindustryhowto.com", 
            "https://blog.bandcamp.com",
            "https://daily.bandcamp.com",
            "https://ra.co",
            "https://www.allmusic.com",
            "https://pitchfork.com",
            "https://www.thefader.com",
            "https://consequenceofsound.net",
            "https://www.xlr8r.com",
            "https://www.residentadvisor.net",
            "https://electronicbeats.net",
            "https://www.factmag.com",
            "https://mixmag.net"
        ]
        
        # Press kit content
        self.press_kit = {
            "site_url": "https://nullrecords.com",
            "contact_email": "team@nullrecords.com",
            "genres": ["LoFi", "Jazz Fusion", "Electronic Jazz", "Instrumental", "Ambient", "Chillhop", "Experimental"],
            "artists": [
                {
                    "name": "My Evil Robot Army",
                    "description": "Experimental electronic soundscapes blending jazz fusion with lo-fi aesthetics",
                    "albums": ["Evil Robot", "Space Jazz"],
                    "spotify": "https://open.spotify.com/artist/myevilrobotarmy"
                },
                {
                    "name": "MERA", 
                    "description": "Ambient lo-fi compositions exploring the relationship between nature and technology",
                    "albums": ["Travel Beyond", "Explorations", "Explorations in Blue"],
                    "spotify": "https://open.spotify.com/artist/mera"
                }
            ]
        }
        
    def initialize_contacts(self):
        """Initialize the contact database with comprehensive targets"""
        contacts_data = [
            # Search Engines & AI Services
            Contact("Google Search Console", "search_engine", 
                   submission_url="https://search.google.com/search-console/",
                   description="Submit sitemap for Google indexing"),
            Contact("Bing Webmaster Tools", "search_engine",
                   submission_url="https://www.bing.com/webmasters/",
                   description="Submit to Bing search index"),
            Contact("DuckDuckGo", "search_engine",
                   contact_form_url="https://duckduckgo.com/feedback",
                   description="Privacy-focused search engine"),
            Contact("Perplexity AI", "ai_service",
                   contact_form_url="https://www.perplexity.ai/contact",
                   description="AI-powered search and discovery"),
            Contact("Claude AI (Anthropic)", "ai_service",
                   email="support@anthropic.com",
                   description="AI assistant for content discovery"),
            Contact("ChatGPT (OpenAI)", "ai_service",
                   contact_form_url="https://help.openai.com/en/",
                   description="AI content and music discovery"),
            
            # Music Discovery Platforms
            Contact("Spotify Editorial", "platform",
                   submission_url="https://artists.spotify.com/c/music/playlist-submission",
                   description="Spotify playlist submission",
                   genre_focus=["electronic", "jazz", "lofi", "instrumental"]),
            Contact("Apple Music", "platform",
                   submission_url="https://artists.apple.com/",
                   description="Apple Music artist submission"),
            Contact("Bandcamp", "platform",
                   contact_form_url="https://bandcamp.com/contact",
                   description="Independent music platform"),
            Contact("SoundCloud", "platform",
                   contact_form_url="https://help.soundcloud.com/hc/en-us/requests/new",
                   description="Audio platform for artists"),
            
            # Music Blogs & Publications  
            Contact("Pitchfork", "publication",
                   email="tips@pitchfork.com",
                   description="Influential music publication",
                   genre_focus=["electronic", "experimental", "jazz"]),
            Contact("The Fader", "publication",
                   email="tips@thefader.com", 
                   description="Music and culture magazine"),
            Contact("Stereogum", "publication",
                   email="tips@stereogum.com",
                   description="Music blog and news"),
            Contact("Complex Music", "publication",
                   email="music@complex.com",
                   description="Music and culture publication"),
            Contact("Consequence of Sound", "publication",
                   email="tips@consequenceofsound.net",
                   description="Music news and reviews"),
            
            # Electronic/Jazz Focused Publications
            Contact("Resident Advisor", "publication",
                   contact_form_url="https://ra.co/contact",
                   description="Electronic music publication",
                   genre_focus=["electronic", "ambient", "experimental"]),
            Contact("Jazz Times", "publication",
                   email="editor@jazztimes.com",
                   description="Jazz music publication",
                   genre_focus=["jazz", "fusion", "experimental"]),
            Contact("All About Jazz", "publication",
                   contact_form_url="https://www.allaboutjazz.com/contact.php",
                   description="Jazz publication and database",
                   genre_focus=["jazz", "fusion", "electronic jazz"]),
            Contact("Electronic Beats", "publication",
                   email="info@electronicbeats.net",
                   description="Electronic music culture magazine"),
            
            # LoFi/Chillhop Focused
            Contact("Chillhop Music", "label",
                   email="demo@chillhopmusic.com",
                   description="LoFi hip hop label and playlist curator",
                   genre_focus=["lofi", "chillhop", "instrumental"]),
            Contact("LoFi Girl", "influencer",
                   contact_form_url="https://lofigirl.com/contact/",
                   description="Popular LoFi music curator",
                   genre_focus=["lofi", "study music", "chill"]),
            Contact("Ambient Online", "publication",
                   email="editor@ambient.org",
                   description="Ambient music publication",
                   genre_focus=["ambient", "electronic", "experimental"]),
            
            # YouTube Influencers & Channels
            Contact("Majestic Casual", "influencer",
                   contact_form_url="https://majesticcasual.com/contact",
                   description="Electronic music YouTube channel",
                   genre_focus=["electronic", "chill", "indie"]),
            Contact("Mr. Suicide Sheep", "influencer",
                   email="business@mrsuicidesheep.com",
                   description="Electronic music promotion",
                   genre_focus=["electronic", "indie", "chill"]),
            Contact("Chill Nation", "influencer", 
                   contact_form_url="https://www.chillnation.com/contact",
                   description="Chill music promotion channel"),
            
            # Music Aggregators & Discovery
            Contact("Last.fm", "platform",
                   contact_form_url="https://support.last.fm/",
                   description="Music discovery and scrobbling"),
            Contact("AllMusic", "database",
                   contact_form_url="https://www.allmusic.com/contact",
                   description="Music database and discovery"),
            Contact("Discogs", "database",
                   contact_form_url="https://www.discogs.com/help/",
                   description="Music database and marketplace"),
            Contact("MusicBrainz", "database",
                   contact_form_url="https://musicbrainz.org/contact",
                   description="Open music encyclopedia"),
            
            # Playlist Curators
            Contact("Indie Shuffle", "curator",
                   email="submit@indieshuffle.com",
                   description="Music discovery and playlists",
                   genre_focus=["indie", "electronic", "experimental"]),
            Contact("The Music Ninja", "curator",
                   email="hello@themusicninja.com",
                   description="Music discovery blog"),
            Contact("Earmilk", "curator",
                   email="submissions@earmilk.com",
                   description="Music discovery platform"),
            
            # AI Music Discovery
            Contact("AIVA Technologies", "ai_service",
                   contact_form_url="https://www.aiva.ai/contact/",
                   description="AI music composition and discovery"),
            Contact("Endel", "ai_service",
                   email="hello@endel.io",
                   description="AI-powered adaptive music"),
            Contact("Mubert", "ai_service",
                   email="hello@mubert.com",
                   description="AI music streaming platform"),
        ]
        
        self.contacts = contacts_data
        self.save_contacts()
        logging.info(f"Initialized {len(contacts_data)} contacts")
    
    def load_contacts(self):
        """Load contacts from JSON file"""
        if self.contacts_file.exists():
            try:
                with open(self.contacts_file, 'r') as f:
                    data = json.load(f)
                    self.contacts = [Contact(**contact) for contact in data]
                logging.info(f"Loaded {len(self.contacts)} contacts")
            except Exception as e:
                logging.error(f"Error loading contacts: {e}")
                self.contacts = []
        else:
            logging.info("No contacts file found, initializing...")
            self.initialize_contacts()
    
    def save_contacts(self):
        """Save contacts to JSON file"""
        try:
            with open(self.contacts_file, 'w') as f:
                json.dump([asdict(contact) for contact in self.contacts], f, indent=2)
            logging.info("Contacts saved successfully")
        except Exception as e:
            logging.error(f"Error saving contacts: {e}")
    
    def load_sources(self):
        """Load source tracking data"""
        if self.sources_file.exists():
            try:
                with open(self.sources_file, 'r') as f:
                    data = json.load(f)
                    self.sources = [SourceTracker(**source) for source in data]
                logging.info(f"Loaded {len(self.sources)} source trackers")
            except Exception as e:
                logging.error(f"Error loading sources: {e}")
                self.sources = []
        else:
            self.sources = []
    
    def save_sources(self):
        """Save source tracking data"""
        try:
            with open(self.sources_file, 'w') as f:
                json.dump([asdict(source) for source in self.sources], f, indent=2)
            logging.info("Source tracking data saved")
        except Exception as e:
            logging.error(f"Error saving sources: {e}")
    
    def discover_new_sources(self, max_new_sources=10):
        """Discover new music industry sources through web scraping"""
        if not SCRAPING_AVAILABLE:
            logging.warning("Web scraping not available - install beautifulsoup4 and requests")
            return []
        
        new_contacts = []
        
        # Search for music blogs and publications
        search_queries = [
            "electronic music blogs 2024",
            "independent music publications",
            "lofi chillhop blogs",
            "experimental music websites",
            "music submission blogs",
        ]
        
        for query in search_queries[:2]:  # Limit to 2 searches per run
            try:
                results = self.search_duckduckgo(query)
                for result in results[:5]:  # Check top 5 results per query
                    contacts = self.scrape_music_site(result['url'])
                    new_contacts.extend(contacts)
                    
                    if len(new_contacts) >= max_new_sources:
                        break
                        
                time.sleep(random.uniform(2, 4))  # Rate limiting
                
            except Exception as e:
                logging.error(f"Error discovering sources for '{query}': {e}")
        
        # Deduplicate based on contact hash
        existing_hashes = {c.contact_hash for c in self.contacts}
        unique_new_contacts = [c for c in new_contacts if c.contact_hash not in existing_hashes]
        
        logging.info(f"Discovered {len(unique_new_contacts)} new unique contacts")
        return unique_new_contacts
    
    def search_duckduckgo(self, query, max_results=10):
        """Search DuckDuckGo for music-related sites"""
        try:
            search_url = f"https://html.duckduckgo.com/html/?q={query.replace(' ', '+')}"
            response = self.session.get(search_url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            results = []
            
            for result in soup.find_all('a', class_='result__a')[:max_results]:
                href = result.get('href')
                if href and not href.startswith('/'):
                    results.append({
                        'url': href,
                        'title': result.get_text(strip=True)
                    })
            
            return results
            
        except Exception as e:
            logging.error(f"DuckDuckGo search failed: {e}")
            return []
    
    def scrape_music_site(self, url):
        """Scrape a music website for contact information"""
        contacts = []
        
        try:
            # Track this source
            source = next((s for s in self.sources if s.url == url), None)
            if not source:
                source = SourceTracker(url=url)
                self.sources.append(source)
            
            source.scrape_count += 1
            source.last_scraped = datetime.now().isoformat()
            
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract site information
            site_name = self.extract_site_name(soup, url)
            site_description = self.extract_site_description(soup)
            contact_info = self.extract_contact_info(soup, url)
            
            if contact_info['email'] or contact_info['contact_form']:
                # Determine site type and genre focus
                site_type = self.classify_site_type(soup, url)
                genre_focus = self.extract_genre_focus(soup)
                
                contact = Contact(
                    name=site_name,
                    type=site_type,
                    email=contact_info['email'],
                    website=url,
                    contact_form_url=contact_info['contact_form'],
                    description=site_description,
                    genre_focus=genre_focus,
                    source_url=url,
                    confidence_score=self.calculate_confidence_score(soup, url)
                )
                
                contacts.append(contact)
                source.contacts_found += 1
                
                logging.info(f"Found contact: {site_name} at {url}")
            
            time.sleep(random.uniform(1, 2))  # Rate limiting
            
        except Exception as e:
            logging.error(f"Error scraping {url}: {e}")
            if source:
                source.status = "error"
        
        self.save_sources()
        return contacts
    
    def extract_site_name(self, soup, url):
        """Extract site name from HTML"""
        # Try title tag first
        title = soup.find('title')
        if title:
            site_name = title.get_text(strip=True).split('|')[0].split('-')[0].strip()
            if len(site_name) < 50:
                return site_name
        
        # Try h1 tag
        h1 = soup.find('h1')
        if h1:
            return h1.get_text(strip=True)[:50]
        
        # Fallback to domain name
        domain = urlparse(url).netloc.replace('www.', '')
        return domain.split('.')[0].title()
    
    def extract_site_description(self, soup):
        """Extract site description"""
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            return meta_desc.get('content', '')[:200]
        
        # Try to find about section
        about_text = soup.find(text=re.compile(r'about|music|blog|publication', re.I))
        if about_text:
            return str(about_text)[:200]
        
        return ""
    
    def extract_contact_info(self, soup, base_url):
        """Extract contact information from site"""
        contact_info = {'email': None, 'contact_form': None}
        
        # Look for email addresses
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        page_text = soup.get_text()
        emails = re.findall(email_pattern, page_text)
        
        # Filter for relevant emails
        relevant_emails = [email for email in emails if any(keyword in email.lower() 
                          for keyword in ['contact', 'info', 'submit', 'music', 'editor', 'demo'])]
        
        if relevant_emails:
            contact_info['email'] = relevant_emails[0]
        elif emails:
            contact_info['email'] = emails[0]
        
        # Look for contact forms
        contact_links = soup.find_all('a', href=True)
        for link in contact_links:
            href = link.get('href', '').lower()
            text = link.get_text().lower()
            
            if any(keyword in href or keyword in text 
                   for keyword in ['contact', 'submit', 'demo', 'music-submission']):
                full_url = urljoin(base_url, link['href'])
                contact_info['contact_form'] = full_url
                break
        
        return contact_info
    
    def classify_site_type(self, soup, url):
        """Classify the type of music site"""
        text = soup.get_text().lower()
        url_lower = url.lower()
        
        if any(keyword in text or keyword in url_lower 
               for keyword in ['blog', 'magazine', 'publication', 'review']):
            return 'publication'
        elif any(keyword in text or keyword in url_lower 
                 for keyword in ['playlist', 'curator', 'mix']):
            return 'curator'
        elif any(keyword in text or keyword in url_lower 
                 for keyword in ['label', 'records']):
            return 'label'
        elif any(keyword in text or keyword in url_lower 
                 for keyword in ['radio', 'podcast']):
            return 'influencer'
        else:
            return 'publication'  # Default
    
    def extract_genre_focus(self, soup):
        """Extract what genres this site focuses on"""
        text = soup.get_text().lower()
        genres = []
        
        genre_keywords = {
            'electronic': ['electronic', 'edm', 'techno', 'house', 'ambient'],
            'jazz': ['jazz', 'fusion', 'bebop', 'smooth jazz'],
            'lofi': ['lofi', 'lo-fi', 'chill', 'chillhop', 'study'],
            'experimental': ['experimental', 'avant-garde', 'noise', 'abstract'],
            'indie': ['indie', 'independent', 'alternative'],
            'hip-hop': ['hip-hop', 'rap', 'beats', 'instrumental hip-hop']
        }
        
        for genre, keywords in genre_keywords.items():
            if any(keyword in text for keyword in keywords):
                genres.append(genre)
        
        return genres[:3]  # Limit to 3 genres
    
    def calculate_confidence_score(self, soup, url):
        """Calculate how confident we are this is a relevant contact"""
        score = 0.5  # Base score
        text = soup.get_text().lower()
        
        # Positive indicators
        if any(keyword in text for keyword in ['music submission', 'demo', 'press kit']):
            score += 0.3
        if any(keyword in text for keyword in ['electronic', 'jazz', 'lofi', 'experimental']):
            score += 0.2
        if any(keyword in text for keyword in ['independent', 'indie', 'underground']):
            score += 0.1
        if 'contact' in text:
            score += 0.1
        
        # Negative indicators
        if any(keyword in text for keyword in ['country', 'pop', 'rock', 'metal']):
            score -= 0.1
        if len(text) < 500:  # Very short pages might not be substantial
            score -= 0.1
        
        return max(0.0, min(1.0, score))
    
    def generate_press_kit_email(self, contact: Contact) -> str:
        """Generate personalized press kit email"""
        
        subject_templates = [
            f"🎵 Introducing NullRecords: {', '.join(self.press_kit['genres'][:3])} Music Collective",
            f"New Music Discovery: NullRecords - Independent {contact.genre_focus[0] if contact.genre_focus else 'Electronic'} Artists",
            f"Press Kit: NullRecords - Innovative Music at the Intersection of Art & Technology",
            f"🎧 NullRecords: Fresh Sounds in {', '.join(contact.genre_focus[:2]) if contact.genre_focus else 'Electronic Jazz'}"
        ]
        
        greetings = [
            f"Hello {contact.name} team,",
            f"Hi there,",
            f"Greetings from NullRecords,",
            f"Hello,"
        ]
        
        intro_paragraphs = [
            f"I hope this message finds you well! I'm reaching out to introduce you to NullRecords, an independent music collective creating innovative sounds at the intersection of music, art, and technology.",
            
            f"We're a group of artists pushing the boundaries of {', '.join(self.press_kit['genres'][:4])}, and we'd love to share our music with your audience.",
            
            f"NullRecords represents a new wave of independent artists exploring the relationship between human creativity and digital innovation through music."
        ]
        
        artist_section = "\n\n🎨 Our Artists:\n"
        for artist in self.press_kit['artists']:
            artist_section += f"• {artist['name']}: {artist['description']}\n"
            artist_section += f"  Albums: {', '.join(artist['albums'])}\n\n"
        
        website_section = f"""
🌐 Explore Our Music:
• Website: {self.press_kit['site_url']}
• Full artist profiles and streaming links available
• High-quality press photos and assets available upon request

🎯 Why This Might Interest You:"""
        
        # Customize based on contact type
        why_relevant = {
            'search_engine': "Our site features comprehensive metadata and structured data perfect for music discovery indexing.",
            'ai_service': "Our music represents the intersection of human creativity and AI-assisted composition, perfect for AI music discovery platforms.",
            'publication': f"Our artists create unique sounds that blend {', '.join(contact.genre_focus if contact.genre_focus else self.press_kit['genres'][:3])}, offering fresh content for your readers.",
            'influencer': "Our music aligns perfectly with your audience's taste for innovative, high-quality independent music.",
            'platform': "We're looking to connect with new audiences who appreciate innovative, independently-produced music.",
            'curator': "Our catalog offers unique tracks perfect for playlists focused on innovative electronic and jazz fusion music.",
            'label': "We're open to collaboration and partnership opportunities with like-minded labels.",
            'database': "We'd love to ensure our music is properly catalogued and discoverable through your platform."
        }
        
        call_to_action = f"""
📧 We'd love to hear your thoughts, questions, or any opportunities for collaboration. Please feel free to reach out to us at {self.press_kit['contact_email']}.

Thank you for your time and for supporting independent music!

Best regards,
The NullRecords Team
{self.press_kit['site_url']}
{self.press_kit['contact_email']}

---
This is a one-time introduction. If you'd prefer not to receive future communications, please reply and let us know.
"""
        
        # Compose email
        subject = random.choice(subject_templates)
        greeting = random.choice(greetings)
        intro = random.choice(intro_paragraphs)
        relevance = why_relevant.get(contact.type, why_relevant['platform'])
        
        email_body = f"""{greeting}

{intro}

{artist_section}{website_section}
• {relevance}

{call_to_action}"""
        
        return subject, email_body
    
    def create_press_release(self) -> str:
        """Generate a comprehensive press release"""
        return f"""
FOR IMMEDIATE RELEASE

NullRecords: Independent Music Collective Launches Innovative Platform Blending Jazz Fusion, Electronic Music, and Visual Art

{datetime.now().strftime('%B %d, %Y')} - NullRecords announces the launch of their comprehensive digital platform showcasing a new generation of independent artists creating music at the intersection of technology, art, and human creativity.

ABOUT NULLRECORDS
NullRecords represents a collective of innovative musicians specializing in LoFi jazz fusion, electronic instrumentals, and multimedia art collaborations. The platform features artists who push creative boundaries by blending organic musical elements with digital innovation.

FEATURED ARTISTS

My Evil Robot Army
Experimental electronic soundscapes that explore the relationship between human creativity and artificial intelligence. Their debut albums "Evil Robot" and "Space Jazz" showcase a unique blend of jazz fusion with lo-fi electronic aesthetics.

MERA  
Solo artist and producer creating ambient lo-fi compositions that examine the intersection of nature, technology, and human emotion. Albums include "Travel Beyond," "Explorations," and "Explorations in Blue."

MISSION & VISION
NullRecords aims to create a space where music, visual art, and technology converge to produce innovative artistic expressions. The collective focuses on:
• Supporting independent artists pushing creative boundaries
• Exploring AI-assisted composition and human-machine collaboration
• Creating multimedia art experiences that transcend traditional formats
• Building a community around innovative, high-quality independent music

AVAILABILITY
All NullRecords content is available at https://nullrecords.com, featuring:
• Full artist profiles and discographies
• High-quality streaming and download options
• Visual art collaborations and multimedia content
• Direct artist contact and collaboration opportunities

CONTACT INFORMATION
For press inquiries, interview requests, or collaboration opportunities:
Email: team@nullrecords.com
Website: https://nullrecords.com

###

About NullRecords: Founded in 2020, NullRecords is an independent music collective dedicated to supporting innovative artists who create music at the intersection of technology, art, and human creativity. Specializing in LoFi jazz fusion, electronic instrumentals, and multimedia collaborations.
"""
    
    def submit_to_search_engines(self, dry_run=False):
        """Submit site to search engines"""
        search_engines = [c for c in self.contacts if c.type == 'search_engine']
        
        for engine in search_engines:
            if dry_run:
                logging.info(f"[DRY RUN] Would submit to {engine.name}")
                continue
                
            if engine.name == "Google Search Console":
                logging.info("Google Search Console requires manual sitemap submission")
                logging.info("Visit: https://search.google.com/search-console/")
                logging.info("Add property: nullrecords.com")
                logging.info("Submit sitemap: https://nullrecords.com/sitemap.xml")
                
            elif engine.name == "Bing Webmaster Tools":
                logging.info("Bing Webmaster Tools requires manual submission")
                logging.info("Visit: https://www.bing.com/webmasters/")
                
            engine.status = "manual_submission_required"
            engine.contacted_date = datetime.now().isoformat()
    
    def get_eligible_contacts(self, target_types=None):
        """Get contacts eligible for outreach based on frequency rules"""
        eligible = []
        cutoff_date = datetime.now() - timedelta(days=self.min_outreach_interval)
        
        for contact in self.contacts:
            # Filter by type if specified
            if target_types and contact.type not in target_types:
                continue
            
            # Check if we haven't exceeded max outreach attempts
            if contact.outreach_count >= self.max_outreach_per_contact:
                continue
            
            # Check minimum interval since last outreach
            if contact.last_outreach:
                last_contact = datetime.fromisoformat(contact.last_outreach)
                if last_contact > cutoff_date:
                    continue
            
            # Include pending contacts and those ready for follow-up
            if contact.status in ['pending', 'contacted', 'manual_submission_required']:
                eligible.append(contact)
        
        return eligible
    
    def send_outreach_emails(self, target_types=None, dry_run=False, limit=None, discover_new=True):
        """Send outreach emails to contacts with intelligent frequency management"""
        
        # Discover new sources first
        if discover_new and not dry_run:
            try:
                new_contacts = self.discover_new_sources(max_new_sources=5)
                for contact in new_contacts:
                    if contact.confidence_score >= 0.6:  # Only add high-confidence contacts
                        self.contacts.append(contact)
                        logging.info(f"Added new contact: {contact.name} (confidence: {contact.confidence_score:.2f})")
                
                if new_contacts:
                    self.save_contacts()
            except Exception as e:
                logging.error(f"Source discovery failed: {e}")
        
        # Get eligible contacts
        targets = self.get_eligible_contacts(target_types)
        
        # Sort by priority (new contacts first, then by confidence score)
        targets.sort(key=lambda c: (c.outreach_count, -c.confidence_score))
        
        if limit:
            targets = targets[:limit]
        elif not limit:
            # Apply daily limit
            targets = targets[:self.daily_outreach_limit]
        
        logging.info(f"Targeting {len(targets)} eligible contacts for outreach")
        
        successful_outreach = 0
        
        for contact in targets:
            if not contact.email and not contact.contact_form_url:
                logging.warning(f"No email or contact form for {contact.name}")
                continue
            
            subject, body = self.generate_press_kit_email(contact)
            
            if dry_run:
                logging.info(f"[DRY RUN] Would email {contact.name} ({contact.type}) - Attempt #{contact.outreach_count + 1}")
                logging.info(f"Confidence: {contact.confidence_score:.2f}")
                logging.info(f"Subject: {subject}")
                logging.info(f"Body preview: {body[:200]}...")
                logging.info("---")
                continue
            
            if contact.email:
                success = self.send_email(contact.email, subject, body)
                if success:
                    contact.outreach_count += 1
                    contact.last_outreach = datetime.now().isoformat()
                    if contact.outreach_count == 1:
                        contact.status = "contacted"
                        contact.contacted_date = datetime.now().isoformat()
                    successful_outreach += 1
                    logging.info(f"✅ Emailed {contact.name} (attempt #{contact.outreach_count})")
                else:
                    logging.error(f"❌ Failed to email {contact.name}")
            else:
                contact.outreach_count += 1
                contact.last_outreach = datetime.now().isoformat()
                contact.status = "manual_submission_required"
                if not contact.contacted_date:
                    contact.contacted_date = datetime.now().isoformat()
                logging.info(f"📝 Manual submission required for {contact.name}: {contact.contact_form_url}")
            
            # Rate limiting between sends
            time.sleep(random.uniform(2, 5))
        
        self.save_contacts()
        logging.info(f"Completed outreach to {successful_outreach} contacts")
        return successful_outreach
    
    def send_email(self, to_email: str, subject: str, body: str) -> bool:
        """Send email (placeholder - requires SMTP configuration)"""
        if not EMAIL_AVAILABLE:
            logging.warning("Email libraries not available - using placeholder mode")
            
        logging.info(f"📧 [PLACEHOLDER] Would send email to {to_email}")
        logging.info(f"Subject: {subject}")
        logging.info("Configure SMTP settings in send_email method to enable actual sending")
        return True  # Placeholder success
        
        # Uncomment and configure for actual email sending:
        """
        if not EMAIL_AVAILABLE:
            logging.error("Email libraries not installed")
            return False
            
        try:
            msg = MimeMultipart()
            msg['From'] = "team@nullrecords.com"  # Configure your email
            msg['To'] = to_email
            msg['Subject'] = subject
            msg.attach(MimeText(body, 'plain'))
            
            # Configure your SMTP server
            server = smtplib.SMTP('smtp.gmail.com', 587)  # Example
            server.starttls()
            server.login("your_email@gmail.com", "your_app_password")
            server.sendmail("team@nullrecords.com", to_email, msg.as_string())
            server.quit()
            return True
        except Exception as e:
            logging.error(f"Email sending failed: {e}")
            return False
        """
    
    def generate_report(self):
        """Generate outreach status report"""
        status_counts = {}
        type_counts = {}
        
        for contact in self.contacts:
            status_counts[contact.status] = status_counts.get(contact.status, 0) + 1
            type_counts[contact.type] = type_counts.get(contact.type, 0) + 1
        
        report = f"""
NULLRECORDS OUTREACH REPORT
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

TOTAL CONTACTS: {len(self.contacts)}

STATUS BREAKDOWN:
"""
        for status, count in sorted(status_counts.items()):
            report += f"  {status}: {count}\n"
        
        report += "\nTYPE BREAKDOWN:\n"
        for type_name, count in sorted(type_counts.items()):
            report += f"  {type_name}: {count}\n"
        
        # Recent activity
        recent_contacts = [c for c in self.contacts if c.contacted_date and 
                          datetime.fromisoformat(c.contacted_date) > datetime.now() - timedelta(days=7)]
        
        report += f"\nRECENT ACTIVITY (Last 7 days): {len(recent_contacts)} contacts\n"
        
        # Responses received
        responses = [c for c in self.contacts if c.response_received]
        report += f"\nRESPONSES RECEIVED: {len(responses)}\n"
        
        if responses:
            for response in responses[-5:]:  # Show last 5 responses
                report += f"  • {response.name} ({response.response_date})\n"
        
        return report
    
    def export_contact_list(self, filename="outreach_contacts_export.json"):
        """Export contacts for manual use"""
        export_data = {
            "generated": datetime.now().isoformat(),
            "total_contacts": len(self.contacts),
            "contacts": [asdict(contact) for contact in self.contacts],
            "press_kit": self.press_kit
        }
        
        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        logging.info(f"Contacts exported to {filename}")

    def create_daily_schedule(self):
        """Create a schedule for daily automated outreach"""
        schedule_config = {
            "daily_outreach": {
                "enabled": True,
                "max_contacts_per_day": self.daily_outreach_limit,
                "discovery_enabled": True,
                "max_new_sources_per_day": 5,
                "target_distribution": {
                    "publication": 0.4,    # 40% publications
                    "influencer": 0.25,    # 25% influencers  
                    "curator": 0.15,       # 15% curators
                    "platform": 0.1,       # 10% platforms
                    "ai_service": 0.1      # 10% AI services
                }
            },
            "follow_up_schedule": {
                "first_follow_up_days": 14,
                "second_follow_up_days": 30,
                "final_follow_up_days": 60
            }
        }
        
        with open("outreach_schedule.json", 'w') as f:
            json.dump(schedule_config, f, indent=2)
        
        logging.info("Daily schedule configuration created")
        return schedule_config
    
    def run_daily_outreach(self, dry_run=False):
        """Run the daily automated outreach process"""
        logging.info("🚀 Starting daily automated outreach...")
        
        # Load or create schedule
        try:
            with open("outreach_schedule.json", 'r') as f:
                schedule = json.load(f)
        except FileNotFoundError:
            schedule = self.create_daily_schedule()
        
        if not schedule["daily_outreach"]["enabled"]:
            logging.info("Daily outreach is disabled in schedule config")
            return
        
        # Run targeted outreach based on distribution
        total_sent = 0
        target_dist = schedule["daily_outreach"]["target_distribution"]
        max_daily = schedule["daily_outreach"]["max_contacts_per_day"]
        
        for contact_type, percentage in target_dist.items():
            type_limit = int(max_daily * percentage)
            if type_limit > 0:
                sent = self.send_outreach_emails(
                    target_types=[contact_type],
                    dry_run=dry_run,
                    limit=type_limit,
                    discover_new=(contact_type == 'publication')  # Only discover for publications
                )
                total_sent += sent
                
                # Small delay between contact types
                if not dry_run:
                    time.sleep(random.uniform(5, 10))
        
        # Log daily summary
        daily_summary = {
            "date": datetime.now().isoformat(),
            "contacts_reached": total_sent,
            "discovery_run": schedule["daily_outreach"]["discovery_enabled"],
            "target_distribution": target_dist
        }
        
        # Save daily log
        daily_log_file = Path("daily_outreach_log.json")
        if daily_log_file.exists():
            with open(daily_log_file, 'r') as f:
                daily_log = json.load(f)
        else:
            daily_log = []
        
        daily_log.append(daily_summary)
        
        # Keep only last 30 days
        cutoff_date = datetime.now() - timedelta(days=30)
        daily_log = [entry for entry in daily_log 
                    if datetime.fromisoformat(entry["date"]) > cutoff_date]
        
        with open(daily_log_file, 'w') as f:
            json.dump(daily_log, f, indent=2)
        
        logging.info(f"✅ Daily outreach completed: {total_sent} contacts reached")
        return total_sent

def main():
    parser = argparse.ArgumentParser(description='NullRecords Music Industry Outreach Tool')
    parser.add_argument('--dry-run', action='store_true', help='Run without actually sending emails')
    parser.add_argument('--target-type', choices=['search_engine', 'ai_service', 'influencer', 'publication', 'platform', 'curator', 'label'], 
                       help='Target specific contact type')
    parser.add_argument('--limit', type=int, help='Limit number of contacts to process')
    parser.add_argument('--report', action='store_true', help='Generate status report')
    parser.add_argument('--export', action='store_true', help='Export contact list')
    parser.add_argument('--init', action='store_true', help='Initialize contact database')
    parser.add_argument('--daily', action='store_true', help='Run daily automated outreach')
    parser.add_argument('--discover', action='store_true', help='Discover new sources only')
    parser.add_argument('--schedule', action='store_true', help='Create daily schedule configuration')
    
    args = parser.parse_args()
    
    outreach = MusicOutreach()
    
    if args.init:
        outreach.initialize_contacts()
        return
    
    if args.report:
        print(outreach.generate_report())
        return
    
    if args.export:
        outreach.export_contact_list()
        return
        
    if args.schedule:
        outreach.create_daily_schedule()
        return
    
    if args.discover:
        if not SCRAPING_AVAILABLE:
            print("❌ Web scraping not available. Install: pip install beautifulsoup4 requests")
            return
        logging.info("🔍 Discovering new sources...")
        new_contacts = outreach.discover_new_sources(max_new_sources=10)
        for contact in new_contacts:
            if contact.confidence_score >= 0.5:
                outreach.contacts.append(contact)
                logging.info(f"Added: {contact.name} (confidence: {contact.confidence_score:.2f})")
        outreach.save_contacts()
        print(f"✅ Discovered {len(new_contacts)} new contacts")
        return
    
    if args.daily:
        outreach.run_daily_outreach(dry_run=args.dry_run)
        print("\n" + outreach.generate_report())
        return
    
    # Manual outreach process
    target_types = [args.target_type] if args.target_type else None
    
    logging.info("Starting NullRecords outreach campaign...")
    
    # Submit to search engines (one-time setup)
    if not target_types or 'search_engine' in target_types:
        outreach.submit_to_search_engines(dry_run=args.dry_run)
    
    # Send outreach emails
    outreach.send_outreach_emails(
        target_types=target_types,
        dry_run=args.dry_run,
        limit=args.limit,
        discover_new=True
    )
    
    # Generate report
    print("\n" + outreach.generate_report())
    
    logging.info("Outreach campaign completed!")

if __name__ == "__main__":
    main()
