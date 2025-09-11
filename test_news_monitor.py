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
    # Import the class directly without instantiating
    from scripts.news_monitor import NewsArticle
    print("✅ NewsArticle imported")
    
    # Create a test article
    test_article = NewsArticle(
        id="test123",
        title="Test Article",
        content="Test content about My Evil Robot Army",
        source="Test Source",
        url="https://example.com"
    )
    print("✅ NewsArticle created")
    
    print("Test completed successfully! News monitor classes are working.")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
