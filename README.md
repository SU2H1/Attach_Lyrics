# 🎵 Lyrics Updater - Audio File Lyrics Manager

A powerful desktop application that automatically identifies songs and adds lyrics to your audio files using web scraping with Puppeteer.

## ✨ Features

- **User-Friendly GUI**: Clean, intuitive interface for easy file management
- **Automatic Song Recognition**: Reads metadata or parses filenames to identify songs
- **Web Scraping with Puppeteer**: Fetches lyrics from multiple sources without API keys:
  - Genius
  - AZLyrics  
  - Google Search
  - And more!
- **Multiple Format Support**: MP3, M4A, MP4, FLAC, OGG
- **Batch Processing**: Process entire folders of music at once
- **Smart Detection**: Skip files that already have lyrics (optional)
- **Real-time Progress**: See live updates as files are processed

## 📋 Requirements

- Python 3.7+
- Node.js 14+
- Chrome/Chromium (for Puppeteer)

## 🚀 Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/lyrics-updater.git
cd lyrics-updater
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Install Node.js dependencies:
```bash
npm install
```

## 💻 Usage

### GUI Application (Recommended)

Simply run the GUI application:
```bash
python gui_app.py
```

The app will:
1. Start the Puppeteer server automatically
2. Open a user-friendly interface
3. Let you select files or folders
4. Show real-time progress as lyrics are added

### Command Line Interface

For the web scraping version:
```bash
# Start the Node.js server first
node scraper.js

# In another terminal, run the Python script
python lyrics_scraper.py "path/to/music"
```

### Options

- **Overwrite existing lyrics**: Replace lyrics even if they already exist
- **File type selection**: Choose which audio formats to process
- **Batch processing**: Select entire folders for processing

## 🎯 How It Works

1. **Song Identification**: 
   - Reads ID3 tags, MP4 atoms, or Vorbis comments
   - Falls back to intelligent filename parsing

2. **Lyrics Fetching**:
   - Uses Puppeteer to render JavaScript-heavy sites
   - Tries multiple sources until lyrics are found
   - No API keys required!

3. **Metadata Writing**:
   - MP3: USLT (Unsynchronized Lyrics) ID3 tag
   - MP4/M4A: ©lyr atom
   - FLAC/OGG: 'lyrics' Vorbis comment

## 📁 File Structure

```
lyrics-updater/
├── gui_app.py          # Main GUI application
├── scraper.js          # Puppeteer web scraping server
├── lyrics_scraper.py   # Python scraping implementation
├── package.json        # Node.js dependencies
├── requirements.txt    # Python dependencies
├── CLAUDE.md          # Development instructions
└── README.md          # This file
```

## 🎨 Screenshots

The application features:
- Clean, modern interface
- Real-time progress tracking
- Detailed logging
- File selection options
- Processing controls

## 🔧 Troubleshooting

**Node.js server won't start:**
- Make sure Node.js is installed: `node --version`
- Try running `npm install` again

**No lyrics found:**
- Check your internet connection
- Some songs may not have lyrics available online
- Try different variations of artist/title names

**GUI doesn't open:**
- Tkinter should be included with Python
- On Linux: `sudo apt-get install python3-tk`

## 📝 License

MIT License - feel free to use and modify!

## 🤝 Contributing

Contributions are welcome! Feel free to:
- Add new lyrics sources
- Improve the GUI
- Add more audio format support
- Fix bugs

## ⚠️ Disclaimer

This tool is for personal use only. Please respect copyright laws and terms of service of the websites being scraped.
