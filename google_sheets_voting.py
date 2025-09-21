#!/usr/bin/env python3
"""
Google Sheets Voting Integration
===============================

Integration with Google Sheets for collecting voting data and engagement metrics.
Tracks votes, preferences, and user engagement for NullRecords content.

Required Environment Variables:
- GOOGLE_SERVICE_ACCOUNT_PATH: Path to service account JSON file
- GOOGLE_SHEETS_ID: ID of the Google Sheet containing voting data
- VOTING_SHEET_NAME: Name of the sheet tab (default: 'Votes')
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

# Load environment variables
try:
    from dotenv import load_dotenv
    if os.path.exists('.env'):
        load_dotenv('.env')
except ImportError:
    logging.warning("⚠️  python-dotenv not installed")

# Google Sheets API
try:
    from googleapiclient.discovery import build
    from google.oauth2 import service_account
    GOOGLE_SHEETS_AVAILABLE = True
except ImportError:
    GOOGLE_SHEETS_AVAILABLE = False
    logging.warning("⚠️  Google Sheets API not available - install google-api-python-client google-auth")

@dataclass
class VotingData:
    """Voting data structure"""
    total_votes: int = 0
    new_votes_today: int = 0
    votes_by_category: Dict[str, int] = None
    votes_by_artist: Dict[str, int] = None
    recent_votes: List[Dict] = None
    engagement_metrics: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.votes_by_category is None:
            self.votes_by_category = {}
        if self.votes_by_artist is None:
            self.votes_by_artist = {}
        if self.recent_votes is None:
            self.recent_votes = []
        if self.engagement_metrics is None:
            self.engagement_metrics = {}

class GoogleSheetsVoting:
    """Google Sheets voting integration"""
    
    def __init__(self):
        self.service = None
        self.sheets_id = os.getenv('GOOGLE_SHEETS_ID')
        self.sheet_name = os.getenv('VOTING_SHEET_NAME', 'Votes')
        self.initialize_service()
    
    def initialize_service(self):
        """Initialize Google Sheets API service"""
        if not GOOGLE_SHEETS_AVAILABLE:
            logging.warning("⚠️  Google Sheets API not available")
            return
        
        try:
            # Use the same service account credentials as other Google APIs
            credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
            if not credentials_path or not os.path.exists(credentials_path):
                logging.warning("⚠️  Google service account file not found")
                return
            
            credentials = service_account.Credentials.from_service_account_file(
                credentials_path,
                scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
            )
            
            self.service = build('sheets', 'v4', credentials=credentials)
            logging.info("✅ Google Sheets API initialized")
            
        except Exception as e:
            logging.error(f"❌ Failed to initialize Google Sheets API: {e}")
    
    def get_voting_data(self) -> VotingData:
        """Retrieve voting data from Google Sheets"""
        if not self.service or not self.sheets_id:
            logging.warning("⚠️  Google Sheets not configured - using mock data")
            return self._generate_mock_voting_data()
        
        try:
            # Define the range to read (adjust based on your sheet structure)
            range_name = f"{self.sheet_name}!A:F"  # Columns A-F
            
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.sheets_id,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            
            if not values:
                logging.warning("⚠️  No data found in Google Sheets")
                return self._generate_mock_voting_data()
            
            return self._parse_voting_data(values)
            
        except Exception as e:
            logging.error(f"❌ Error reading Google Sheets: {e}")
            return self._generate_mock_voting_data()
    
    def _parse_voting_data(self, values: List[List[str]]) -> VotingData:
        """Parse voting data from sheet values"""
        voting_data = VotingData()
        
        # Assume first row is headers: Timestamp, Artist, Category, Vote, Email, Comments
        headers = values[0] if values else []
        data_rows = values[1:] if len(values) > 1 else []
        
        today = datetime.now().date()
        votes_by_category = {}
        votes_by_artist = {}
        recent_votes = []
        
        for row in data_rows:
            if len(row) < 4:  # Skip incomplete rows
                continue
            
            timestamp_str = row[0] if len(row) > 0 else ""
            artist = row[1] if len(row) > 1 else ""
            category = row[2] if len(row) > 2 else ""
            vote = row[3] if len(row) > 3 else ""
            
            # Parse timestamp
            vote_date = None
            try:
                # Try different timestamp formats
                for fmt in ['%Y-%m-%d %H:%M:%S', '%m/%d/%Y %H:%M:%S', '%Y-%m-%d']:
                    try:
                        vote_date = datetime.strptime(timestamp_str, fmt).date()
                        break
                    except ValueError:
                        continue
            except:
                pass
            
            # Count total votes
            voting_data.total_votes += 1
            
            # Count votes from today
            if vote_date == today:
                voting_data.new_votes_today += 1
                recent_votes.append({
                    'artist': artist,
                    'category': category,
                    'vote': vote,
                    'timestamp': timestamp_str
                })
            
            # Count by category
            if category:
                votes_by_category[category] = votes_by_category.get(category, 0) + 1
            
            # Count by artist
            if artist:
                votes_by_artist[artist] = votes_by_artist.get(artist, 0) + 1
        
        voting_data.votes_by_category = votes_by_category
        voting_data.votes_by_artist = votes_by_artist
        voting_data.recent_votes = recent_votes[-10:]  # Last 10 votes
        
        # Calculate engagement metrics
        voting_data.engagement_metrics = {
            'avg_votes_per_day': voting_data.total_votes / max(1, 30),  # Rough estimate
            'top_category': max(votes_by_category.items(), key=lambda x: x[1])[0] if votes_by_category else 'N/A',
            'top_artist': max(votes_by_artist.items(), key=lambda x: x[1])[0] if votes_by_artist else 'N/A',
            'categories_count': len(votes_by_category),
            'artists_count': len(votes_by_artist)
        }
        
        logging.info(f"✅ Parsed {voting_data.total_votes} total votes, {voting_data.new_votes_today} new today")
        return voting_data
    
    def _generate_mock_voting_data(self) -> VotingData:
        """Generate mock voting data for testing"""
        import random
        
        voting_data = VotingData()
        voting_data.total_votes = random.randint(150, 300)
        voting_data.new_votes_today = random.randint(5, 25)
        
        voting_data.votes_by_category = {
            'Favorite Track': random.randint(40, 80),
            'Best Album': random.randint(30, 60),
            'Live Performance': random.randint(20, 50),
            'New Release': random.randint(15, 40),
            'Collaboration': random.randint(10, 30)
        }
        
        voting_data.votes_by_artist = {
            'My Evil Robot Army': random.randint(50, 90),
            'MERA': random.randint(40, 70),
            'Evil Robot Army': random.randint(30, 60),
            'Other Artists': random.randint(20, 40)
        }
        
        voting_data.recent_votes = [
            {
                'artist': 'My Evil Robot Army',
                'category': 'Favorite Track',
                'vote': 'Space Jazz EP',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            },
            {
                'artist': 'MERA',
                'category': 'Best Album',
                'vote': 'Explorations in Blue',
                'timestamp': (datetime.now() - timedelta(hours=2)).strftime('%Y-%m-%d %H:%M:%S')
            },
            {
                'artist': 'My Evil Robot Army',
                'category': 'Live Performance',
                'vote': 'Upcoming Show',
                'timestamp': (datetime.now() - timedelta(hours=4)).strftime('%Y-%m-%d %H:%M:%S')
            }
        ]
        
        voting_data.engagement_metrics = {
            'avg_votes_per_day': round(voting_data.total_votes / 30, 1),
            'top_category': max(voting_data.votes_by_category.items(), key=lambda x: x[1])[0],
            'top_artist': max(voting_data.votes_by_artist.items(), key=lambda x: x[1])[0],
            'categories_count': len(voting_data.votes_by_category),
            'artists_count': len(voting_data.votes_by_artist)
        }
        
        logging.info(f"✅ Generated mock voting data: {voting_data.total_votes} total votes")
        return voting_data
    
    def add_vote(self, artist: str, category: str, vote: str, email: str = "", comments: str = ""):
        """Add a new vote to the Google Sheet"""
        if not self.service or not self.sheets_id:
            logging.warning("⚠️  Google Sheets not configured - cannot add vote")
            return False
        
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Prepare the row data
            row_data = [timestamp, artist, category, vote, email, comments]
            
            # Append to the sheet
            range_name = f"{self.sheet_name}!A:F"
            
            body = {
                'values': [row_data]
            }
            
            result = self.service.spreadsheets().values().append(
                spreadsheetId=self.sheets_id,
                range=range_name,
                valueInputOption='RAW',
                body=body
            ).execute()
            
            logging.info(f"✅ Added vote: {artist} - {category} - {vote}")
            return True
            
        except Exception as e:
            logging.error(f"❌ Error adding vote to Google Sheets: {e}")
            return False
    
    def create_voting_sheet_template(self):
        """Create a template voting sheet structure"""
        if not self.service or not self.sheets_id:
            logging.warning("⚠️  Google Sheets not configured")
            return False
        
        try:
            # Define headers
            headers = ['Timestamp', 'Artist', 'Category', 'Vote', 'Email', 'Comments']
            
            # Clear existing content and add headers
            range_name = f"{self.sheet_name}!A1:F1"
            
            body = {
                'values': [headers]
            }
            
            result = self.service.spreadsheets().values().update(
                spreadsheetId=self.sheets_id,
                range=range_name,
                valueInputOption='RAW',
                body=body
            ).execute()
            
            logging.info("✅ Created voting sheet template")
            return True
            
        except Exception as e:
            logging.error(f"❌ Error creating voting sheet template: {e}")
            return False

def main():
    """Test the Google Sheets voting integration"""
    voting_system = GoogleSheetsVoting()
    
    # Get current voting data
    voting_data = voting_system.get_voting_data()
    
    print(f"📊 Voting Data Summary:")
    print(f"  Total Votes: {voting_data.total_votes}")
    print(f"  New Votes Today: {voting_data.new_votes_today}")
    print(f"  Categories: {voting_data.engagement_metrics.get('categories_count', 0)}")
    print(f"  Artists: {voting_data.engagement_metrics.get('artists_count', 0)}")
    
    print(f"\n🎵 Votes by Artist:")
    for artist, votes in voting_data.votes_by_artist.items():
        print(f"  {artist}: {votes} votes")
    
    print(f"\n📝 Votes by Category:")
    for category, votes in voting_data.votes_by_category.items():
        print(f"  {category}: {votes} votes")
    
    print(f"\n🕒 Recent Votes:")
    for vote in voting_data.recent_votes[:5]:
        print(f"  {vote['timestamp']} - {vote['artist']} - {vote['category']}")

if __name__ == "__main__":
    main()
