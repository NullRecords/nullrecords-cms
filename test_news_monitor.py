#!/usr/bin/env python3

import os
import sys

# Add current directory to path
sys.path.insert(0, os.getcwd())

try:
    print("Testing basic imports...")
    import json
    print("✅ json imported")
    
    import time
    print("✅ time imported")
    
    import requests
    print("✅ requests imported")
    
    from bs4 import BeautifulSoup
    print("✅ BeautifulSoup imported")
    
    print("Testing news monitor import...")
    from scripts.news_monitor import NewsMonitor
    print("✅ NewsMonitor imported")
    
    print("Creating NewsMonitor instance...")
    monitor = NewsMonitor()
    print("✅ NewsMonitor created")
    
    print(f"Loaded {len(monitor.articles)} articles")
    print(f"Configured {len(monitor.search_sources)} sources")
    
    # Show first few sources
    print("\nFirst 5 sources:")
    for i, source in enumerate(monitor.search_sources[:5]):
        print(f"  {i+1}. {source['name']} ({source['type']})")
    
    print("\nTest completed successfully!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
