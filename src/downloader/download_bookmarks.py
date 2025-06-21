import requests
import json
import time
import os
import base64
import hashlib
import secrets
import urllib.parse
import webbrowser
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timedelta

class CallbackHandler(BaseHTTPRequestHandler):
    """HTTP request handler for OAuth callback"""
    
    def do_GET(self):
        """Handle GET request to callback URL"""
        parsed_url = urlparse(self.path)
        query_params = parse_qs(parsed_url.query)
        
        # Extract authorization code and state
        auth_code = query_params.get('code', [None])[0]
        state = query_params.get('state', [None])[0]
        error = query_params.get('error', [None])[0]
        
        if error:
            self.server.auth_result = {'error': error, 'error_description': query_params.get('error_description', ['Unknown error'])[0]}
            response_html = """
            <html><body>
            <h2>❌ Authorization Failed</h2>
            <p>Error: {}</p>
            <p>You can close this window and try again.</p>
            </body></html>
            """.format(error)
        elif auth_code:
            self.server.auth_result = {'code': auth_code, 'state': state}
            response_html = """
            <html><body>
            <h2>✅ Authorization Successful!</h2>
            <p>Authorization code received. You can close this window.</p>
            <p>The bookmark download will start automatically...</p>
            </body></html>
            """
        else:
            self.server.auth_result = {'error': 'no_code', 'error_description': 'No authorization code received'}
            response_html = """
            <html><body>
            <h2>❌ No Authorization Code</h2>
            <p>No authorization code was received. Please try again.</p>
            </body></html>
            """
        
        # Send response
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(response_html.encode())
    
    def log_message(self, format, *args):
        """Suppress default HTTP server logging"""
        pass

class TwitterBookmarksDownloader:
    def __init__(self, config, state_file="bookmark_download_state.json"):
        """
        Initialize the downloader with OAuth 2.0 configuration
        
        Args:
            config (dict): Configuration containing OAuth credentials
            state_file (str): File to store download progress state
        """
        self.client_id = config["client_id"]
        self.client_secret = config["client_secret"]
        self.redirect_uri = config.get("redirect_uri", "http://localhost:3000/callback")
        self.base_url = "https://api.twitter.com/2"
        self.oauth_url = "https://twitter.com/i/oauth2/authorize"
        self.token_url = "https://api.twitter.com/2/oauth2/token"
        self.state_file = state_file
        self.state = self.load_state()
        self.access_token = None
        self.refresh_token = None
    
    def load_state(self):
        """
        Load the download state from file
        
        Returns:
            dict: Download state information
        """
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                print(f"Loaded existing state: {state.get('total_downloaded', 0)} bookmarks already downloaded")
                return state
            except Exception as e:
                print(f"Error loading state file: {e}")
        
        # Default state
        return {
            "last_pagination_token": None,
            "total_downloaded": 0,
            "last_download_time": None,
            "output_file": None,
            "user_id": None,
            "completed": False,
            "access_token": None,
            "refresh_token": None,
            "token_expires_at": None
        }
    
    def save_state(self):
        """
        Save the current download state to file
        """
        # Update tokens in state
        self.state["access_token"] = self.access_token
        self.state["refresh_token"] = self.refresh_token
        
        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            print(f"Error saving state: {e}")
    
    def start_callback_server(self, timeout=300):
        """
        Start a temporary HTTP server to capture OAuth callback
        Uses the redirect_uri from config to determine host and port
        
        Args:
            timeout (int): Timeout in seconds
            
        Returns:
            dict: Authorization result or None if timeout
        """
        # Parse the redirect URI to get host and port
        parsed_uri = urlparse(self.redirect_uri)
        host = parsed_uri.hostname or 'localhost'
        port = parsed_uri.port or (443 if parsed_uri.scheme == 'https' else 80)
        
        # For localhost, use default HTTP port if not specified
        if host in ['localhost', '127.0.0.1'] and not parsed_uri.port:
            port = 3000
        
        try:
            server_address = (host, port)
            httpd = HTTPServer(server_address, CallbackHandler)
            httpd.auth_result = None
            httpd.timeout = 1  # Check for results every second
            
            print(f"🌐 Started callback server on {self.redirect_uri}")
            print("📱 Waiting for authorization... (this will open in your browser)")
            
            start_time = time.time()
            while time.time() - start_time < timeout:
                httpd.handle_request()
                if httpd.auth_result is not None:
                    return httpd.auth_result
            
            print("⏰ Timeout waiting for authorization")
            return None
            
        except OSError as e:
            if e.errno == 98:  # Address already in use
                print(f"❌ Port {port} is already in use. Please:")
                print(f"   1. Change the port in your config.json redirect_uri")
                print(f"   2. Update the redirect URI in your Twitter app settings")
                print(f"   3. Or stop any process using port {port}")
            elif e.errno == 13:  # Permission denied
                print(f"❌ Permission denied to bind to {host}:{port}")
                if port < 1024:
                    print(f"   Ports below 1024 require admin privileges. Try a higher port like 3000, 8080, or 8000")
            else:
                print(f"❌ Failed to start server on {host}:{port}: {e}")
            return None
        except Exception as e:
            print(f"❌ Unexpected error starting callback server: {e}")
            return None
    
    def generate_pkce_pair(self):
        """
        Generate PKCE code verifier and challenge for OAuth 2.0
        
        Returns:
            tuple: (code_verifier, code_challenge)
        """
        code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8')
        code_verifier = code_verifier.rstrip('=')
        
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode('utf-8')).digest()
        ).decode('utf-8')
        code_challenge = code_challenge.rstrip('=')
        
        return code_verifier, code_challenge
        """
        Generate PKCE code verifier and challenge for OAuth 2.0
        
        Returns:
            tuple: (code_verifier, code_challenge)
        """
        code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8')
        code_verifier = code_verifier.rstrip('=')
        
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode('utf-8')).digest()
        ).decode('utf-8')
        code_challenge = code_challenge.rstrip('=')
        
        return code_verifier, code_challenge
    
    def get_authorization_url(self):
        """
        Generate the authorization URL for OAuth 2.0 flow
        
        Returns:
            tuple: (authorization_url, code_verifier, state)
        """
        code_verifier, code_challenge = self.generate_pkce_pair()
        state = secrets.token_urlsafe(32)
        
        params = {
            'response_type': 'code',
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'scope': 'tweet.read users.read bookmark.read offline.access',
            'state': state,
            'code_challenge': code_challenge,
            'code_challenge_method': 'S256'
        }
        
        auth_url = f"{self.oauth_url}?{urllib.parse.urlencode(params)}"
        return auth_url, code_verifier, state
    
    def exchange_code_for_tokens(self, authorization_code, code_verifier):
        """
        Exchange authorization code for access and refresh tokens
        
        Args:
            authorization_code (str): Authorization code from callback
            code_verifier (str): PKCE code verifier
            
        Returns:
            bool: True if successful
        """
        data = {
            'grant_type': 'authorization_code',
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'code': authorization_code,
            'code_verifier': code_verifier
        }
        
        # Create basic auth header
        auth_string = f"{self.client_id}:{self.client_secret}"
        auth_bytes = auth_string.encode('ascii')
        auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
        
        headers = {
            'Authorization': f'Basic {auth_b64}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        try:
            response = requests.post(self.token_url, data=data, headers=headers)
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data['access_token']
                self.refresh_token = token_data.get('refresh_token')
                
                # Calculate expiration time
                expires_in = token_data.get('expires_in', 7200)  # Default 2 hours
                expires_at = datetime.now() + timedelta(seconds=expires_in)
                self.state["token_expires_at"] = expires_at.isoformat()
                
                print("✅ Successfully obtained access tokens!")
                return True
            else:
                print(f"Token exchange failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"Error exchanging code for tokens: {e}")
            return False
    
    def refresh_access_token(self):
        """
        Refresh the access token using refresh token
        
        Returns:
            bool: True if successful
        """
        if not self.refresh_token:
            return False
        
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': self.refresh_token,
            'client_id': self.client_id
        }
        
        auth_string = f"{self.client_id}:{self.client_secret}"
        auth_bytes = auth_string.encode('ascii')
        auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
        
        headers = {
            'Authorization': f'Basic {auth_b64}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        try:
            response = requests.post(self.token_url, data=data, headers=headers)
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data['access_token']
                if 'refresh_token' in token_data:
                    self.refresh_token = token_data['refresh_token']
                
                expires_in = token_data.get('expires_in', 7200)
                expires_at = datetime.now() + timedelta(seconds=expires_in)
                self.state["token_expires_at"] = expires_at.isoformat()
                
                print("✅ Access token refreshed successfully!")
                return True
            else:
                print(f"Token refresh failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"Error refreshing token: {e}")
            return False
    
    def authenticate(self):
        """
        Handle the complete OAuth 2.0 authentication flow with automatic callback
        
        Returns:
            bool: True if authenticated successfully
        """
        # Check if we have valid tokens
        if self.state.get("access_token") and self.state.get("token_expires_at"):
            expires_at = datetime.fromisoformat(self.state["token_expires_at"])
            if datetime.now() < expires_at - timedelta(minutes=5):  # 5 minute buffer
                self.access_token = self.state["access_token"]
                self.refresh_token = self.state.get("refresh_token")
                print("✅ Using existing valid access token")
                return True
            elif self.state.get("refresh_token"):
                print("🔄 Access token expired, attempting refresh...")
                self.refresh_token = self.state["refresh_token"]
                if self.refresh_access_token():
                    return True
        
        # Need to do full OAuth flow
        print("🔐 Starting OAuth 2.0 authentication flow...")
        auth_url, code_verifier, oauth_state = self.get_authorization_url()
        
        # Start callback server in a separate thread
        server_result = {'auth_result': None, 'exception': None}
        
        def run_server():
            try:
                server_result['auth_result'] = self.start_callback_server(timeout=300)
            except Exception as e:
                server_result['exception'] = e
        
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        
        # Give server a moment to start
        time.sleep(1)
        
        # Open browser automatically
        print(f"🌐 Opening authorization URL in your browser...")
        try:
            webbrowser.open(auth_url)
            print("✅ Browser opened. Please authorize the application.")
        except Exception as e:
            print(f"❌ Could not open browser automatically: {e}")
            print(f"📋 Please manually open this URL in your browser:")
            print(f"   {auth_url}")
        
        print("⏳ Waiting for authorization (timeout: 5 minutes)...")
        
        # Wait for server thread to complete
        server_thread.join(timeout=310)  # 10 seconds buffer
        
        # Check results
        if server_result['exception']:
            print(f"❌ Server error: {server_result['exception']}")
            return False
        
        auth_result = server_result['auth_result']
        if not auth_result:
            print("❌ Authorization timeout or failed")
            return False
        
        if 'error' in auth_result:
            print(f"❌ Authorization error: {auth_result['error']} - {auth_result.get('error_description', '')}")
            return False
        
        authorization_code = auth_result.get('code')
        if not authorization_code:
            print("❌ No authorization code received")
            return False
        
        print("✅ Authorization code received, exchanging for tokens...")
        return self.exchange_code_for_tokens(authorization_code, code_verifier)
    
    def get_authenticated_headers(self):
        """
        Get headers with OAuth 2.0 authentication
        
        Returns:
            dict: Headers with Bearer token
        """
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
    
    def get_current_user(self):
        """
        Get the current authenticated user's information
        
        Returns:
            dict: User information
        """
        url = f"{self.base_url}/users/me"
        headers = self.get_authenticated_headers()
        
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                return response.json()["data"]
            else:
                print(f"Error getting user info: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"Error getting user info: {e}")
            return None
    
    def get_rate_limit_reset_time(self, response):
        """
        Get the rate limit reset time from response headers
        
        Args:
            response: HTTP response object
            
        Returns:
            datetime: When the rate limit resets
        """
        reset_timestamp = response.headers.get('x-rate-limit-reset')
        if reset_timestamp:
            return datetime.fromtimestamp(int(reset_timestamp))
        return None
    
    def wait_for_rate_limit_reset(self, response):
        """
        Wait for rate limit to reset based on response headers
        
        Args:
            response: HTTP response object with rate limit info
        """
        reset_time = self.get_rate_limit_reset_time(response)
        if reset_time:
            wait_time = (reset_time - datetime.now()).total_seconds() + 60  # Add 1 minute buffer
            if wait_time > 0:
                print(f"Rate limit hit. Waiting until {reset_time.strftime('%H:%M:%S')} ({wait_time/60:.1f} minutes)")
                self.save_state()
                time.sleep(wait_time)
            else:
                print("Rate limit should have reset. Continuing...")
        else:
            print("Rate limit hit. Waiting 15 minutes (default)...")
            self.save_state()
            time.sleep(900)  # 15 minutes default
    
    def append_to_output_file(self, new_bookmarks, includes_data):
        """
        Append new bookmarks to the output file
        
        Args:
            new_bookmarks (list): New bookmarks to add
            includes_data (dict): Additional data (users, media, etc.)
        """
        if not self.state["output_file"]:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.state["output_file"] = f"twitter_bookmarks_{timestamp}.json"
        
        # Load existing data or create new structure
        if os.path.exists(self.state["output_file"]):
            try:
                with open(self.state["output_file"], 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
            except Exception as e:
                print(f"Error reading existing file: {e}")
                existing_data = {"bookmarks": [], "includes": {"users": [], "media": []}}
        else:
            existing_data = {
                "download_started": datetime.now().isoformat(),
                "bookmarks": [],
                "includes": {"users": [], "media": [], "tweets": []}
            }
        
        # Append new bookmarks
        existing_data["bookmarks"].extend(new_bookmarks)
        
        # Merge includes data (avoid duplicates by ID)
        for key in ["users", "media", "tweets"]:
            if key in includes_data:
                existing_ids = set()
                if key in existing_data["includes"]:
                    # Handle cases where items might not have 'id' field
                    existing_ids = set()
                    for item in existing_data["includes"][key]:
                        if isinstance(item, dict):
                            if key == "media" and "media_key" in item:
                                existing_ids.add(item["media_key"])
                            elif "id" in item:
                                existing_ids.add(item["id"])
                
                # Filter new items, handling missing 'id' fields
                new_items = []
                for item in includes_data[key]:
                    if isinstance(item, dict):
                        # For media items, use media_key as the unique identifier
                        if key == "media" and "media_key" in item:
                            if item["media_key"] not in existing_ids:
                                new_items.append(item)
                        # For other items, use id field
                        elif "id" in item:
                            if item["id"] not in existing_ids:
                                new_items.append(item)
                        else:
                            # Items without proper ID - include anyway but warn
                            print(f"⚠️  Warning: {key} item missing identifier: {type(item)} - {str(item)[:100]}...")
                            new_items.append(item)
                
                if key not in existing_data["includes"]:
                    existing_data["includes"][key] = []
                existing_data["includes"][key].extend(new_items)
        
        # Update metadata
        existing_data["last_updated"] = datetime.now().isoformat()
        existing_data["total_bookmarks"] = len(existing_data["bookmarks"])
        existing_data["download_completed"] = self.state["completed"]
        
        # Save updated data
        try:
            with open(self.state["output_file"], 'w', encoding='utf-8') as f:
                json.dump(existing_data, f, indent=2, ensure_ascii=False)
            print(f"Saved {len(new_bookmarks)} new bookmarks to {self.state['output_file']}")
        except Exception as e:
            print(f"Error saving bookmarks: {e}")
    
    def get_bookmarks_batch(self, user_id, max_results=100):
        """
        Fetch a single batch of bookmarks
        
        Args:
            user_id (str): Your Twitter user ID
            max_results (int): Number of tweets per request (max 100)
            
        Returns:
            tuple: (bookmarks_list, includes_dict, next_token, rate_limited)
        """
        url = f"{self.base_url}/users/{user_id}/bookmarks"
        headers = self.get_authenticated_headers()
        
        params = {
            "max_results": 100,  # Maximum allowed for bookmarks endpoint
            "tweet.fields": "id,text,author_id,created_at,public_metrics,context_annotations,entities,referenced_tweets,reply_settings,source,lang,possibly_sensitive,edit_controls",
            "user.fields": "id,name,username,verified,description,public_metrics,profile_image_url,url,location,created_at",
            "expansions": "author_id,referenced_tweets.id,referenced_tweets.id.author_id,entities.mentions.username,attachments.media_keys",
            "media.fields": "media_key,type,url,preview_image_url,public_metrics,alt_text,variants"
        }
        
        if self.state["last_pagination_token"]:
            params["pagination_token"] = self.state["last_pagination_token"]
        
        try:
            response = requests.get(url, headers=headers, params=params)
            
            # Debug: Log response details
            print(f"🔍 API Response Status: {response.status_code}")
            print(f"🔍 Rate Limit Headers:")
            print(f"   x-rate-limit-limit: {response.headers.get('x-rate-limit-limit', 'Not present')}")
            print(f"   x-rate-limit-remaining: {response.headers.get('x-rate-limit-remaining', 'Not present')}")
            print(f"   x-rate-limit-reset: {response.headers.get('x-rate-limit-reset', 'Not present')}")
            
            if response.status_code == 429:
                print(f"🔍 Rate limit response body: {response.text}")
                return [], {}, None, True
            elif response.status_code == 401:
                print("❌ Authentication failed. Token may have expired.")
                print(f"🔍 401 response body: {response.text}")
                if self.refresh_access_token():
                    # Retry with new token
                    headers = self.get_authenticated_headers()
                    response = requests.get(url, headers=headers, params=params)
                    if response.status_code == 200:
                        data = response.json()
                        return data.get("data", []), data.get("includes", {}), data.get("meta", {}).get("next_token"), False
                return [], {}, None, False
            elif response.status_code != 200:
                print(f"Error: {response.status_code} - {response.text}")
                return [], {}, None, False
            
            data = response.json()
            bookmarks = data.get("data", [])
            includes = data.get("includes", {})
            next_token = data.get("meta", {}).get("next_token")
            
            # Debug: Log the structure of the response for troubleshooting
            if not bookmarks and "data" not in data:
                print(f"🔍 Debug: API response structure: {list(data.keys())}")
                if "errors" in data:
                    print(f"🔍 API errors: {data['errors']}")
                if "meta" in data:
                    print(f"🔍 Meta info: {data['meta']}")
            
            return bookmarks, includes, next_token, False
            
        except requests.exceptions.RequestException as e:
            print(f"Request error: {e}")
            return [], {}, None, False
    
    def download_all_bookmarks(self, user_id, batch_size=100, auto_resume=True):
        """
        Download all bookmarks with resume capability
        
        Args:
            user_id (str): Your Twitter user ID
            batch_size (int): Number of tweets per request
            auto_resume (bool): Whether to automatically resume after rate limits
            
        Returns:
            bool: True if download completed successfully
        """
        self.state["user_id"] = user_id
        
        if self.state["completed"]:
            print("Download already completed! Delete the state file to start over.")
            return True
        
        print(f"Starting download from position: {self.state['total_downloaded']} bookmarks")
        if self.state["last_pagination_token"]:
            print("Resuming from previous session...")
        
        consecutive_rate_limits = 0
        max_consecutive_rate_limits = 3
        
        while not self.state["completed"]:
            try:
                # Get a batch of bookmarks
                bookmarks, includes, next_token, rate_limited = self.get_bookmarks_batch(user_id, batch_size)
                
                if rate_limited:
                    consecutive_rate_limits += 1
                    if consecutive_rate_limits >= max_consecutive_rate_limits and not auto_resume:
                        print(f"Hit rate limit {consecutive_rate_limits} times. Set auto_resume=True to continue automatically.")
                        return False
                    
                    # Create dummy response for rate limit handling
                    dummy_response = requests.Response()
                    dummy_response.status_code = 429
                    self.wait_for_rate_limit_reset(dummy_response)
                    continue
                
                consecutive_rate_limits = 0  # Reset counter on successful request
                
                if not bookmarks:
                    print("No more bookmarks found. Download completed!")
                    self.state["completed"] = True
                    self.save_state()
                    break
                
                print(f"🔍 Debug: Retrieved {len(bookmarks)} bookmarks in this batch")
                
                # Save bookmarks to file
                self.append_to_output_file(bookmarks, includes)
                
                # Update state
                self.state["total_downloaded"] += len(bookmarks)
                self.state["last_pagination_token"] = next_token
                self.state["last_download_time"] = datetime.now().isoformat()
                self.save_state()
                
                print(f"Downloaded batch of {len(bookmarks)} bookmarks. Total: {self.state['total_downloaded']}")
                
                # Check if we've reached the end
                if not next_token:
                    print("Reached end of bookmarks. Download completed!")
                    self.state["completed"] = True
                    self.save_state()
                    break
                
                # Small delay between requests
                time.sleep(1)
                
            except Exception as e:
                print(f"❌ Error processing batch: {e}")
                print(f"🔍 Error type: {type(e).__name__}")
                import traceback
                print(f"🔍 Full traceback:")
                traceback.print_exc()
                
                # Save current state before potentially stopping
                self.save_state()
                
                # For debugging, let's continue instead of breaking
                print("⚠️  Attempting to continue with next batch...")
                continue
        
        # Final summary
        if self.state["completed"]:
            print(f"\n✅ Download completed successfully!")
            print(f"Total bookmarks downloaded: {self.state['total_downloaded']}")
            print(f"Output file: {self.state['output_file']}")
            return True
        
        return False
    
    def reset_download(self):
        """
        Reset the download state to start fresh
        """
        if os.path.exists(self.state_file):
            os.remove(self.state_file)
        self.state = {
            "last_pagination_token": None,
            "total_downloaded": 0,
            "last_download_time": None,
            "output_file": None,
            "user_id": None,
            "completed": False,
            "access_token": None,
            "refresh_token": None,
            "token_expires_at": None
        }
        print("Download state reset. Next run will start from the beginning.")
    
    def get_status(self):
        """
        Print current download status
        """
        print(f"\n📊 Download Status:")
        print(f"Total downloaded: {self.state['total_downloaded']} bookmarks")
        print(f"Completed: {'Yes' if self.state['completed'] else 'No'}")
        print(f"Output file: {self.state['output_file'] or 'Not created yet'}")
        if self.state["last_download_time"]:
            print(f"Last download: {self.state['last_download_time']}")
        
        # Token status
        if self.state.get("access_token"):
            if self.state.get("token_expires_at"):
                expires_at = datetime.fromisoformat(self.state["token_expires_at"])
                if datetime.now() < expires_at:
                    print(f"🔐 Authentication: Valid (expires {expires_at.strftime('%Y-%m-%d %H:%M:%S')})")
                else:
                    print(f"🔐 Authentication: Expired (will refresh automatically)")
            else:
                print(f"🔐 Authentication: Token available")
        else:
            print(f"🔐 Authentication: Not authenticated")

def load_config(config_file="config.json"):
    """
    Load configuration from JSON file
    
    Args:
        config_file (str): Path to configuration file
        
    Returns:
        dict: Configuration data
    """
    if not os.path.exists(config_file):
        # Create a template config file
        template_config = {
            "client_id": "your_client_id_here",
            "client_secret": "your_client_secret_here",
            "redirect_uri": "http://localhost:3000/callback",
            "batch_size": 100,
            "state_file": "bookmark_download_state.json"
        }
        
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(template_config, f, indent=2)
            print(f"Created template config file: {config_file}")
            print("Please edit the config file with your Twitter API OAuth 2.0 credentials.")
            print("\nTo get OAuth 2.0 credentials:")
            print("1. Go to https://developer.twitter.com/en/portal/dashboard")
            print("2. Create a new app or select existing app")
            print("3. Go to 'Keys and tokens' tab")
            print("4. Generate OAuth 2.0 Client ID and Client Secret")
            print("5. Add 'http://localhost:3000/callback' as a redirect URI in app settings")
            return None
        except Exception as e:
            print(f"Error creating config file: {e}")
            return None
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Validate required fields
        required_fields = ["client_id", "client_secret"]
        missing_fields = [field for field in required_fields if not config.get(field) or config[field] == f"your_{field}_here"]
        
        if missing_fields:
            print(f"Please update the following fields in {config_file}: {', '.join(missing_fields)}")
            return None
        
        return config
        
    except Exception as e:
        print(f"Error loading config file: {e}")
        return None

def main():
    """
    Main function with OAuth 2.0 authentication
    """
    # Load configuration
    config = load_config()
    if not config:
        return
    
    # Extract configuration
    BATCH_SIZE = config.get("batch_size", 100)
    STATE_FILE = config.get("state_file", "bookmark_download_state.json")
    
    downloader = TwitterBookmarksDownloader(config, STATE_FILE)
    
    # Show current status
    downloader.get_status()
    
    # Authenticate
    if not downloader.authenticate():
        print("❌ Authentication failed. Please check your credentials.")
        return
    
    # Get current user info
    user_info = downloader.get_current_user()
    if not user_info:
        print("❌ Failed to get user information.")
        return
    
    user_id = user_info["id"]
    username = user_info["username"]
    print(f"✅ Authenticated as @{username} (ID: {user_id})")
    
    # Check if we should resume or start fresh
    if downloader.state["total_downloaded"] > 0 and not downloader.state["completed"]:
        print(f"\n🔄 Found incomplete download with {downloader.state['total_downloaded']} bookmarks")
        choice = input("Resume download? (y/n): ").lower().strip()
        if choice != 'y':
            reset_choice = input("Start fresh? This will delete current progress (y/n): ").lower().strip()
            if reset_choice == 'y':
                downloader.reset_download()
            else:
                print("Exiting...")
                return
    
    # Start download
    print(f"\n⬇️  Starting bookmark download...")
    print("The download will automatically handle rate limits and can be safely interrupted.")
    print("Run this script again to resume from where you left off.\n")
    
    try:
        success = downloader.download_all_bookmarks(user_id, batch_size=BATCH_SIZE, auto_resume=True)
        if success:
            print(f"\n🎉 All bookmarks downloaded successfully to: {downloader.state['output_file']}")
        else:
            print(f"\n⏸️  Download paused. Run the script again to resume.")
    except KeyboardInterrupt:
        print(f"\n⏸️  Download interrupted by user. Progress saved.")
        print("Run the script again to resume from where you left off.")
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")
        print("Progress has been saved. Try running the script again.")

if __name__ == "__main__":
    main()
