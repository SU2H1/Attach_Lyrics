import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from tkinterdnd2 import DND_FILES, TkinterDnD
import threading
import subprocess
import os
import sys
import time
import json
import requests
from pathlib import Path
from typing import Optional, List
import mutagen
from mutagen.id3 import ID3, USLT, TIT2, TPE1, TALB, TCOM
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4
from mutagen.flac import FLAC
from mutagen.oggvorbis import OggVorbis
from mutagen.wave import WAVE
from mutagen.asf import ASF
from mutagen.aac import AAC
from mutagen.oggopus import OggOpus


class LyricsApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Lyrics Updater - Add Lyrics to Your Music")
        self.root.geometry("950x750")

        # Set icon if available
        try:
            self.root.iconbitmap(default='icon.ico')
        except:
            pass

        # Variables
        self.selected_files = []
        self.processing = False
        self.node_process = None
        self.scraper_url = "http://localhost:3000"
        self.server_ready = False
        self.stats = {'success': 0, 'failed': 0, 'skipped': 0}
        self.failed_files = []  # Track files that failed to get lyrics

        # File type selection variables
        self.file_types = {
            'mp3': tk.BooleanVar(value=True),
            'm4a': tk.BooleanVar(value=True),
            'flac': tk.BooleanVar(value=True),
            'ogg': tk.BooleanVar(value=True),
            'wav': tk.BooleanVar(value=True),
            'wma': tk.BooleanVar(value=True),
            'aac': tk.BooleanVar(value=True),
            'opus': tk.BooleanVar(value=True),
            'other': tk.BooleanVar(value=False)  # webm, mkv, avi, etc.
        }

        # Setup UI first (before starting server)
        self.setup_ui()

        # Start Node.js server after UI is ready
        self.start_node_server()

        # Bind close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Keyboard shortcuts
        self.root.bind('<Control-o>', lambda e: self.select_files())
        self.root.bind('<Control-d>', lambda e: self.select_folder())
        self.root.bind('<Control-l>', lambda e: self.clear_log())
        self.root.bind('<F5>', lambda e: self.start_processing() if self.start_button['state'] == 'normal' else None)
        
    def setup_ui(self):
        # Style
        style = ttk.Style()
        style.theme_use('clam')
        
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="🎵 Lyrics Updater", font=('Arial', 20, 'bold'))
        title_label.grid(row=0, column=0, pady=(0, 5))

        # Subtitle with shortcuts info
        subtitle_label = ttk.Label(main_frame,
                                  text="Keyboard shortcuts: Ctrl+O (Files), Ctrl+D (Folder), Ctrl+L (Clear Log), F5 (Start)",
                                  font=('Arial', 8), foreground='gray')
        subtitle_label.grid(row=0, column=0, pady=(25, 10), sticky='s')
        
        # File selection frame with drag and drop
        selection_frame = ttk.LabelFrame(main_frame, text="Select Files or Folder", padding="10")
        selection_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=10)
        selection_frame.columnconfigure(0, weight=1)
        
        # Drag and drop area
        self.drop_frame = tk.Frame(selection_frame, bg='#f0f0f0', relief=tk.SUNKEN, bd=2, height=100)
        self.drop_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        self.drop_label = tk.Label(self.drop_frame, text="🎵 Drag & Drop Files or Folders Here 🎵\n\nor use buttons below",
                                  bg='#f0f0f0', font=('Arial', 12))
        self.drop_label.pack(expand=True, pady=20)
        
        # Enable drag and drop
        self.drop_frame.drop_target_register(DND_FILES)
        self.drop_frame.dnd_bind('<<Drop>>', self.on_drop)
        
        # Hover effect
        self.drop_frame.dnd_bind('<<DragEnter>>', self.on_drag_enter)
        self.drop_frame.dnd_bind('<<DragLeave>>', self.on_drag_leave)
        
        # Buttons
        button_frame = ttk.Frame(selection_frame)
        button_frame.grid(row=1, column=0, pady=(10, 0))
        
        ttk.Button(button_frame, text="Select Files", command=self.select_files).grid(row=0, column=0, padx=5)
        ttk.Button(button_frame, text="Select Folder", command=self.select_folder).grid(row=0, column=1, padx=5)
        ttk.Button(button_frame, text="Clear Selection", command=self.clear_selection).grid(row=0, column=2, padx=5)
        
        # Selected files label
        self.files_label = ttk.Label(selection_frame, text="No files selected", foreground="gray")
        self.files_label.grid(row=2, column=0, pady=(10, 0))
        
        # Options frame
        options_frame = ttk.LabelFrame(main_frame, text="Options", padding="10")
        options_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=10)
        options_frame.columnconfigure(1, weight=1)

        # Overwrite checkbox
        self.overwrite_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_frame, text="Overwrite existing lyrics",
                       variable=self.overwrite_var).grid(row=0, column=0, sticky=tk.W)

        # Server status
        self.server_status_label = ttk.Label(options_frame, text="Server: Starting...",
                                           foreground="orange")
        self.server_status_label.grid(row=0, column=1, sticky=tk.E, padx=(10, 0))

        # Auto-detect info
        self.info_label = ttk.Label(options_frame, text="✓ Processing selected file types only",
                                   foreground="#008000")
        self.info_label.grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(10, 0))

        # File type selection frame
        file_types_frame = ttk.LabelFrame(options_frame, text="File Types to Process", padding="5")
        file_types_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))

        # Create checkboxes for file types
        row = 0
        col = 0
        for file_type, var in self.file_types.items():
            if file_type == 'other':
                text = "Other (WebM, MKV, AVI)"
            else:
                text = file_type.upper()

            ttk.Checkbutton(file_types_frame, text=text, variable=var).grid(
                row=row, column=col, sticky=tk.W, padx=(0, 15)
            )

            col += 1
            if col > 4:  # 5 columns
                col = 0
                row += 1

        # Select/Deselect all buttons
        select_buttons_frame = ttk.Frame(file_types_frame)
        select_buttons_frame.grid(row=row+1, column=0, columnspan=5, pady=(5, 0))

        ttk.Button(select_buttons_frame, text="Select All",
                  command=self.select_all_file_types).grid(row=0, column=0, padx=5)
        ttk.Button(select_buttons_frame, text="Deselect All",
                  command=self.deselect_all_file_types).grid(row=0, column=1, padx=5)
        ttk.Button(select_buttons_frame, text="Common Only",
                  command=self.select_common_file_types).grid(row=0, column=2, padx=5)

        # Stats frame
        stats_frame = ttk.Frame(options_frame)
        stats_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))

        ttk.Label(stats_frame, text="Session Stats:").grid(row=0, column=0, sticky=tk.W)
        self.stats_label = ttk.Label(stats_frame, text="Success: 0 | Failed: 0 | Skipped: 0",
                                    foreground="gray")
        self.stats_label.grid(row=0, column=1, sticky=tk.W, padx=(10, 0))
        
        # Progress frame
        progress_frame = ttk.LabelFrame(main_frame, text="Progress", padding="10")
        progress_frame.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        progress_frame.columnconfigure(0, weight=1)
        progress_frame.rowconfigure(1, weight=1)
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Progress text
        self.progress_text = scrolledtext.ScrolledText(progress_frame, height=15, width=70, wrap=tk.WORD)
        self.progress_text.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Control buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, pady=10)
        
        self.start_button = ttk.Button(button_frame, text="Start Processing",
                                      command=self.start_processing, state=tk.DISABLED)
        self.start_button.grid(row=0, column=0, padx=5)

        self.stop_button = ttk.Button(button_frame, text="Stop",
                                     command=self.stop_processing, state=tk.DISABLED)
        self.stop_button.grid(row=0, column=1, padx=5)

        self.clear_log_button = ttk.Button(button_frame, text="Clear Log",
                                         command=self.clear_log)
        self.clear_log_button.grid(row=0, column=2, padx=5)

        self.show_failed_button = ttk.Button(button_frame, text="Show Failed Files",
                                            command=self.show_failed_files, state=tk.DISABLED)
        self.show_failed_button.grid(row=0, column=3, padx=5)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.grid(row=5, column=0, sticky=(tk.W, tk.E), pady=(5, 0))
        
    def start_node_server(self):
        """Start the Node.js Puppeteer server"""
        def server_startup():
            try:
                self.log("Starting Puppeteer server...")
                self.server_status_label.config(text="Server: Starting...", foreground="orange")

                # Check if node_modules exists, if not install dependencies
                if not os.path.exists('node_modules'):
                    self.log("Installing Node.js dependencies...")
                    self.server_status_label.config(text="Server: Installing deps...", foreground="orange")
                    result = subprocess.run(['npm', 'install'], capture_output=True, text=True, shell=True)
                    if result.returncode != 0:
                        raise Exception(f"npm install failed: {result.stderr}")

                # Start the Node.js server
                self.node_process = subprocess.Popen(
                    ['node', 'scraper.js'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    shell=True
                )

                # Wait for server to start
                max_attempts = 15  # Increased attempts
                for attempt in range(max_attempts):
                    time.sleep(2)  # Longer sleep between attempts
                    try:
                        # Test if server is responding
                        response = requests.get(f"{self.scraper_url}", timeout=5)
                        if response.status_code == 404:  # Server is up, just no route
                            # Now try to initialize
                            init_response = requests.post(f"{self.scraper_url}/init", timeout=10)
                            if init_response.status_code == 200:
                                self.log("✓ Puppeteer server started successfully")
                                self.server_ready = True
                                self.server_status_label.config(text="Server: Ready ✓", foreground="green")
                                self.status_var.set("Server running - Ready to process files")
                                return
                    except requests.exceptions.ConnectionError:
                        self.log(f"  Waiting for server... (attempt {attempt + 1}/{max_attempts})")
                        continue
                    except Exception as e:
                        self.log(f"  Server check error: {e}")
                        continue

                # Server didn't start properly
                self.log("⚠ Server startup timeout - using fallback mode")
                self.server_status_label.config(text="Server: Fallback mode", foreground="orange")
                self.status_var.set("Using fallback scraping - Ready to process files")

            except Exception as e:
                self.log(f"✗ Error starting server: {e}")
                self.log("Will use fallback scraping method")
                self.server_status_label.config(text="Server: Failed", foreground="red")
                self.status_var.set("Using fallback scraping - Ready to process files")

        # Start server in background thread
        threading.Thread(target=server_startup, daemon=True).start()

    def select_all_file_types(self):
        """Select all file types"""
        for var in self.file_types.values():
            var.set(True)

    def deselect_all_file_types(self):
        """Deselect all file types"""
        for var in self.file_types.values():
            var.set(False)

    def select_common_file_types(self):
        """Select only common file types (MP3, M4A, FLAC)"""
        for file_type, var in self.file_types.items():
            if file_type in ['mp3', 'm4a', 'flac']:
                var.set(True)
            else:
                var.set(False)

    def on_drag_enter(self, event):
        """Handle drag enter event"""
        self.drop_frame.config(bg='#e0e0ff')
        self.drop_label.config(bg='#e0e0ff', text="🎵 Drop files here! 🎵")

    def on_drag_leave(self, event):
        """Handle drag leave event"""
        self.drop_frame.config(bg='#f0f0f0')
        self.drop_label.config(bg='#f0f0f0', text="🎵 Drag & Drop Files or Folders Here 🎵\n\nor use buttons below")

    def on_drop(self, event):
        """Handle drag and drop events"""
        # Reset hover color
        self.drop_frame.config(bg='#f0f0f0')
        
        # Parse dropped files/folders
        files = self.root.tk.splitlist(event.data)
        self.process_dropped_items(files)
    
    def process_dropped_items(self, items):
        """Process dropped files or folders"""
        processed_items = []
        for item in items:
            # Remove curly braces if present (Windows drag and drop quirk)
            item = item.strip('{}').strip('"')
            if os.path.exists(item):
                processed_items.append(item)
        
        if processed_items:
            self.selected_files = processed_items
            self.update_file_label()
            self.start_button.config(state=tk.NORMAL)
    
    def select_files(self):
        files = filedialog.askopenfilenames(
            title="Select Audio Files",
            filetypes=[
                ("All Audio Files", "*.mp3;*.m4a;*.mp4;*.flac;*.ogg;*.wav;*.wma;*.aac;*.opus;*.webm;*.mkv;*.avi"),
                ("MP3 Files", "*.mp3"),
                ("M4A Files", "*.m4a"),
                ("FLAC Files", "*.flac"),
                ("All Files", "*.*")
            ]
        )
        if files:
            self.selected_files = list(files)
            self.update_file_label()
            self.start_button.config(state=tk.NORMAL)
    
    def select_folder(self):
        folder = filedialog.askdirectory(title="Select Folder Containing Audio Files")
        if folder:
            self.selected_files = [folder]
            self.update_file_label()
            self.start_button.config(state=tk.NORMAL)
    
    def clear_selection(self):
        self.selected_files = []
        self.update_file_label()
        self.start_button.config(state=tk.DISABLED)
    
    def update_file_label(self):
        if not self.selected_files:
            self.files_label.config(text="No files selected", foreground="gray")
        elif len(self.selected_files) == 1:
            path = Path(self.selected_files[0])
            if path.is_dir():
                # Don't count files immediately for performance
                self.files_label.config(text=f"Folder: {path.name} (scanning will start when processing)", foreground="black")
            else:
                self.files_label.config(text=f"File: {path.name}", foreground="black")
        else:
            # Don't count files immediately for performance
            self.files_label.config(text=f"{len(self.selected_files)} items selected", foreground="black")
    
    def log(self, message):
        """Add message to progress text"""
        self.progress_text.insert(tk.END, f"{message}\n")
        self.progress_text.see(tk.END)
        self.root.update()

    def clear_log(self):
        """Clear the progress log"""
        self.progress_text.delete(1.0, tk.END)
    
    def is_audio_file(self, filepath: Path) -> bool:
        """Check if file is an audio file that mutagen can handle"""
        try:
            audio = mutagen.File(str(filepath))
            return audio is not None
        except:
            return False
    
    def get_audio_files(self, max_files: int = None, show_progress: bool = True) -> List[Path]:
        """Get all audio files based on selection with optimized scanning"""
        audio_files = []

        for item in self.selected_files:
            path = Path(item)
            if path.is_file():
                if self.is_audio_file_quick(path):
                    audio_files.append(path)
            elif path.is_dir():
                if show_progress:
                    self.log(f"Scanning folder: {path.name}...")
                    self.status_var.set("Scanning for audio files...")

                # Get selected extensions based on user preferences
                selected_extensions = self.get_selected_extensions()

                if not selected_extensions:
                    if show_progress:
                        self.log("No file types selected! Please select at least one file type.")
                    return audio_files

                for ext in selected_extensions:
                    try:
                        # Use glob instead of rglob for better control
                        for file in path.rglob(f'*{ext}'):
                            if file.is_file() and self.is_audio_file_quick(file):
                                audio_files.append(file)

                                # Check file limit
                                if max_files and len(audio_files) >= max_files:
                                    if show_progress:
                                        self.log(f"Reached file limit of {max_files} files")
                                    return audio_files

                                # Show progress every 100 files
                                if show_progress and len(audio_files) % 100 == 0:
                                    self.status_var.set(f"Found {len(audio_files)} audio files...")
                                    self.root.update_idletasks()
                    except Exception as e:
                        if show_progress:
                            self.log(f"Error scanning {ext} files: {e}")
                        continue

        return audio_files

    def get_selected_extensions(self):
        """Get list of file extensions based on user selection"""
        extensions = []

        if self.file_types['mp3'].get():
            extensions.extend(['.mp3'])
        if self.file_types['m4a'].get():
            extensions.extend(['.m4a', '.mp4'])
        if self.file_types['flac'].get():
            extensions.extend(['.flac'])
        if self.file_types['ogg'].get():
            extensions.extend(['.ogg', '.oga'])
        if self.file_types['wav'].get():
            extensions.extend(['.wav', '.wave'])
        if self.file_types['wma'].get():
            extensions.extend(['.wma'])
        if self.file_types['aac'].get():
            extensions.extend(['.aac'])
        if self.file_types['opus'].get():
            extensions.extend(['.opus'])
        if self.file_types['other'].get():
            extensions.extend(['.webm', '.mkv', '.avi', '.wv', '.ape'])

        return extensions

    def is_audio_file_quick(self, filepath: Path) -> bool:
        """Quick check if file is audio based on extension and user selection"""
        ext = filepath.suffix.lower()

        # Map extensions to our file type categories
        extension_map = {
            '.mp3': 'mp3',
            '.m4a': 'm4a', '.mp4': 'm4a',  # MP4 audio files usually M4A
            '.flac': 'flac',
            '.ogg': 'ogg', '.oga': 'ogg',
            '.wav': 'wav', '.wave': 'wav',
            '.wma': 'wma',
            '.aac': 'aac',
            '.opus': 'opus',
            '.webm': 'other', '.mkv': 'other', '.avi': 'other',
            '.wv': 'other', '.ape': 'other'
        }

        # Check if extension is supported
        if ext not in extension_map:
            return False

        # Check if user has selected this file type
        file_type = extension_map[ext]
        return self.file_types[file_type].get()
    
    def read_metadata(self, filepath: Path) -> dict:
        """Read metadata from audio file"""
        info = {'title': '', 'artist': ''}
        
        try:
            audio = mutagen.File(str(filepath))
            if not audio:
                return self.parse_filename(filepath.stem)
            
            # Handle different audio formats
            if hasattr(audio, 'tags') and audio.tags:
                # ID3 tags (MP3, WAV with ID3)
                if hasattr(audio.tags, 'get'):
                    info['title'] = str(audio.tags.get('TIT2', [''])[0]) if audio.tags.get('TIT2') else ''
                    info['artist'] = str(audio.tags.get('TPE1', [''])[0]) if audio.tags.get('TPE1') else ''
            
            # MP4/M4A/AAC format
            if isinstance(audio, (MP4, AAC)) or (hasattr(audio, 'mime') and 'mp4' in str(audio.mime)):
                info['title'] = audio.get('\xa9nam', [''])[0] if audio.get('\xa9nam') else ''
                info['artist'] = audio.get('\xa9ART', [''])[0] if audio.get('\xa9ART') else ''
            
            # Vorbis comments (FLAC, OGG, Opus)
            elif isinstance(audio, (FLAC, OggVorbis, OggOpus)) or hasattr(audio, 'get'):
                info['title'] = audio.get('title', [''])[0] if audio.get('title') else ''
                info['artist'] = audio.get('artist', [''])[0] if audio.get('artist') else ''
            
            # ASF format (WMA)
            elif isinstance(audio, ASF):
                info['title'] = str(audio.get('Title', [''])[0]) if audio.get('Title') else ''
                info['artist'] = str(audio.get('Author', [''])[0]) if audio.get('Author') else ''
            
            # Generic fallback for any format
            if not info['title'] and not info['artist']:
                # Try common tag names
                common_title_tags = ['TIT2', 'TITLE', 'Title', '\xa9nam', 'title']
                common_artist_tags = ['TPE1', 'ARTIST', 'Artist', '\xa9ART', 'artist', 'Author']
                
                for tag in common_title_tags:
                    if hasattr(audio, 'get') and audio.get(tag):
                        val = audio.get(tag)
                        info['title'] = str(val[0] if isinstance(val, list) else val)
                        break
                
                for tag in common_artist_tags:
                    if hasattr(audio, 'get') and audio.get(tag):
                        val = audio.get(tag)
                        info['artist'] = str(val[0] if isinstance(val, list) else val)
                        break
            
            # Final fallback to filename parsing
            if not info['title']:
                parsed = self.parse_filename(filepath.stem)
                info['title'] = parsed['title'] or info['title']
                info['artist'] = parsed['artist'] or info['artist']
                
        except Exception as e:
            self.log(f"Error reading metadata from {filepath.name}: {e}")
            return self.parse_filename(filepath.stem)
        
        return info
    
    def parse_filename(self, filename: str) -> dict:
        """Parse artist and title from filename"""
        # Try common patterns
        patterns = [
            r'^(?P<artist>[^-]+)\s*-\s*(?P<title>.+)$',
            r'^(?P<title>[^-]+)\s*-\s*(?P<artist>.+)$',
        ]
        
        import re
        for pattern in patterns:
            match = re.match(pattern, filename)
            if match:
                return {
                    'title': match.group('title').strip() if 'title' in match.groupdict() else '',
                    'artist': match.group('artist').strip() if 'artist' in match.groupdict() else ''
                }
        
        return {'title': filename, 'artist': ''}
    
    def clean_lyrics(self, lyrics: str) -> str:
        """Clean scraped lyrics from unwanted text patterns"""
        if not lyrics:
            return lyrics

        import re

        cleaned = lyrics

        # Remove common unwanted patterns
        unwanted_patterns = [
            # Contributors and translation info
            r'\d+\s*Contributors?',
            r'Translations?\w*',
            r'\d+\s*Embed',

            # Song title repetition at start (e.g., "Love in My Pocket Lyrics")
            r'^.*?Lyrics\s*',

            # Language indicators
            r'Español|Français|Deutsch|Italiano|Português|العربية|中文|日本語|한국어|Русский',

            # Website metadata
            r'genius\.com|azlyrics\.com|lyrics\.com',
            r'\bgenius\b|\bazlyrics\b',

            # Copyright and legal text
            r'©.*?\d{4}',
            r'All rights reserved',
            r'Powered by.*$',

            # Social media and sharing
            r'Share on Facebook|Tweet|Share|Like|Follow',
            r'www\.|http[s]?://',

            # Advertisement text
            r'Advertisement',
            r'Sponsored',

            # Navigation elements
            r'Home|About|Contact|Privacy|Terms',

            # Common metadata patterns
            r'Album:|Artist:|Released:',
            r'\bfrom the album\b',

            # Multiple spaces, tabs, newlines
            r'\s{3,}',
            r'\t+',
            r'\n{3,}'
        ]

        # Apply all patterns
        for pattern in unwanted_patterns:
            cleaned = re.sub(pattern, ' ', cleaned, flags=re.IGNORECASE | re.MULTILINE)

        # Clean up structure
        lines = [line.strip() for line in cleaned.split('\n')]
        filtered_lines = []

        for line in lines:
            # Remove lines that are likely metadata
            if len(line) == 0:
                continue
            if re.match(r'^\d+$', line):  # Just numbers
                continue
            if re.match(r'^[^\w]*$', line):  # Just punctuation
                continue
            if len(line) < 3 and not re.match(r'^[A-Za-z]+$', line):  # Very short non-word lines
                continue
            filtered_lines.append(line)

        cleaned = '\n'.join(filtered_lines)
        cleaned = re.sub(r'\n{2,}', '\n\n', cleaned)  # Max 2 consecutive newlines

        return cleaned.strip()

    def fetch_lyrics_fallback(self, title: str, artist: str) -> Optional[str]:
        """Fallback lyrics fetching using direct requests (no Puppeteer)"""
        from urllib.parse import quote
        import re

        # Try Genius (works without JavaScript)
        try:
            clean_artist = re.sub(r'[^a-zA-Z0-9]', '-', artist).strip('-').lower()
            clean_title = re.sub(r'[^a-zA-Z0-9]', '-', title).strip('-').lower()
            url = f"https://genius.com/{clean_artist}-{clean_title}-lyrics"

            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.text, 'html.parser')

                # Look for lyrics containers
                lyrics_divs = soup.find_all('div', {'data-lyrics-container': 'true'})
                if lyrics_divs:
                    lyrics_text = []
                    for div in lyrics_divs:
                        for br in div.find_all('br'):
                            br.replace_with('\n')
                        lyrics_text.append(div.get_text())
                    raw_lyrics = '\n'.join(lyrics_text).strip()
                    return self.clean_lyrics(raw_lyrics)
        except Exception as e:
            self.log(f"Genius fallback failed: {e}")

        # Try AZLyrics fallback
        try:
            clean_artist = re.sub(r'[^a-z0-9]', '', artist.lower())
            clean_title = re.sub(r'[^a-z0-9]', '', title.lower())
            url = f"https://www.azlyrics.com/lyrics/{clean_artist}/{clean_title}.html"

            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')

                # Find lyrics div (usually the largest div without class/id)
                for div in soup.find_all('div'):
                    if not div.get('class') and not div.get('id'):
                        text = div.get_text().strip()
                        if len(text) > 200 and '\n' in text:
                            return self.clean_lyrics(text)
        except Exception as e:
            self.log(f"AZLyrics fallback failed: {e}")

        return None
    
    def fetch_lyrics(self, title: str, artist: str) -> Optional[str]:
        """Fetch lyrics using Puppeteer server with fallback"""
        # Try Puppeteer first if server is ready
        if self.server_ready:
            try:
                response = requests.post(
                    f"{self.scraper_url}/scrape",
                    json={'title': title, 'artist': artist},
                    timeout=30
                )
                if response.status_code == 200:
                    data = response.json()
                    lyrics = data.get('lyrics')
                    if lyrics and len(lyrics.strip()) > 50:  # Ensure we got meaningful lyrics
                        return lyrics
                elif response.status_code >= 500:
                    # Server error, mark as not ready
                    self.server_ready = False
                    self.server_status_label.config(text="Server: Error", foreground="red")
            except requests.exceptions.ConnectionError:
                # Server died, mark as not ready
                self.server_ready = False
                self.server_status_label.config(text="Server: Disconnected", foreground="red")
                self.log("Server connection lost, using fallback...")
            except Exception as e:
                self.log(f"Puppeteer error: {e}")

        # Fallback to direct scraping (don't log error if server wasn't ready)
        if not self.server_ready:
            pass  # Server wasn't available, use fallback silently
        else:
            self.log("Puppeteer failed, using fallback...")

        return self.fetch_lyrics_fallback(title, artist)
    
    def write_lyrics(self, filepath: Path, lyrics: str) -> bool:
        """Write lyrics to audio file"""
        try:
            audio = mutagen.File(str(filepath))
            if not audio:
                return False
            
            # Handle different audio formats
            if isinstance(audio, MP3) or (hasattr(audio, 'tags') and hasattr(audio.tags, 'add')):
                # MP3 and other ID3-tagged formats
                if audio.tags is None:
                    audio.add_tags()
                audio.tags.add(USLT(encoding=3, lang='eng', desc='', text=lyrics))
            
            elif isinstance(audio, (MP4, AAC)) or (hasattr(audio, 'mime') and 'mp4' in str(audio.mime)):
                # MP4/M4A/AAC format
                audio['\xa9lyr'] = lyrics
            
            elif isinstance(audio, (FLAC, OggVorbis, OggOpus)):
                # Vorbis comments (FLAC, OGG, Opus) - MP3Tag compatible fields
                audio['LYRICS'] = lyrics
                audio['UNSYNCED LYRICS'] = lyrics  # MP3Tag uses this exact field name
            
            elif isinstance(audio, ASF):
                # WMA format
                audio['WM/Lyrics'] = lyrics
            
            elif isinstance(audio, WAVE):
                # WAV files - try to add ID3 tags
                if not hasattr(audio, 'tags') or audio.tags is None:
                    audio.add_tags()
                audio.tags.add(USLT(encoding=3, lang='eng', desc='', text=lyrics))
            
            else:
                # Generic fallback - try common approaches
                if hasattr(audio, '__setitem__'):
                    # Try vorbis-style first
                    try:
                        audio['lyrics'] = lyrics
                    except:
                        try:
                            audio['LYRICS'] = lyrics
                        except:
                            try:
                                audio['\xa9lyr'] = lyrics
                            except:
                                self.log(f"Unsupported format for lyrics: {filepath.suffix}")
                                return False
                else:
                    self.log(f"Cannot write lyrics to format: {filepath.suffix}")
                    return False
            
            audio.save()
            return True
            
        except Exception as e:
            self.log(f"Error writing lyrics to {filepath.name}: {e}")
            return False
    
    def check_has_lyrics(self, filepath: Path) -> bool:
        """Check if file already has lyrics"""
        try:
            audio = mutagen.File(str(filepath))
            if not audio:
                return False
            
            # Check for ID3 USLT frames (MP3, WAV)
            if hasattr(audio, 'tags') and audio.tags:
                if any(hasattr(frame, 'FrameID') and frame.FrameID == 'USLT' for frame in audio.tags.values()):
                    return True
            
            # Check MP4/M4A/AAC format
            if isinstance(audio, (MP4, AAC)) or (hasattr(audio, 'mime') and 'mp4' in str(audio.mime)):
                return '\xa9lyr' in audio
            
            # Check Vorbis comments (FLAC, OGG, Opus)
            elif isinstance(audio, (FLAC, OggVorbis, OggOpus)):
                return 'LYRICS' in audio or 'lyrics' in audio or 'UNSYNCED LYRICS' in audio
            
            # Check WMA format
            elif isinstance(audio, ASF):
                return 'WM/Lyrics' in audio or 'Lyrics' in audio
            
            # Generic check for any format
            else:
                # Check common lyrics field names
                lyrics_fields = ['lyrics', 'LYRICS', '\xa9lyr', 'WM/Lyrics', 'Lyrics']
                for field in lyrics_fields:
                    if hasattr(audio, '__contains__') and field in audio:
                        lyrics_content = audio.get(field)
                        if lyrics_content and (isinstance(lyrics_content, list) and lyrics_content[0] or lyrics_content):
                            return True
                
        except Exception as e:
            self.log(f"Error checking lyrics in {filepath.name}: {e}")
        
        return False
    
    def update_stats_display(self):
        """Update the statistics display"""
        self.stats_label.config(
            text=f"Success: {self.stats['success']} | Failed: {self.stats['failed']} | Skipped: {self.stats['skipped']}"
        )

    def reset_stats(self):
        """Reset statistics counters"""
        self.stats = {'success': 0, 'failed': 0, 'skipped': 0}
        self.failed_files = []
        self.show_failed_button.config(state=tk.DISABLED)
        self.update_stats_display()

    def check_server_health(self):
        """Check if Puppeteer server is still alive"""
        if not self.server_ready:
            return False

        try:
            response = requests.post(f"{self.scraper_url}/init", timeout=3)
            return response.status_code == 200
        except:
            self.server_ready = False
            self.server_status_label.config(text="Server: Disconnected", foreground="red")
            return False

    def process_files(self):
        """Process all selected files"""
        self.log("Scanning for audio files...")
        self.status_var.set("Scanning for audio files...")

        # Check server health before starting
        if self.server_ready:
            if self.check_server_health():
                self.log("✓ Puppeteer server is ready")
            else:
                self.log("⚠ Puppeteer server not responding, using fallback mode")

        # Get audio files with progress
        audio_files = self.get_audio_files(show_progress=True)
        total = len(audio_files)

        if total == 0:
            self.log("No audio files found with selected extensions")
            self.status_var.set("No audio files found")
            return

        # Reset stats for new processing session
        self.reset_stats()

        self.log(f"Found {total} audio files to process")
        self.log("=" * 50)

        # Warn if very large number of files
        if total > 1000:
            self.log(f"⚠ Large library detected ({total} files). This may take a while...")

        success = 0
        skipped = 0
        failed = 0
        
        for i, filepath in enumerate(audio_files):
            if not self.processing:
                break
            
            # Update progress
            progress = ((i + 1) / total) * 100
            self.progress_var.set(progress)
            self.status_var.set(f"Processing {i + 1}/{total}: {filepath.name}")
            
            self.log(f"\n[{i + 1}/{total}] Processing: {filepath.name}")
            
            # Check if has lyrics
            if not self.overwrite_var.get() and self.check_has_lyrics(filepath):
                self.log("  ✓ Already has lyrics, skipping")
                skipped += 1
                self.stats['skipped'] += 1
                self.update_stats_display()
                continue

            # Read metadata
            info = self.read_metadata(filepath)
            if not info['title']:
                self.log("  ✗ Could not determine song title")
                failed += 1
                self.stats['failed'] += 1
                self.failed_files.append({
                    'file': filepath.name,
                    'path': str(filepath),
                    'reason': 'Could not determine song title'
                })
                self.update_stats_display()
                continue

            self.log(f"  Song: {info['title']}")
            self.log(f"  Artist: {info['artist'] or 'Unknown'}")

            # Fetch lyrics
            self.log("  Searching for lyrics...")
            lyrics = self.fetch_lyrics(info['title'], info['artist'])

            if lyrics:
                # Write lyrics
                if self.write_lyrics(filepath, lyrics):
                    self.log("  ✓ Successfully added lyrics!")
                    success += 1
                    self.stats['success'] += 1
                    self.update_stats_display()
                else:
                    self.log("  ✗ Failed to write lyrics")
                    failed += 1
                    self.stats['failed'] += 1
                    self.failed_files.append({
                        'file': filepath.name,
                        'path': str(filepath),
                        'reason': 'Failed to write lyrics to file',
                        'title': info['title'],
                        'artist': info['artist'] or 'Unknown'
                    })
                    self.update_stats_display()
            else:
                self.log("  ✗ No lyrics found")
                failed += 1
                self.stats['failed'] += 1
                self.failed_files.append({
                    'file': filepath.name,
                    'path': str(filepath),
                    'reason': 'No lyrics found online',
                    'title': info['title'],
                    'artist': info['artist'] or 'Unknown'
                })
                self.update_stats_display()
            
            # Small delay
            time.sleep(0.5)
        
        # Final summary
        self.log("\n" + "=" * 60)
        self.log("🎵 PROCESSING COMPLETED! 🎵")
        self.log("=" * 60)
        self.log(f"📊 FINAL STATISTICS:")
        self.log(f"   ✓ Successfully processed: {success}/{total} ({success/total*100:.1f}%)")
        self.log(f"   ⊖ Skipped (already have lyrics): {skipped}/{total} ({skipped/total*100:.1f}%)")
        self.log(f"   ✗ Failed to process: {failed}/{total} ({failed/total*100:.1f}%)")
        self.log("=" * 60)

        if success > 0:
            self.log(f"🎉 Great! {success} files now have lyrics!")
        if failed > 0:
            self.log(f"💡 Tip: Failed files might have unusual titles or artists")
            self.log(f"📋 Click 'Show Failed Files' to see details")
            self.show_failed_button.config(state=tk.NORMAL)
            self.save_failed_files_report()

        self.status_var.set(f"Completed - Success: {success}, Skipped: {skipped}, Failed: {failed}")
    
    def start_processing(self):
        """Start processing in a separate thread"""
        if not self.selected_files:
            messagebox.showwarning("No Files", "Please select files or a folder first")
            return
        
        self.processing = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.progress_var.set(0)
        self.progress_text.delete(1.0, tk.END)
        
        # Start processing in a thread
        thread = threading.Thread(target=self.process_files)
        thread.start()
        
        # Monitor thread
        def check_thread():
            if thread.is_alive():
                self.root.after(100, check_thread)
            else:
                self.processing = False
                self.start_button.config(state=tk.NORMAL)
                self.stop_button.config(state=tk.DISABLED)
                if self.progress_var.get() >= 100:
                    messagebox.showinfo("Complete", "Processing completed!")
        
        check_thread()
    
    def stop_processing(self):
        """Stop processing"""
        self.processing = False
        self.log("\nProcessing stopped by user")
        self.status_var.set("Stopped")
    
    def save_failed_files_report(self):
        """Save a report of failed files to a text file"""
        if not self.failed_files:
            return

        try:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_file = f"failed_lyrics_report_{timestamp}.txt"

            with open(report_file, 'w', encoding='utf-8') as f:
                f.write("=" * 60 + "\n")
                f.write("FAILED LYRICS REPORT\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 60 + "\n\n")

                f.write(f"Total failed files: {len(self.failed_files)}\n\n")

                # Group by reason
                by_reason = {}
                for item in self.failed_files:
                    reason = item['reason']
                    if reason not in by_reason:
                        by_reason[reason] = []
                    by_reason[reason].append(item)

                for reason, files in by_reason.items():
                    f.write(f"\n{reason.upper()} ({len(files)} files):\n")
                    f.write("-" * 40 + "\n")
                    for file_info in files:
                        f.write(f"  File: {file_info['file']}\n")
                        if 'title' in file_info:
                            f.write(f"    Title: {file_info['title']}\n")
                            f.write(f"    Artist: {file_info['artist']}\n")
                        f.write(f"    Path: {file_info['path']}\n\n")

            self.log(f"📄 Failed files report saved: {report_file}")

        except Exception as e:
            self.log(f"Error saving report: {e}")

    def show_failed_files(self):
        """Show a window with failed files details"""
        if not self.failed_files:
            messagebox.showinfo("No Failed Files", "No files failed to get lyrics!")
            return

        # Create a new window
        failed_window = tk.Toplevel(self.root)
        failed_window.title("Failed Files Report")
        failed_window.geometry("800x600")

        # Main frame
        main_frame = ttk.Frame(failed_window, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        failed_window.columnconfigure(0, weight=1)
        failed_window.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)

        # Title
        title_label = ttk.Label(main_frame, text=f"Failed to Get Lyrics: {len(self.failed_files)} Files",
                               font=('Arial', 14, 'bold'))
        title_label.grid(row=0, column=0, pady=(0, 10))

        # Text area with scrollbar
        text_frame = ttk.Frame(main_frame)
        text_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)

        text_widget = scrolledtext.ScrolledText(text_frame, wrap=tk.WORD, width=80, height=25)
        text_widget.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Group by reason
        by_reason = {}
        for item in self.failed_files:
            reason = item['reason']
            if reason not in by_reason:
                by_reason[reason] = []
            by_reason[reason].append(item)

        # Display the information
        for reason, files in by_reason.items():
            text_widget.insert(tk.END, f"\n{reason.upper()} ({len(files)} files):\n", 'header')
            text_widget.insert(tk.END, "-" * 60 + "\n")

            for file_info in files:
                text_widget.insert(tk.END, f"  📁 {file_info['file']}\n", 'filename')
                if 'title' in file_info:
                    text_widget.insert(tk.END, f"      Title: {file_info['title']}\n")
                    text_widget.insert(tk.END, f"      Artist: {file_info['artist']}\n")
                text_widget.insert(tk.END, f"      Path: {file_info['path']}\n\n")

        # Configure text tags
        text_widget.tag_config('header', font=('Arial', 11, 'bold'), foreground='#0066cc')
        text_widget.tag_config('filename', font=('Arial', 10, 'bold'))

        # Make read-only
        text_widget.config(state=tk.DISABLED)

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, pady=(10, 0))

        def copy_to_clipboard():
            content = text_widget.get(1.0, tk.END)
            failed_window.clipboard_clear()
            failed_window.clipboard_append(content)
            messagebox.showinfo("Copied", "Report copied to clipboard!")

        ttk.Button(button_frame, text="Copy to Clipboard", command=copy_to_clipboard).grid(row=0, column=0, padx=5)
        ttk.Button(button_frame, text="Close", command=failed_window.destroy).grid(row=0, column=1, padx=5)

    def on_closing(self):
        """Clean up when closing"""
        if self.processing:
            if not messagebox.askokcancel("Quit", "Processing is in progress. Do you want to quit?"):
                return

        # Stop Node.js server
        if self.node_process:
            try:
                requests.post(f"{self.scraper_url}/close", timeout=2)
            except:
                pass
            self.node_process.terminate()

        self.root.destroy()


def main():
    # Use TkinterDnD for drag and drop support
    root = TkinterDnD.Tk()
    app = LyricsApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()