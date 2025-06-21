const express = require('express');
const cors = require('cors');
const fs = require('fs');
const path = require('path');

const app = express();

// Load configuration
function loadConfig() {
  const configPath = './config.json';
  
  if (!fs.existsSync(configPath)) {
    console.error('❌ config.json not found. Run: npm run setup');
    process.exit(1);
  }
  
  try {
    const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
    
    // Validate required fields
    if (!config.dataDirectory) {
      throw new Error('dataDirectory is required in config.json');
    }
    
    // Set defaults for optional fields
    config.server = config.server || {};
    config.server.port = config.server.port || 3000;
    config.server.host = config.server.host || 'localhost';
    config.filePattern = config.filePattern || { include: ['bookmark', '.json'], exclude: [] };
    config.ui = config.ui || {};
    
    return config;
  } catch (error) {
    console.error('❌ Error loading config.json:', error.message);
    console.error('💡 Run: npm run setup to create a valid config file');
    process.exit(1);
  }
}

const config = loadConfig();
const DATA_DIR = path.resolve(config.dataDirectory);
const PORT = config.server.port;
const HOST = config.server.host;

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.static('public'));

// Helper function to check if file matches pattern
function matchesFilePattern(filename) {
  const { include, exclude } = config.filePattern;
  
  // Check if file includes required patterns
  const includeMatch = include.every(pattern => 
    filename.toLowerCase().includes(pattern.toLowerCase())
  );
  
  if (!includeMatch) return false;
  
  // Check if file doesn't include excluded patterns
  const excludeMatch = exclude.some(pattern => 
    filename.toLowerCase().includes(pattern.toLowerCase())
  );
  
  return !excludeMatch;
}

// API endpoint to get configuration
app.get('/api/config', (req, res) => {
  res.json({
    ui: config.ui,
    dataDirectory: config.dataDirectory
  });
});

// API endpoint to get available bookmark files
app.get('/api/files', (req, res) => {
  try {
    if (!fs.existsSync(DATA_DIR)) {
      return res.status(404).json({ 
        error: `Data directory not found: ${DATA_DIR}`,
        suggestion: 'Check your config.json dataDirectory setting'
      });
    }
    
    const files = fs.readdirSync(DATA_DIR)
      .filter(file => matchesFilePattern(file))
      .map(file => {
        const filePath = path.join(DATA_DIR, file);
        const stats = fs.statSync(filePath);
        return {
          name: file,
          path: `/api/bookmarks/${encodeURIComponent(file)}`,
          modified: stats.mtime,
          size: stats.size
        };
      })
      .sort((a, b) => new Date(b.modified) - new Date(a.modified));
    
    res.json(files);
  } catch (error) {
    console.error('Error reading data directory:', error);
    res.status(500).json({ 
      error: 'Could not read bookmark files',
      dataDirectory: DATA_DIR
    });
  }
});

// API endpoint to get specific bookmark file
app.get('/api/bookmarks/:filename', (req, res) => {
  try {
    const filename = decodeURIComponent(req.params.filename);
    
    // Security check - ensure filename doesn't contain path traversal
    if (filename.includes('..') || filename.includes('/') || filename.includes('\\')) {
      return res.status(400).json({ error: 'Invalid filename' });
    }
    
    const filePath = path.join(DATA_DIR, filename);
    
    if (!fs.existsSync(filePath)) {
      return res.status(404).json({ 
        error: 'File not found',
        filename: filename,
        dataDirectory: DATA_DIR
      });
    }
    
    // Check if file matches pattern
    if (!matchesFilePattern(filename)) {
      return res.status(403).json({ 
        error: 'File does not match configured pattern',
        filePattern: config.filePattern
      });
    }
    
    const data = fs.readFileSync(filePath, 'utf8');
    const bookmarks = JSON.parse(data);
    
    res.json(bookmarks);
  } catch (error) {
    console.error('Error reading bookmark file:', error);
    res.status(500).json({ 
      error: 'Could not read bookmark file',
      details: error.message
    });
  }
});

// API endpoint to get the latest bookmark file
app.get('/api/bookmarks', (req, res) => {
  try {
    if (!fs.existsSync(DATA_DIR)) {
      return res.status(404).json({ 
        error: `Data directory not found: ${DATA_DIR}`,
        suggestion: 'Check your config.json dataDirectory setting'
      });
    }
    
    const files = fs.readdirSync(DATA_DIR)
      .filter(file => matchesFilePattern(file))
      .map(file => ({
        name: file,
        modified: fs.statSync(path.join(DATA_DIR, file)).mtime
      }))
      .sort((a, b) => new Date(b.modified) - new Date(a.modified));
    
    if (files.length === 0) {
      return res.status(404).json({ 
        error: 'No bookmark files found',
        dataDirectory: DATA_DIR,
        filePattern: config.filePattern,
        suggestion: `Place bookmark JSON files in ${DATA_DIR}`
      });
    }
    
    const latestFile = files[0];
    const filePath = path.join(DATA_DIR, latestFile.name);
    const data = fs.readFileSync(filePath, 'utf8');
    const bookmarks = JSON.parse(data);
    
    res.json({ ...bookmarks, filename: latestFile.name });
  } catch (error) {
    console.error('Error reading bookmark files:', error);
    res.status(500).json({ 
      error: 'Could not read bookmark files',
      dataDirectory: DATA_DIR
    });
  }
});

// Serve the React app
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

// Check if data directory exists and create if needed
if (!fs.existsSync(DATA_DIR)) {
  console.log(`📁 Creating data directory: ${DATA_DIR}`);
  fs.mkdirSync(DATA_DIR, { recursive: true });
}

// Check if public directory exists
if (!fs.existsSync('./public')) {
  console.log('📁 Creating public directory...');
  fs.mkdirSync('./public');
  console.log('💡 Please place index.html in the public/ directory');
}

app.listen(PORT, HOST, () => {
  console.log(`🚀 Twitter Bookmarks Viewer running on http://${HOST}:${PORT}`);
  console.log(`📁 Data directory: ${DATA_DIR}`);
  console.log(`🔍 File pattern: includes ${config.filePattern.include.join(', ')}`);
  if (config.filePattern.exclude.length > 0) {
    console.log(`🚫 Excludes: ${config.filePattern.exclude.join(', ')}`);
  }
  console.log('📋 Place your bookmark JSON files in the data directory');
  console.log('💡 Make sure index.html is in the public/ directory');
});
