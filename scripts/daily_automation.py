#!/usr/bin/env python3
"""
NullRecords Daily Automation Script

This script runs the complete daily automation sequence:
1. Run outreach activities (discovery, sending emails)
2. Collect all metrics and progress data
3. Send comprehensive daily report with real activity results

This ensures the daily report shows actual progress and activity
rather than starting the day with empty metrics.
"""

import sys
import os
import subprocess
import logging
import argparse
from datetime import datetime

# Add project root to path to import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
try:
    from dotenv import load_dotenv
    # Try to find .env file in current directory or parent directory
    env_paths = ['.env', '../.env', os.path.join(os.path.dirname(__file__), '..', '.env')]
    env_loaded = False
    for env_path in env_paths:
        if os.path.exists(env_path):
            load_dotenv(env_path)
            logging.info(f"✅ Environment variables loaded from {env_path}")
            env_loaded = True
            break
    
    # If not found in relative paths, try absolute path to workspace root
    if not env_loaded:
        workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        env_path = os.path.join(workspace_root, '.env')
        if os.path.exists(env_path):
            load_dotenv(env_path)
            logging.info(f"✅ Environment variables loaded from {env_path}")
            env_loaded = True
    
    if not env_loaded:
        logging.warning("⚠️  .env file not found in expected locations")
except ImportError:
    logging.warning("⚠️  python-dotenv not installed - using system environment variables only")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs', 'daily_automation.log'), mode='a')
    ]
)

class DailyAutomationSystem:
    """Manages the complete daily automation sequence"""
    
    def __init__(self):
        self.start_time = datetime.now()
        self.results = {
            'outreach_discovery': {'success': False, 'new_sources': 0, 'errors': []},
            'outreach_emails': {'success': False, 'emails_sent': 0, 'errors': []},
            'daily_report': {'success': False, 'errors': []}
        }
        
    def run_outreach_discovery(self, max_new_sources=5):
        """Run outreach discovery to find new contacts"""
        logging.info("🔍 Step 1: Running outreach discovery...")
        
        try:
            # Run discovery to find new music industry contacts
            result = subprocess.run([
                sys.executable, 'scripts/music_outreach.py', '--discover'
            ], capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                output = result.stdout
                logging.info(f"✅ Discovery completed: {output.strip()}")
                
                # Parse discovery results
                if "Discovered" in output:
                    # Extract number of new sources discovered
                    for line in output.split('\n'):
                        if "Discovered" in line and "new contacts" in line:
                            try:
                                new_sources = int(line.split()[1])
                                self.results['outreach_discovery']['new_sources'] = new_sources
                            except (ValueError, IndexError):
                                pass
                
                self.results['outreach_discovery']['success'] = True
                return True
            else:
                error_msg = f"Discovery failed with return code {result.returncode}: {result.stderr}"
                logging.error(f"❌ {error_msg}")
                self.results['outreach_discovery']['errors'].append(error_msg)
                return False
                
        except subprocess.TimeoutExpired:
            error_msg = "Discovery timed out after 5 minutes"
            logging.error(f"❌ {error_msg}")
            self.results['outreach_discovery']['errors'].append(error_msg)
            return False
        except Exception as e:
            error_msg = f"Discovery error: {e}"
            logging.error(f"❌ {error_msg}")
            self.results['outreach_discovery']['errors'].append(error_msg)
            return False
    
    def run_daily_outreach(self, limit=None):
        """Run daily outreach to send emails to contacts"""
        logging.info("📧 Step 2: Running daily outreach emails...")
        
        try:
            # Get daily limit from environment or use default
            if not limit:
                limit = int(os.getenv('MAX_DAILY_OUTREACH', '10'))
            
            # Run daily outreach with limit
            cmd = [sys.executable, 'scripts/music_outreach.py', '--daily']
            if limit:
                cmd.extend(['--limit', str(limit)])
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            
            if result.returncode == 0:
                output = result.stdout
                logging.info(f"✅ Outreach completed: {output.strip()}")
                
                # Parse outreach results to count emails sent
                emails_sent = 0
                for line in output.split('\n'):
                    if "emails sent" in line.lower():
                        try:
                            # Try to extract number of emails sent
                            words = line.split()
                            for i, word in enumerate(words):
                                if word.isdigit() and i < len(words) - 1:
                                    if "email" in words[i+1].lower():
                                        emails_sent = max(emails_sent, int(word))
                        except (ValueError, IndexError):
                            pass
                
                self.results['outreach_emails']['emails_sent'] = emails_sent
                self.results['outreach_emails']['success'] = True
                return True
            else:
                error_msg = f"Outreach failed with return code {result.returncode}: {result.stderr}"
                logging.error(f"❌ {error_msg}")
                self.results['outreach_emails']['errors'].append(error_msg)
                return False
                
        except subprocess.TimeoutExpired:
            error_msg = "Outreach timed out after 10 minutes"
            logging.error(f"❌ {error_msg}")
            self.results['outreach_emails']['errors'].append(error_msg)
            return False
        except Exception as e:
            error_msg = f"Outreach error: {e}"
            logging.error(f"❌ {error_msg}")
            self.results['outreach_emails']['errors'].append(error_msg)
            return False
    
    def send_daily_report(self):
        """Send daily report with all collected metrics"""
        logging.info("📊 Step 3: Sending daily report with activity results...")
        
        try:
            # Run daily report generation and email
            result = subprocess.run([
                sys.executable, 'scripts/daily_report.py', '--send-email'
            ], capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                output = result.stdout
                logging.info(f"✅ Daily report sent: {output.strip()}")
                self.results['daily_report']['success'] = True
                return True
            else:
                error_msg = f"Daily report failed with return code {result.returncode}: {result.stderr}"
                logging.error(f"❌ {error_msg}")
                self.results['daily_report']['errors'].append(error_msg)
                return False
                
        except subprocess.TimeoutExpired:
            error_msg = "Daily report timed out after 5 minutes"
            logging.error(f"❌ {error_msg}")
            self.results['daily_report']['errors'].append(error_msg)
            return False
        except Exception as e:
            error_msg = f"Daily report error: {e}"
            logging.error(f"❌ {error_msg}")
            self.results['daily_report']['errors'].append(error_msg)
            return False
    
    def run_complete_automation(self, discovery=True, outreach=True, report=True, outreach_limit=None):
        """Run the complete daily automation sequence"""
        logging.info("🚀 Starting NullRecords Daily Automation Sequence")
        logging.info(f"⏰ Started at: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        success_count = 0
        total_steps = sum([discovery, outreach, report])
        
        # Step 1: Discovery (optional)
        if discovery:
            if self.run_outreach_discovery():
                success_count += 1
                logging.info(f"✅ Discovery: Found {self.results['outreach_discovery']['new_sources']} new sources")
            else:
                logging.error("❌ Discovery failed")
        
        # Step 2: Daily Outreach (optional)
        if outreach:
            if self.run_daily_outreach(limit=outreach_limit):
                success_count += 1
                logging.info(f"✅ Outreach: Sent {self.results['outreach_emails']['emails_sent']} emails")
            else:
                logging.error("❌ Outreach failed")
        
        # Step 3: Daily Report (should always run to report progress)
        if report:
            if self.send_daily_report():
                success_count += 1
                logging.info("✅ Daily report sent with activity results")
            else:
                logging.error("❌ Daily report failed")
        
        # Summary
        end_time = datetime.now()
        duration = end_time - self.start_time
        
        logging.info(f"🏁 Daily automation completed")
        logging.info(f"📊 Success rate: {success_count}/{total_steps} steps completed")
        logging.info(f"⏱️  Total duration: {duration.total_seconds():.1f} seconds")
        
        # Print summary
        print(f"\n🎵 NULLRECORDS DAILY AUTOMATION SUMMARY")
        print(f"{'='*50}")
        print(f"📅 Date: {self.start_time.strftime('%Y-%m-%d')}")
        print(f"⏰ Duration: {duration.total_seconds():.1f} seconds")
        print(f"✅ Success Rate: {success_count}/{total_steps} steps")
        print()
        
        if discovery:
            status = "✅" if self.results['outreach_discovery']['success'] else "❌"
            new_sources = self.results['outreach_discovery']['new_sources']
            print(f"{status} Discovery: {new_sources} new sources found")
        
        if outreach:
            status = "✅" if self.results['outreach_emails']['success'] else "❌"
            emails_sent = self.results['outreach_emails']['emails_sent']
            print(f"{status} Outreach: {emails_sent} emails sent")
        
        if report:
            status = "✅" if self.results['daily_report']['success'] else "❌"
            print(f"{status} Daily Report: Sent with activity metrics")
        
        print()
        
        return success_count == total_steps

def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(description='NullRecords Daily Automation System')
    parser.add_argument('--skip-discovery', action='store_true', help='Skip outreach discovery')
    parser.add_argument('--skip-outreach', action='store_true', help='Skip daily outreach emails')
    parser.add_argument('--skip-report', action='store_true', help='Skip daily report (not recommended)')
    parser.add_argument('--outreach-limit', type=int, help='Limit number of outreach emails', default=None)
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without executing')
    
    args = parser.parse_args()
    
    if args.dry_run:
        print("🔍 DRY RUN - Daily Automation Sequence:")
        print("1. 🔍 Outreach Discovery" + (" (SKIPPED)" if args.skip_discovery else ""))
        print("2. 📧 Daily Outreach" + (" (SKIPPED)" if args.skip_outreach else f" (limit: {args.outreach_limit or 'default'})"))
        print("3. 📊 Daily Report" + (" (SKIPPED)" if args.skip_report else ""))
        return
    
    # Run automation
    automation = DailyAutomationSystem()
    success = automation.run_complete_automation(
        discovery=not args.skip_discovery,
        outreach=not args.skip_outreach,
        report=not args.skip_report,
        outreach_limit=args.outreach_limit
    )
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()