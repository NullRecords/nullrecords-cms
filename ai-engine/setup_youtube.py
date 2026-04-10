#!/usr/bin/env python3
"""YouTube OAuth Setup Script for NullRecords AI Engine.

This script helps you configure YouTube API access for automatic video uploads.

Usage:
    python setup_youtube.py

Requirements:
    1. A Google Cloud project with YouTube Data API v3 enabled
    2. OAuth 2.0 credentials (Desktop app type)
"""

import json
import os
import sys
import webbrowser
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

ENV_FILE = Path(__file__).parent / ".env"
TOKENS_FILE = Path(__file__).parent / ".youtube_tokens.json"

CONSOLE_URL = "https://console.cloud.google.com/apis/credentials"
API_ENABLE_URL = "https://console.cloud.google.com/apis/library/youtube.googleapis.com"

BANNER = """
╔══════════════════════════════════════════════════════════════════════╗
║          NULLRECORDS AI ENGINE — YOUTUBE SETUP                       ║
╠══════════════════════════════════════════════════════════════════════╣
║  This script will configure YouTube API access for auto-uploading    ║
║  daily shorts and videos to your YouTube channel.                    ║
╚══════════════════════════════════════════════════════════════════════╝
"""


def print_step(num, text):
    print(f"\n{'─'*60}")
    print(f"  STEP {num}: {text}")
    print(f"{'─'*60}")


def read_env():
    """Read existing .env file into a dict."""
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                env[key.strip()] = value.strip()
    return env


def write_env(env):
    """Write env dict back to .env file, preserving comments."""
    lines = []
    if ENV_FILE.exists():
        existing_keys = set()
        for line in ENV_FILE.read_text().splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and "=" in stripped:
                key = stripped.split("=")[0].strip()
                if key in env:
                    lines.append(f"{key}={env[key]}")
                    existing_keys.add(key)
                else:
                    lines.append(line)
            else:
                lines.append(line)
        # Add new keys
        for key, value in env.items():
            if key not in existing_keys:
                lines.append(f"{key}={value}")
    else:
        lines = [f"{k}={v}" for k, v in env.items()]
    
    ENV_FILE.write_text("\n".join(lines) + "\n")


def check_existing():
    """Check if YouTube is already configured."""
    env = read_env()
    has_client_id = bool(env.get("YOUTUBE_CLIENT_ID"))
    has_client_secret = bool(env.get("YOUTUBE_CLIENT_SECRET"))
    has_tokens = TOKENS_FILE.exists()
    
    if has_tokens:
        tokens = json.loads(TOKENS_FILE.read_text())
        if tokens.get("refresh_token"):
            print("\n✅ YouTube is already configured and authorized!")
            print(f"   Tokens file: {TOKENS_FILE}")
            response = input("\n   Reconfigure anyway? [y/N]: ").strip().lower()
            if response != "y":
                return False
    
    if has_client_id and has_client_secret:
        print("\n📋 Found existing OAuth credentials in .env")
        print(f"   Client ID: {env['YOUTUBE_CLIENT_ID'][:20]}...")
        response = input("\n   Use existing credentials? [Y/n]: ").strip().lower()
        if response != "n":
            return "use_existing"
    
    return True


def setup_credentials():
    """Guide user through setting up OAuth credentials."""
    print_step(1, "Enable YouTube Data API v3")
    print("""
    First, enable the YouTube Data API in your Google Cloud project:
    
    1. Go to: https://console.cloud.google.com/apis/library/youtube.googleapis.com
    2. Select your project (or create one)
    3. Click "ENABLE"
    """)
    
    input("    Press Enter when done...")
    
    print_step(2, "Create OAuth Credentials")
    print(f"""
    Now create OAuth 2.0 credentials:
    
    1. Go to: {CONSOLE_URL}
    2. Click "+ CREATE CREDENTIALS" → "OAuth client ID"
    3. Application type: "Desktop app"
    4. Name: "NullRecords AI Engine" (or anything you like)
    5. Click "CREATE"
    6. Copy the Client ID and Client Secret
    """)
    
    open_browser = input("    Open Google Cloud Console in browser? [Y/n]: ").strip().lower()
    if open_browser != "n":
        webbrowser.open(CONSOLE_URL)
    
    print("\n    Enter your OAuth credentials:")
    client_id = input("    Client ID: ").strip()
    client_secret = input("    Client Secret: ").strip()
    
    if not client_id or not client_secret:
        print("\n❌ Both Client ID and Client Secret are required.")
        sys.exit(1)
    
    # Save to .env
    env = read_env()
    env["YOUTUBE_CLIENT_ID"] = client_id
    env["YOUTUBE_CLIENT_SECRET"] = client_secret
    write_env(env)
    
    print(f"\n✅ Credentials saved to {ENV_FILE}")
    return client_id, client_secret


def authorize(client_id, client_secret):
    """Run OAuth authorization flow."""
    print_step(3, "Authorize YouTube Access")
    
    import requests
    
    REDIRECT_PORT = 8765
    REDIRECT_URI = f"http://localhost:{REDIRECT_PORT}"
    SCOPES = "https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube"
    
    auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={client_id}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&response_type=code"
        f"&scope={SCOPES}"
        f"&access_type=offline"
        f"&prompt=consent"
    )
    
    print(f"""
    A browser window will open for you to authorize YouTube access.
    
    1. Sign in with the Google account that owns your YouTube channel
    2. Click "Allow" to grant upload permissions
    3. You'll be redirected back here automatically
    """)
    
    input("    Press Enter to open the authorization page...")
    
    # Callback handler
    auth_code = None
    
    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            nonlocal auth_code
            query = parse_qs(urlparse(self.path).query)
            auth_code = query.get("code", [None])[0]
            
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            
            if auth_code:
                self.wfile.write(b"""
                <html><body style="font-family:system-ui;text-align:center;padding:50px">
                <h1 style="color:#00ff41">&#10004; Authorization Successful!</h1>
                <p>You can close this window and return to the terminal.</p>
                </body></html>
                """)
            else:
                error = query.get("error", ["Unknown error"])[0]
                self.wfile.write(f"""
                <html><body style="font-family:system-ui;text-align:center;padding:50px">
                <h1 style="color:#ff5555">&#10008; Authorization Failed</h1>
                <p>Error: {error}</p>
                </body></html>
                """.encode())
        
        def log_message(self, format, *args):
            pass  # Suppress HTTP logs
    
    # Start callback server
    server = HTTPServer(("localhost", REDIRECT_PORT), CallbackHandler)
    server.timeout = 300  # 5 minute timeout
    
    webbrowser.open(auth_url)
    print(f"\n    Waiting for authorization (timeout: 5 minutes)...")
    
    server.handle_request()
    server.server_close()
    
    if not auth_code:
        print("\n❌ Authorization failed or was cancelled.")
        sys.exit(1)
    
    print("\n    Exchanging code for tokens...")
    
    # Exchange code for tokens
    token_resp = requests.post("https://oauth2.googleapis.com/token", data={
        "code": auth_code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    }, timeout=30)
    
    if not token_resp.ok:
        print(f"\n❌ Token exchange failed: {token_resp.text}")
        sys.exit(1)
    
    tokens = token_resp.json()
    TOKENS_FILE.write_text(json.dumps(tokens, indent=2))
    
    print(f"\n✅ Tokens saved to {TOKENS_FILE}")
    return tokens


def test_upload():
    """Test that uploads work."""
    print_step(4, "Test Upload Capability")
    
    try:
        from app.services.social.youtube import is_authenticated, _get_access_token
        
        if not is_authenticated():
            print("\n❌ Authentication check failed")
            return False
        
        token = _get_access_token()
        print(f"\n✅ Access token obtained successfully!")
        print(f"   Token prefix: {token[:20]}...")
        
        # Test API access
        import requests
        resp = requests.get(
            "https://www.googleapis.com/youtube/v3/channels",
            params={"part": "snippet", "mine": "true"},
            headers={"Authorization": f"Bearer {token}"},
            timeout=30
        )
        
        if resp.ok:
            data = resp.json()
            items = data.get("items", [])
            if items:
                channel = items[0]["snippet"]
                print(f"\n✅ Connected to YouTube channel: {channel['title']}")
                return True
            else:
                print("\n⚠️  No YouTube channels found for this account")
                print("    Make sure you authorized with the correct Google account.")
        else:
            print(f"\n❌ API test failed: {resp.status_code} - {resp.text[:200]}")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
    
    return False


def main():
    print(BANNER)
    
    result = check_existing()
    if result is False:
        print("\nSetup cancelled.")
        return
    
    if result == "use_existing":
        env = read_env()
        client_id = env["YOUTUBE_CLIENT_ID"]
        client_secret = env["YOUTUBE_CLIENT_SECRET"]
    else:
        client_id, client_secret = setup_credentials()
    
    authorize(client_id, client_secret)
    
    if test_upload():
        print(f"""
{'═'*60}
  ✅ YOUTUBE SETUP COMPLETE!
{'═'*60}

  Your AI Engine can now automatically upload videos to YouTube.
  
  Videos in the daily shorts queue with status 'approved' will
  be posted at 10:00, 14:00, and 18:00 UTC.
  
  To manually trigger posting:
    curl -X POST http://localhost:8009/video/daily-shorts/post-now
  
  To check queue status:
    http://localhost:8009/admin#video → Daily Shorts tab
    
{'═'*60}
""")
    else:
        print("""
⚠️  Setup completed but test failed. You may need to:
    1. Verify the YouTube Data API is enabled
    2. Check that your Google account has a YouTube channel
    3. Try running this script again
""")


if __name__ == "__main__":
    main()
