#!/bin/bash

# NullRecords News Monitoring System Runner
# ========================================

set -e  # Exit on any error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
print_header() {
    echo -e "${BLUE}🎵 NullRecords News Monitoring System${NC}"
    echo -e "${BLUE}=====================================${NC}"
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
    
    print_success "Dependencies checked"
}

run_news_collection() {
    print_info "Collecting news articles..."
    python3 news_monitor.py --collect
}

monitor_releases() {
    print_info "Monitoring streaming platforms for new releases..."
    python3 news_monitor.py --releases
}

generate_pages() {
    print_info "Generating HTML pages..."
    python3 news_monitor.py --generate
}

update_main_site() {
    print_info "Updating main site news section..."
    python3 news_monitor.py --update-site
}

show_report() {
    print_info "Generating monitoring report..."
    python3 news_monitor.py --report
}

deploy_changes() {
    print_info "Deploying changes to GitHub..."
    
    # Check if there are changes to commit
    if git diff --quiet && git diff --staged --quiet; then
        print_info "No changes to deploy"
        return
    fi
    
    # Add all changes
    git add .
    
    # Commit with timestamp
    commit_msg="Update news content - $(date '+%Y-%m-%d %H:%M')"
    git commit -m "$commit_msg

- Automated news collection and page generation
- Updated SYSTEM_UPDATE.LOG with latest articles
- Generated individual article pages
- Refreshed main site news section"
    
    # Push to GitHub
    git push origin main
    
    print_success "Changes deployed to GitHub Pages"
}

# Main execution
case "${1:-help}" in
    "collect")
        print_header
        check_dependencies
        run_news_collection
        ;;
    "releases")
        print_header
        check_dependencies
        monitor_releases
        ;;
    "generate")
        print_header
        check_dependencies
        generate_pages
        ;;
    "update")
        print_header
        check_dependencies
        update_main_site
        ;;
    "report")
        print_header
        check_dependencies
        show_report
        ;;
    "full")
        print_header
        check_dependencies
        run_news_collection
        monitor_releases
        generate_pages
        update_main_site
        show_report
        ;;
    "deploy")
        print_header
        check_dependencies
        run_news_collection
        monitor_releases
        generate_pages
        update_main_site
        deploy_changes
        ;;
    "help"|*)
        print_header
        echo ""
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  collect   - Collect new news articles about NullRecords artists"
        echo "  releases  - Monitor streaming platforms for new releases"
        echo "  generate  - Generate HTML pages for all collected articles"
        echo "  update    - Update main site news section"
        echo "  report    - Show monitoring and statistics report"
        echo "  full      - Run collect, releases, generate, update, and report"
        echo "  deploy    - Run full process and deploy to GitHub Pages"
        echo "  help      - Show this help message"
        echo ""
        echo "Examples:"
        echo "  $0 collect    # Just collect new articles"
        echo "  $0 full       # Complete news update cycle"
        echo "  $0 deploy     # Full update + deploy to live site"
        echo ""
        ;;
esac
