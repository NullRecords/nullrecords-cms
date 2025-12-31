#!/bin/bash

# NullRecords Daily Report System Runner
# =====================================

set -e  # Exit on any error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Functions
print_header() {
    echo -e "${CYAN}📊 NullRecords Daily Report System${NC}"
    echo -e "${CYAN}===================================${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ️  $1${NC}"
}

check_dependencies() {
    print_info "Checking dependencies..."
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is required but not installed"
        exit 1
    fi
    
    # Check pip packages
    if ! python3 -c "import requests, bs4" 2>/dev/null; then
        print_info "Installing required Python packages..."
        pip3 install requests beautifulsoup4 python-dotenv
    fi
    
    # Check for Google API packages (optional)
    if ! python3 -c "import googleapiclient, google.oauth2" 2>/dev/null; then
        print_info "Google API packages not found - will use mock data"
        print_info "To enable real Google Analytics/YouTube data:"
        print_info "  pip3 install google-api-python-client google-auth"
    fi
    
    print_success "Dependencies checked"
}

load_environment() {
    # Load .env file if it exists
    if [[ -f ".env" ]]; then
        export $(grep -v '^#' .env | xargs)
        print_info "Loaded environment variables from .env file"
    fi
}

check_environment() {
    print_info "Checking environment configuration..."
    
    # Load environment first
    load_environment
    
    # Check for SMTP credentials (use same as outreach system)
    if [[ -z "${SMTP_USER}" || -z "${SMTP_PASSWORD}" || -z "${SMTP_SERVER}" || -z "${SENDER_EMAIL}" ]]; then
        print_error "SMTP credentials not found in environment"
        print_info "Please set SMTP_USER, SMTP_PASSWORD, SMTP_SERVER, and SENDER_EMAIL in .env file"
        print_info "(These are the same credentials used by the outreach system)"
        return 1
    fi
    
    # Check for Google Analytics (optional)
    if [[ -z "${GA_VIEW_ID}" ]]; then
        print_info "GA_VIEW_ID not set - will use mock analytics data"
    fi
    
    # Check for YouTube API (optional)
    if [[ -z "${YOUTUBE_API_KEY}" ]]; then
        print_info "YOUTUBE_API_KEY not set - will use mock YouTube data"
    fi
    
    print_success "Environment configuration checked"
}

generate_report() {
    print_info "Generating daily report..."
    python3 scripts/daily_report.py
}

send_report_email() {
    print_info "Generating and sending daily report email..."
    python3 scripts/daily_report.py --send-email
}

generate_historical_report() {
    local date="$1"
    print_info "Generating historical report for $date..."
    python3 scripts/daily_report.py --date "$date"
}

view_recent_reports() {
    print_info "Recent daily reports:"
    echo ""
    
    # List recent HTML reports
    for report in daily_report_*.html; do
        if [[ -f "$report" ]]; then
            # Extract date from filename
            date=$(echo "$report" | sed 's/daily_report_//' | sed 's/.html//')
            size=$(ls -lh "$report" | awk '{print $5}')
            modified=$(ls -l "$report" | awk '{print $6, $7, $8}')
            
            echo -e "📊 ${BLUE}$date${NC} - $size - $modified"
        fi
    done
    
    echo ""
    print_info "To view a report: open daily_report_YYYY-MM-DD.html"
}

setup_cron_job() {
    print_info "Setting up daily report cron job..."
    
    # Create cron entry
    cron_entry="0 8 * * * cd $SCRIPT_DIR && ./daily_report_system.sh email >/dev/null 2>&1"
    
    # Check if cron job already exists
    if crontab -l 2>/dev/null | grep -q "daily_report_system.sh"; then
        print_info "Daily report cron job already exists"
    else
        # Add to crontab
        (crontab -l 2>/dev/null; echo "$cron_entry") | crontab -
        print_success "Daily report cron job added - will run at 8:00 AM daily"
    fi
    
    # Show current cron jobs
    print_info "Current cron jobs:"
    crontab -l 2>/dev/null | grep -E "(daily_report|news_system)" || echo "No automated jobs found"
}

show_sample_env() {
    print_info "Sample .env configuration for daily reports:"
    echo ""
    cat << 'EOF'
# SMTP Configuration (required for email reports)
SMTP_SERVER=your_smtp_server
SMTP_PORT=587
SMTP_USER=your_smtp_username
SMTP_PASSWORD=your_smtp_password
SENDER_EMAIL=your_sender_email
DAILY_REPORT_EMAIL=your_recipient_email
BCC_EMAIL=your_bcc_email

# Google Analytics (optional - will use mock data if not provided)
GOOGLE_SERVICE_ACCOUNT_PATH=/path/to/service-account-key.json
GA_VIEW_ID=your_ga_view_id

# YouTube API (optional - will use mock data if not provided)
YOUTUBE_API_KEY=your_youtube_api_key
YOUTUBE_CHANNEL_ID=your_channel_id

# Google Sheets API (optional - for voting data)
GOOGLE_SHEETS_ID=your_sheets_id
EOF
    echo ""
}

# Main execution
case "${1:-help}" in
    "generate")
        print_header
        check_dependencies
        check_environment
        generate_report
        ;;
    "email")
        print_header
        check_dependencies
        check_environment
        send_report_email
        ;;
    "history")
        if [[ -n "$2" ]]; then
            print_header
            check_dependencies
            generate_historical_report "$2"
        else
            print_error "Please specify a date: ./daily_report_system.sh history 2025-01-15"
        fi
        ;;
    "list")
        print_header
        view_recent_reports
        ;;
    "setup-cron")
        print_header
        setup_cron_job
        ;;
    "env")
        print_header
        show_sample_env
        ;;
    "test")
        print_header
        check_dependencies
        check_environment
        print_info "Running test report generation..."
        python3 scripts/daily_report.py
        print_success "Test completed - check daily_report_*.html file"
        ;;
    "help"|*)
        print_header
        echo ""
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  generate     - Generate daily report (HTML file only)"
        echo "  email        - Generate and send daily report via email"
        echo "  history DATE - Generate historical report for specific date (YYYY-MM-DD)"
        echo "  list         - List recent daily reports"
        echo "  setup-cron   - Set up automated daily email reports"
        echo "  env          - Show sample environment configuration"
        echo "  test         - Test report generation with current setup"
        echo "  help         - Show this help message"
        echo ""
        echo "Examples:"
        echo "  $0 email               # Generate and email today's report"
        echo "  $0 history 2025-01-15  # Generate report for specific date"
        echo "  $0 setup-cron          # Set up automated daily emails"
        echo ""
        echo "Environment Setup:"
        echo "  1. Create .env file with SMTP credentials"
        echo "  2. (Optional) Add Google Analytics/YouTube API keys"
        echo "  3. Run: $0 test"
        echo "  4. Run: $0 setup-cron"
        echo ""
        ;;
esac
