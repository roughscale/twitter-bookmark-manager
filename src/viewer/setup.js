const fs = require('fs');
const path = require('path');

const defaultConfig = {
  dataDirectory: "./data",
  server: {
    port: 3000,
    host: "localhost"
  },
  filePattern: {
    include: ["bookmark", ".json"],
    exclude: ["temp", "backup"]
  },
  ui: {
    title: "Twitter Bookmarks Viewer",
    itemsPerPage: 50,
    enableSearch: true,
    enableFileSelector: true
  }
};

function createConfigFile() {
  const configPath = './config.json';
  
  if (!fs.existsSync(configPath)) {
    console.log('Creating default config.json...');
    fs.writeFileSync(configPath, JSON.stringify(defaultConfig, null, 2));
    console.log('✅ Created config.json with default settings');
  } else {
    console.log('📄 config.json already exists');
  }
}

function createDataDirectory(config) {
  const dataDir = path.resolve(config.dataDirectory);
  
  if (!fs.existsSync(dataDir)) {
    console.log(`Creating data directory: ${dataDir}`);
    fs.mkdirSync(dataDir, { recursive: true });
    console.log('✅ Created data directory');
  } else {
    console.log(`📁 Data directory exists: ${dataDir}`);
  }
}

function createPublicDirectory() {
  const publicDir = './public';
  
  if (!fs.existsSync(publicDir)) {
    console.log('Creating public directory...');
    fs.mkdirSync(publicDir);
    console.log('✅ Created public directory');
  } else {
    console.log('📁 Public directory exists');
  }
}

function validateConfig(config) {
  const errors = [];
  
  if (!config.dataDirectory) {
    errors.push('dataDirectory is required');
  }
  
  if (!config.server || !config.server.port) {
    errors.push('server.port is required');
  }
  
  if (errors.length > 0) {
    console.error('❌ Configuration errors:');
    errors.forEach(error => console.error(`  - ${error}`));
    process.exit(1);
  }
}

function setup() {
  console.log('🚀 Setting up Twitter Bookmarks Viewer...\n');
  
  // Create config file
  createConfigFile();
  
  // Load and validate config
  const config = JSON.parse(fs.readFileSync('./config.json', 'utf8'));
  validateConfig(config);
  
  // Create directories
  createDataDirectory(config);
  createPublicDirectory();
  
  console.log('\n✅ Setup complete!');
  console.log('\n📋 Next steps:');
  console.log(`1. Place your bookmark JSON files in: ${path.resolve(config.dataDirectory)}`);
  console.log('2. Make sure you have the index.html file in the public/ directory');
  console.log('3. Run: npm install');
  console.log('4. Run: npm start');
  console.log(`5. Open: http://${config.server.host}:${config.server.port}`);
  console.log('\n💡 You can modify config.json to change settings');
}

if (require.main === module) {
  setup();
}

module.exports = { setup, defaultConfig };
