# Twitter Bookmarks Downloader

A Python tool for downloading Twitter bookmarks using the Twitter API v2 with OAuth 2.0 authentication. Features automatic rate limit handling, resume capability, and robust error handling.

## Features

- **OAuth 2.0 Authentication** - Secure user authentication with automatic token refresh
- **Resume Capability** - Automatically saves progress and resumes from where you left off
- **Rate Limit Handling** - Respects Twitter's API limits with automatic waiting
- **Monthly Cap Detection** - Handles Twitter's monthly usage caps gracefully
- **Incremental Downloads** - Saves bookmarks as they're downloaded, never loses data
- **Configurable Settings** - Easy configuration via JSON file
- **Automatic Browser OAuth** - Opens browser automatically for authentication
- **Media Support** - Downloads complete bookmark data including images and videos
- **Error Recovery** - Robust error handling and recovery mechanisms

## Requirements

- Python 3.7 or higher
- Twitter Developer Account with OAuth 2.0 app
- Internet connection

## Project Structure

```
twitter-bookmarks-manager/downloader/
├── download_bookmarks.py     # Main downloader script
├── config.json              # Configuration file
├── bookmark_download_state.json  # Progress state (auto-created)
├── twitter_bookmarks_*.json # Downloaded bookmark files
└── README.md                # This file
```

## Quick Setup

### 1. Get Twitter API Credentials

**Create Twitter Developer Account:**
1. Go to https://developer.twitter.com/en/portal/dashboard
2. Sign in with your Twitter account
3. Apply for a developer account if you don't have one

**Create an App:**
1. Create a new app or select existing app
2. Go to app **Settings** tab
3. Find **"User authentication settings"**
4. Click **"Set up"** or **"Edit"**

**Configure OAuth 2.0:**
- **App type**: Web App
- **App permissions**: 
  - ✅ Read
  - ✅ Users.read
  - ✅ Tweet.read
  - ✅ Bookmark.read
- **Callback URLs**: `http://localhost:3001/callback`
- **Website URL**: Any valid URL (e.g., `https://example.com`)
- **Terms of Service**: Any URL (required field)
- **Privacy Policy**: Any URL (required field)

**Get Credentials:**
1. Go to **"Keys and tokens"** tab
2. Find **"OAuth 2.0 Client ID and Client Secret"** section
3. Click **"Generate"** if not already created
4. Copy the Client ID and Client Secret

### 2. Install Dependencies

```bash
pip install requests
```

### 3. Configure the Script

Create or edit `config.json`:

```json
{
  "client_id": "your_oauth2_client_id_here",
  "client_secret": "your_oauth2_client_secret_here",
  "redirect_uri": "http://localhost:3001/callback",
  "batch_size": 100,
  "state_file": "bookmark_download_state.json"
}
```

### 4. Run the Downloader

```bash
python download_bookmarks.py
```

The script will:
1. Open your browser for Twitter authentication
2. Start downloading bookmarks automatically
3. Handle rate limits and save progress
4. Create a JSON file with your bookmarks

## Configuration Options

Edit `config.json` to customize the downloader:

```json
{
  "client_id": "your_oauth2_client_id_here",
  "client_secret": "your_oauth2_client_secret_here", 
  "redirect_uri": "http://localhost:3001/callback",
  "batch_size": 100,
  "state_file": "bookmark_download_state.json"
}
```

**Configuration Fields:**

- **`client_id`**: OAuth 2.0 Client ID from Twitter Developer Portal
- **`client_secret`**: OAuth 2.0 Client Secret from Twitter Developer Portal
- **`redirect_uri`**: Callback URL (must match Twitter app settings)
- **`batch_size`**: Number of bookmarks per API request (max 100)
- **`state_file`**: File to store download progress

## Usage

### First Run

```bash
python download_bookmarks.py
```

**What happens:**
1. Script opens your browser to Twitter authorization page
2. You authorize the application
3. Browser shows success page and closes
4. Download starts automatically
5. Progress is saved continuously

### Resume Download

If interrupted, simply run the script again:

```bash
python download_bookmarks.py
```

The script will automatically resume from where it left off.

### Reset Download

To start completely fresh:

```bash
rm bookmark_download_state.json
python download_bookmarks.py
```

## Twitter API Limits

### Rate Limits
- **1 request per 15 minutes** for bookmarks endpoint
- **100 bookmarks maximum** per request
- Automatic handling with progress preservation

### Monthly Caps (vary by tier)
- **Free Tier**: 100 posts per month
- **Basic Tier ($100/month)**: 10,000 posts per month
- **Pro Tier ($5,000/month)**: 1,000,000 posts per month

### Expected Download Times
- **Free Tier**: ~2 requests (200 bookmarks) then monthly cap
- **Basic Tier**: ~100 requests (10,000 bookmarks) over ~25 hours
- **Pro Tier**: ~10,000 requests (1M bookmarks) over ~250 hours

## Output Files

### Bookmark Data File
**Format**: `twitter_bookmarks_YYYYMMDD_HHMMSS.json`

**Structure**:
```json
{
  "download_started": "2024-01-01T10:00:00",
  "last_updated": "2024-01-01T12:30:00", 
  "total_bookmarks": 500,
  "download_completed": true,
  "bookmarks": [...],
  "includes": {
    "users": [...],
    "media": [...],
    "tweets": [...]
  }
}
```

### State File
**Format**: `bookmark_download_state.json`

Tracks download progress:
- Current pagination position
- Total bookmarks downloaded
- Authentication tokens
- Error states and recovery info

## Troubleshooting

### Authentication Issues

**Problem**: "You weren't able to give access to the App"
**Solutions**:
1. Check OAuth 2.0 credentials in Twitter Developer Portal
2. Verify callback URL matches exactly: `http://localhost:3001/callback`
3. Ensure app permissions include bookmark.read
4. Make sure app type is set to "Web App"

**Problem**: "Authentication failed. Token may have expired"
**Solutions**:
1. Script will automatically refresh tokens
2. If refresh fails, delete `bookmark_download_state.json` and re-authenticate

### Rate Limit Issues

**Problem**: "Rate limit hit. Waiting 15 minutes"
**Expected**: This is normal behavior - the script handles this automatically

**Problem**: "UsageCapExceeded" - Monthly cap exceeded
**Solutions**:
1. Wait for monthly reset (beginning of billing cycle)
2. Upgrade to higher API tier
3. Use downloaded bookmarks for now

### File Issues

**Problem**: "config.json not found"
**Solution**: Create config.json with your Twitter API credentials

**Problem**: "Permission denied"
**Solution**: Ensure write permissions in the script directory

### Network Issues

**Problem**: "Request error" or connection timeouts
**Solutions**:
1. Check internet connection
2. Verify Twitter API status: https://api.twitterstat.us/
3. Script will automatically retry failed requests

## Advanced Usage

### Custom Callback Port

Change the port in both `config.json` and your Twitter app settings:

```json
{
  "redirect_uri": "http://localhost:8080/callback"
}
```

### Batch Size Optimization

For accounts with limited monthly caps:

```json
{
  "batch_size": 50
}
```

This uses smaller batches, allowing more granular control over usage.

### Multiple State Files

Run multiple downloads with different state files:

```json
{
  "state_file": "personal_bookmarks_state.json"
}
```

## Error Codes and Recovery

### Common Error Responses

**429 - Rate Limit Exceeded**
- **15-minute limit**: Script waits automatically
- **Monthly cap**: Download stops, can resume next month

**401 - Unauthorized** 
- Automatic token refresh attempted
- Re-authentication required if refresh fails

**403 - Forbidden**
- Check app permissions in Developer Portal
- Verify OAuth 2.0 setup is complete

**404 - Not Found**
- User may not have any bookmarks
- Check authentication and user permissions

### Recovery Strategies

1. **Automatic Recovery**: Script handles most errors automatically
2. **Manual Recovery**: Delete state file to start fresh
3. **Partial Recovery**: Edit state file to resume from specific point

## Security Considerations

### Token Storage
- Access tokens stored locally in state file
- Tokens automatically refresh when expired
- Delete state file to remove stored credentials

### Network Security
- All communication uses HTTPS
- OAuth 2.0 with PKCE for secure authentication
- Local callback server runs temporarily during auth only

### API Key Protection
- Never commit config.json with real credentials to version control
- Use environment variables for CI/CD deployments
- Regularly rotate API keys if compromised

## Development

### Testing Configuration
```bash
# Test with small batch size
python -c "
import json
config = json.load(open('config.json'))
config['batch_size'] = 10
json.dump(config, open('config.json', 'w'), indent=2)
"
python download_bookmarks.py
```

### Debugging
Enable debug output by modifying the script:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Custom Modifications
The script is designed to be easily modified:
- Add custom filtering in `download_all_bookmarks()`
- Modify output format in `append_to_output_file()`
- Add custom error handling in exception blocks

## Integration

### With Bookmark Viewer
Downloaded JSON files work directly with the companion viewer app:

```bash
# Copy downloads to viewer data directory
cp twitter_bookmarks_*.json ../twitter-bookmarks-viewer/data/
```

### With Other Tools
The JSON output follows Twitter API v2 format and can be used with:
- Data analysis tools (pandas, R)
- Database imports (MongoDB, PostgreSQL)
- Other Twitter API tools and libraries

## FAQ

**Q: How many bookmarks can I download?**
A: Depends on your API tier. Free tier allows ~200 bookmarks/month, Basic tier allows ~10,000/month.

**Q: Can I download someone else's bookmarks?**
A: No, you can only download your own bookmarks due to Twitter's privacy restrictions.

**Q: What if I have thousands of bookmarks?**
A: The script handles large collections automatically. With Basic tier ($100/month), you can download 10,000 bookmarks over ~25 hours.

**Q: Can I run this on a server?**
A: Yes, but the OAuth flow requires a browser for initial authentication. You can authenticate locally then transfer the state file to a server.

**Q: Is this against Twitter's Terms of Service?**
A: No, this uses official Twitter API v2 endpoints and follows all rate limits and guidelines.

## License

MIT License - Feel free to modify and distribute as needed.

## Support

For issues:
1. Check this README for troubleshooting steps
2. Verify your Twitter Developer Portal configuration
3. Check Twitter API status page
4. Review error messages and logs

