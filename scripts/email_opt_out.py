#!/usr/bin/env python3
"""
Email Opt-Out Management System
===============================

Handles email opt-out tracking and checking for NullRecords email systems.
Provides utilities for checking opt-out status before sending emails.
"""

import json
import os
import logging
from datetime import datetime
from typing import List, Dict, Optional, Set
from pathlib import Path

class EmailOptOutManager:
    """Manages email opt-out preferences"""
    
    def __init__(self, opt_out_file: str = None):
        self.opt_out_file = opt_out_file or os.path.join(os.path.dirname(__file__), '..', 'data', 'email_opt_outs.json')
        self.opt_out_file = os.path.abspath(self.opt_out_file)
        self._ensure_opt_out_file_exists()
    
    def _ensure_opt_out_file_exists(self):
        """Ensure the opt-out file exists with proper structure"""
        os.makedirs(os.path.dirname(self.opt_out_file), exist_ok=True)
        
        if not os.path.exists(self.opt_out_file):
            initial_data = {
                "opt_outs": [],
                "metadata": {
                    "created": datetime.now().isoformat(),
                    "last_updated": datetime.now().isoformat(),
                    "total_opt_outs": 0,
                    "version": "1.0"
                }
            }
            self._save_opt_outs(initial_data)
    
    def _load_opt_outs(self) -> Dict:
        """Load opt-out data from JSON file"""
        try:
            with open(self.opt_out_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"❌ Error loading opt-out data: {e}")
            # Return empty structure if file is corrupted
            return {
                "opt_outs": [],
                "metadata": {
                    "created": datetime.now().isoformat(),
                    "last_updated": datetime.now().isoformat(),
                    "total_opt_outs": 0,
                    "version": "1.0"
                }
            }
    
    def _save_opt_outs(self, data: Dict):
        """Save opt-out data to JSON file"""
        try:
            with open(self.opt_out_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logging.debug(f"💾 Saved opt-out data to {self.opt_out_file}")
        except Exception as e:
            logging.error(f"❌ Error saving opt-out data: {e}")
    
    def add_opt_out(self, email: str, email_types: List[str], source: str = "manual", 
                   ip_address: str = None, user_agent: str = None) -> bool:
        """Add or update an email opt-out"""
        try:
            data = self._load_opt_outs()
            email = email.lower().strip()
            
            # Find existing opt-out record
            existing_index = -1
            for i, record in enumerate(data["opt_outs"]):
                if record["email"] == email:
                    existing_index = i
                    break
            
            opt_out_record = {
                "email": email,
                "email_types": email_types,
                "opt_out_date": datetime.now().isoformat(),
                "source": source,
                "ip_address": ip_address,
                "user_agent": user_agent
            }
            
            if existing_index >= 0:
                # Update existing record
                data["opt_outs"][existing_index].update(opt_out_record)
                data["opt_outs"][existing_index]["updated_date"] = datetime.now().isoformat()
                logging.info(f"📧 Updated opt-out for {email}: {email_types}")
            else:
                # Add new record
                data["opt_outs"].append(opt_out_record)
                data["metadata"]["total_opt_outs"] += 1
                logging.info(f"📧 Added new opt-out for {email}: {email_types}")
            
            data["metadata"]["last_updated"] = datetime.now().isoformat()
            self._save_opt_outs(data)
            return True
            
        except Exception as e:
            logging.error(f"❌ Error adding opt-out for {email}: {e}")
            return False
    
    def is_opted_out(self, email: str, email_type: str = None) -> bool:
        """Check if an email address has opted out"""
        try:
            data = self._load_opt_outs()
            email = email.lower().strip()
            
            for record in data["opt_outs"]:
                if record["email"] == email:
                    opted_out_types = record.get("email_types", [])
                    
                    # Check for complete opt-out
                    if "all_emails" in opted_out_types:
                        return True
                    
                    # Check for specific email type
                    if email_type and email_type in opted_out_types:
                        return True
                    
                    # If no specific type provided, check if any opt-out exists
                    if not email_type and opted_out_types:
                        return True
            
            return False
            
        except Exception as e:
            logging.error(f"❌ Error checking opt-out status for {email}: {e}")
            # In case of error, err on the side of caution
            return True
    
    def get_opted_out_emails(self, email_type: str = None) -> Set[str]:
        """Get set of all opted-out email addresses for a specific type"""
        try:
            data = self._load_opt_outs()
            opted_out = set()
            
            for record in data["opt_outs"]:
                email = record["email"]
                opted_out_types = record.get("email_types", [])
                
                # Add if opted out of all emails
                if "all_emails" in opted_out_types:
                    opted_out.add(email)
                # Add if opted out of specific type
                elif email_type and email_type in opted_out_types:
                    opted_out.add(email)
                # Add if no specific type and any opt-out exists
                elif not email_type and opted_out_types:
                    opted_out.add(email)
            
            return opted_out
            
        except Exception as e:
            logging.error(f"❌ Error getting opted-out emails: {e}")
            return set()
    
    def remove_opt_out(self, email: str) -> bool:
        """Remove an email from the opt-out list (re-subscribe)"""
        try:
            data = self._load_opt_outs()
            email = email.lower().strip()
            
            original_count = len(data["opt_outs"])
            data["opt_outs"] = [record for record in data["opt_outs"] if record["email"] != email]
            
            if len(data["opt_outs"]) < original_count:
                data["metadata"]["total_opt_outs"] = len(data["opt_outs"])
                data["metadata"]["last_updated"] = datetime.now().isoformat()
                self._save_opt_outs(data)
                logging.info(f"📧 Removed opt-out for {email}")
                return True
            else:
                logging.info(f"📧 No opt-out found for {email}")
                return False
                
        except Exception as e:
            logging.error(f"❌ Error removing opt-out for {email}: {e}")
            return False
    
    def get_opt_out_stats(self) -> Dict:
        """Get statistics about opt-outs"""
        try:
            data = self._load_opt_outs()
            
            stats = {
                "total_opt_outs": len(data["opt_outs"]),
                "by_type": {},
                "by_source": {},
                "recent_opt_outs": 0
            }
            
            # Count recent opt-outs (last 7 days)
            seven_days_ago = datetime.now().timestamp() - (7 * 24 * 60 * 60)
            
            for record in data["opt_outs"]:
                # Count by email type
                for email_type in record.get("email_types", []):
                    stats["by_type"][email_type] = stats["by_type"].get(email_type, 0) + 1
                
                # Count by source
                source = record.get("source", "unknown")
                stats["by_source"][source] = stats["by_source"].get(source, 0) + 1
                
                # Count recent opt-outs
                try:
                    opt_out_date = datetime.fromisoformat(record.get("opt_out_date", ""))
                    if opt_out_date.timestamp() > seven_days_ago:
                        stats["recent_opt_outs"] += 1
                except:
                    pass
            
            return stats
            
        except Exception as e:
            logging.error(f"❌ Error getting opt-out stats: {e}")
            return {"total_opt_outs": 0, "by_type": {}, "by_source": {}, "recent_opt_outs": 0}
    
    def generate_opt_out_link(self, email: str, base_url: str = None) -> str:
        """Generate a personalized opt-out link"""
        if base_url is None:
            base_url = os.getenv('WEBSITE_BASE_URL', 'https://nullrecords.com')
        from urllib.parse import urlencode
        params = {"email": email}
        return f"{base_url.rstrip('/')}/unsubscribe.html?{urlencode(params)}"

# Global instance for easy importing
opt_out_manager = EmailOptOutManager()

def check_opt_out(email: str, email_type: str = None) -> bool:
    """Quick function to check if an email is opted out"""
    return opt_out_manager.is_opted_out(email, email_type)

def add_opt_out(email: str, email_types: List[str], source: str = "manual") -> bool:
    """Quick function to add an opt-out"""
    return opt_out_manager.add_opt_out(email, email_types, source)

def get_opt_out_link(email: str) -> str:
    """Quick function to generate opt-out link"""
    return opt_out_manager.generate_opt_out_link(email)

if __name__ == "__main__":
    # Command line interface for managing opt-outs
    import argparse
    
    parser = argparse.ArgumentParser(description='NullRecords Email Opt-Out Manager')
    parser.add_argument('--check', type=str, help='Check if email is opted out')
    parser.add_argument('--add', type=str, help='Add email to opt-out list')
    parser.add_argument('--types', type=str, nargs='+', default=['all_emails'], 
                       help='Email types to opt out from')
    parser.add_argument('--remove', type=str, help='Remove email from opt-out list')
    parser.add_argument('--stats', action='store_true', help='Show opt-out statistics')
    parser.add_argument('--list', action='store_true', help='List all opted-out emails')
    
    args = parser.parse_args()
    
    manager = EmailOptOutManager()
    
    if args.check:
        is_opted_out = manager.is_opted_out(args.check)
        print(f"Email {args.check}: {'OPTED OUT' if is_opted_out else 'OK TO SEND'}")
    
    elif args.add:
        success = manager.add_opt_out(args.add, args.types, "cli")
        print(f"{'✅' if success else '❌'} Add opt-out for {args.add}: {args.types}")
    
    elif args.remove:
        success = manager.remove_opt_out(args.remove)
        print(f"{'✅' if success else '❌'} Remove opt-out for {args.remove}")
    
    elif args.stats:
        stats = manager.get_opt_out_stats()
        print("📊 Opt-Out Statistics:")
        print(f"  Total opt-outs: {stats['total_opt_outs']}")
        print(f"  Recent (7 days): {stats['recent_opt_outs']}")
        print("  By type:")
        for email_type, count in stats['by_type'].items():
            print(f"    {email_type}: {count}")
        print("  By source:")
        for source, count in stats['by_source'].items():
            print(f"    {source}: {count}")
    
    elif args.list:
        opted_out = manager.get_opted_out_emails()
        print(f"📧 {len(opted_out)} opted-out email addresses:")
        for email in sorted(opted_out):
            print(f"  {email}")
    
    else:
        parser.print_help()
