# Twitter Bookmarks Viewer

A local Node.js-based React application for viewing Twitter bookmarks with configurable data sources.

## Features

- **Configurable data directory** - Specify where your bookmark JSON files are located
- **Multiple file support** - Switch between different bookmark files
- **File pattern matching** - Configure which files to include/exclude
- **Twitter-like interface** - Familiar layout with media support
- **Search functionality** - Filter bookmarks by content, usernames, or names
- **Responsive design** - Works on different screen sizes

## Project Structure

```
twitter-bookmarks-viewer/
├── package.json              # Dependencies and scripts
├── config.json               # Configuration file
├── server.js                 # Express server
├── setup.js                  # Setup script
├── data/                     # Put your JSON files here
│   └── twitter_bookmarks_*.json
├── public/
│   └── index.html            # React frontend
└── README.md                 # This file
```

## Quick Setup

### 1. Download Files
Download these files to your project directory:
- `package.json`
- `server.js` 
- `setup.js`
- `config.json`
- `public/index.html`
- `README.md`

### 2. Install Dependencies
```bash
npm install
```

### 3. Run Setup
```bash
npm run setup
```

This will:
- Create the `data/` directory
- Create the `public/` directory
- Validate your configuration

### 4. Add Your Bookmark Files
Copy your Twitter bookmark JSON files to the `data/` directory:
```bash
cp ~/Downloads/twitter_bookmarks_*.json ./data/
```

### 5. Start the Server
```bash
npm start
```

### 6. Open in Browser
```
http://localhost:3000
```

## Configuration

Edit `config.json` to customize the application:

```json
{
  "dataDirectory": "./data",
  "server": {
    "port": 3000,
    "host": "localhost"
  },
  "filePattern": {
    "include": ["bookmark", ".json"],
    "exclude": ["temp", "backup"]
  },
  "ui": {
    "title": "Twitter Bookmarks Viewer",
    "itemsPerPage": 50,
    "enableSearch": true,
    "enableFileSelector": true
  }
}
```

### Configuration Options

**`dataDirectory`**: Path to directory containing bookmark JSON files
- Can be relative (`./data`) or absolute (`/home/user/bookmarks`)
- Directory will be created if it doesn't exist

**`server`**: Server configuration
- `port`: Port to run the server on (default: 3000)
- `host`: Host to bind to (default: localhost)

**`filePattern`**: File filtering rules
- `include`: Array of strings that filenames must contain
- `exclude`: Array of strings that will exclude files

**`ui`**: User interface options
- `title`: Application title shown in header and browser tab
- `itemsPerPage`: Number of bookmarks per page (future feature)
- `enableSearch`: Enable/disable search functionality
- `enableFileSelector`: Show file selector dropdown when multiple files

## Usage

### File Management
- The app automatically discovers JSON files matching your configured pattern
- Files are sorted by modification date (newest first)
- Use the dropdown to switch between different bookmark files
- Refresh button reloads the current file and checks for new files

### Search
- Search through tweet text, usernames, and display names
- Real-time filtering as you type
- Can be disabled via configuration

### File Patterns
Configure which files to include/exclude:

```json
{
  "filePattern": {
    "include": ["bookmark", ".json"],
    "exclude": ["temp", "backup", "old"]
  }
}
```

This will:
- ✅ Include: `twitter_bookmarks_2024.json`
- ✅ Include: `my_bookmarks_final.json`
- ❌ Exclude: `bookmarks_temp.json`
- ❌ Exclude: `backup_bookmarks.json`

## Scripts

- `npm start` - Start the production server
- `npm run dev` - Start with auto-restart (requires nodemon)
- `npm run setup` - Run the setup script

## API Endpoints

- `GET /api/config` - Get current configuration
- `GET /api/files` - List available bookmark files
- `GET /api/bookmarks` - Get latest bookmark file
- `GET /api/bookmarks/:filename` - Get specific bookmark file

## Troubleshooting

### No files found
1. Check that your JSON files are in the correct directory
2. Verify the `dataDirectory` path in `config.json`
3. Ensure files match the `filePattern` configuration

### Server won't start
1. Check if the port is already in use
2. Verify the `config.json` file is valid JSON
3. Make sure you ran `npm install`

### Permission errors
1. Ensure the data directory is readable
2. Check file permissions on JSON files
3. Run with appropriate user permissions

### Missing index.html
If you get an error about missing index.html:
1. Make sure the `public/` directory exists
2. Place the `index.html` file in the `public/` directory
3. Run `npm run setup` to create missing directories

## Development

```bash
# Install development dependencies
npm install

# Run with auto-restart
npm run dev

# Create fresh config
npm run setup
```

## File Formats

The application expects Twitter bookmark JSON files in the format provided by the Twitter API v2, with the following structure:

```json
{
  "bookmarks": [...],
  "includes": {
    "users": [...],
    "media": [...],
    "tweets": [...]
  },
  "meta": {...}
}
```

## Requirements

- Node.js 14.0.0 or higher
- Modern web browser with JavaScript enabled
- Twitter bookmark JSON files from the Twitter API v2

## License

MIT License - feel free to modify and distribute as needed.
