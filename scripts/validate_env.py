#!/usr/bin/env python3
"""
Environment Configuration Validator
==================================

Validates that all required environment variables are properly configured
and no hardcoded values are being used in production.

Usage: python validate_env.py
"""

import os
import sys
from typing import List, Dict, Optional

# Load environment variables
try:
    from dotenv import load_dotenv
    if os.path.exists('.env'):
        load_dotenv('.env')
        print("✅ Loaded .env file")
    else:
        print("⚠️  No .env file found")
except ImportError:
    print("⚠️  python-dotenv not installed")

class EnvironmentValidator:
    """Validates environment configuration"""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.required_vars = {
            'SMTP_SERVER': 'SMTP server hostname',
            'SMTP_USER': 'SMTP username/login',
            'SMTP_PASSWORD': 'SMTP password',
            'SENDER_EMAIL': 'Email address to send from',
            'BCC_EMAIL': 'Email address for BCC notifications'
        }
        
        self.optional_vars = {
            'SMTP_PORT': 'SMTP port (default: 587)',
            'DAILY_REPORT_EMAIL': 'Email for daily reports',
            'NOTIFICATION_EMAIL': 'Email for notifications',
            'WEBSITE_BASE_URL': 'Base URL for the website (default: https://nullrecords.com)',
            'CONTACT_EMAIL': 'Contact email address (default: team@nullrecords.com)',
            'GOOGLE_SERVICE_ACCOUNT_PATH': 'Path to Google service account JSON',
            'GA_VIEW_ID': 'Google Analytics view ID',
            'YOUTUBE_API_KEY': 'YouTube Data API key',
            'YOUTUBE_CHANNEL_ID': 'YouTube channel ID',
            'GOOGLE_SHEETS_ID': 'Google Sheets ID for voting data',
            'VOTING_SHEET_NAME': 'Name of voting sheet tab',
            'BREVO_API_KEY': 'Brevo API key for detailed metrics'
        }
        
        self.forbidden_values = [
            'your_smtp_server',
            'your_smtp_username', 
            'your_smtp_password',
            'your_sender_email',
            'your_team_email',
            'your_brevo_username',
            'your_brevo_password',
            'your_actual_value',
            'smtp.your-provider.com',
            'outreach@yourdomain.com'
        ]
    
    def validate_required_vars(self):
        """Check all required environment variables"""
        print("\n🔍 Checking Required Environment Variables:")
        print("=" * 50)
        
        for var, description in self.required_vars.items():
            value = os.getenv(var)
            
            if not value:
                self.errors.append(f"❌ {var} is not set ({description})")
                print(f"❌ {var}: NOT SET")
            elif value.lower() in [v.lower() for v in self.forbidden_values]:
                self.errors.append(f"❌ {var} contains placeholder value: {value}")
                print(f"❌ {var}: PLACEHOLDER VALUE")
            else:
                print(f"✅ {var}: SET")
    
    def validate_optional_vars(self):
        """Check optional environment variables"""
        print("\n🔍 Checking Optional Environment Variables:")
        print("=" * 50)
        
        for var, description in self.optional_vars.items():
            value = os.getenv(var)
            
            if not value:
                print(f"⚠️  {var}: NOT SET ({description})")
            elif value.lower() in [v.lower() for v in self.forbidden_values]:
                self.warnings.append(f"⚠️  {var} contains placeholder value: {value}")
                print(f"⚠️  {var}: PLACEHOLDER VALUE")
            else:
                print(f"✅ {var}: SET")
    
    def validate_email_format(self):
        """Basic email format validation"""
        print("\n📧 Validating Email Formats:")
        print("=" * 30)
        
        email_vars = ['SENDER_EMAIL', 'BCC_EMAIL', 'DAILY_REPORT_EMAIL', 'NOTIFICATION_EMAIL']
        
        for var in email_vars:
            value = os.getenv(var)
            
            if value:
                if '@' not in value or '.' not in value.split('@')[-1]:
                    self.errors.append(f"❌ {var} is not a valid email format: {value}")
                    print(f"❌ {var}: INVALID FORMAT")
                else:
                    print(f"✅ {var}: VALID FORMAT")
            elif var in self.required_vars:
                # Already reported as missing in required vars
                pass
            else:
                print(f"⚠️  {var}: NOT SET")
    
    def validate_file_paths(self):
        """Check that file paths exist"""
        print("\n📁 Validating File Paths:")
        print("=" * 25)
        
        path_vars = ['GOOGLE_SERVICE_ACCOUNT_PATH']
        
        for var in path_vars:
            value = os.getenv(var)
            
            if value:
                if os.path.exists(value):
                    print(f"✅ {var}: FILE EXISTS")
                else:
                    self.warnings.append(f"⚠️  {var} file does not exist: {value}")
                    print(f"⚠️  {var}: FILE NOT FOUND")
            else:
                print(f"⚠️  {var}: NOT SET (will use mock data)")
    
    def test_smtp_connection(self):
        """Test SMTP connection (optional)"""
        print("\n🔌 Testing SMTP Connection:")
        print("=" * 28)
        
        smtp_server = os.getenv('SMTP_SERVER')
        smtp_port = int(os.getenv('SMTP_PORT', '587'))
        smtp_user = os.getenv('SMTP_USER')
        smtp_password = os.getenv('SMTP_PASSWORD')
        
        if not all([smtp_server, smtp_user, smtp_password]):
            print("⚠️  SMTP not configured - skipping connection test")
            return
        
        try:
            import smtplib
            
            print(f"🔌 Connecting to {smtp_server}:{smtp_port}...")
            
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_password)
                print("✅ SMTP connection successful")
                
        except ImportError:
            print("⚠️  smtplib not available - skipping connection test")
        except Exception as e:
            self.errors.append(f"❌ SMTP connection failed: {e}")
            print(f"❌ SMTP connection failed: {e}")
    
    def generate_summary(self):
        """Generate validation summary"""
        print("\n" + "=" * 60)
        print("📊 VALIDATION SUMMARY")
        print("=" * 60)
        
        if not self.errors and not self.warnings:
            print("🎉 All environment variables are properly configured!")
            print("✅ Ready for production use")
            return True
        
        if self.errors:
            print(f"❌ {len(self.errors)} CRITICAL ERRORS found:")
            for error in self.errors:
                print(f"   {error}")
            print()
        
        if self.warnings:
            print(f"⚠️  {len(self.warnings)} WARNINGS found:")
            for warning in self.warnings:
                print(f"   {warning}")
            print()
        
        if self.errors:
            print("🚫 CONFIGURATION INVALID - Fix errors before proceeding")
            return False
        else:
            print("⚠️  CONFIGURATION INCOMPLETE - Some optional features may not work")
            return True
    
    def generate_setup_guide(self):
        """Generate setup instructions"""
        if self.errors:
            print("\n🛠️  SETUP INSTRUCTIONS:")
            print("=" * 25)
            print("1. Copy .env.template to .env:")
            print("   cp .env.template .env")
            print()
            print("2. Edit .env file and replace placeholder values:")
            for var in self.required_vars:
                if not os.getenv(var) or os.getenv(var).lower() in [v.lower() for v in self.forbidden_values]:
                    print(f"   {var}=your_actual_value")
            print()
            print("3. Run validation again:")
            print("   python validate_env.py")
            print()
            print("4. Test systems:")
            print("   ./daily_report_system.sh test")
            print("   python music_outreach.py --test")

def main():
    """Main validation function"""
    print("🔍 NullRecords Environment Configuration Validator")
    print("=" * 55)
    
    validator = EnvironmentValidator()
    
    # Run all validations
    validator.validate_required_vars()
    validator.validate_optional_vars()
    validator.validate_email_format()
    validator.validate_file_paths()
    validator.test_smtp_connection()
    
    # Generate summary
    is_valid = validator.generate_summary()
    
    # Show setup guide if needed
    if not is_valid:
        validator.generate_setup_guide()
    
    # Exit with appropriate code
    sys.exit(0 if is_valid else 1)

if __name__ == "__main__":
    main()
