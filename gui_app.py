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
        self.root.geometry("900x700")
        
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
        
        # Setup UI first (before starting server)
        self.setup_ui()
        
        # Start Node.js server after UI is ready
        self.start_node_server()
        
        # Bind close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
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
        title_label.grid(row=0, column=0, pady=(0, 10))
        
        # File selection frame with drag and drop
        selection_frame = ttk.LabelFrame(main_frame, text="Select Files or Folder", padding="10")
        selection_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=10)
        selection_frame.columnconfigure(0, weight=1)
        
        # Drag and drop area
        self.drop_frame = tk.Frame(selection_frame, bg='#f0f0f0', relief=tk.SUNKEN, bd=2, height=100)
        self.drop_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        drop_label = tk.Label(self.drop_frame, text="🎵 Drag & Drop Files or Folders Here 🎵\n\nor use buttons below", 
                             bg='#f0f0f0', font=('Arial', 12))
        drop_label.pack(expand=True, pady=20)
        
        # Enable drag and drop
        self.drop_frame.drop_target_register(DND_FILES)
        self.drop_frame.dnd_bind('<<Drop>>', self.on_drop)
        
        # Hover effect
        self.drop_frame.dnd_bind('<<DragEnter>>', lambda e: self.drop_frame.config(bg='#e0e0ff'))
        self.drop_frame.dnd_bind('<<DragLeave>>', lambda e: self.drop_frame.config(bg='#f0f0f0'))
        
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
        
        # Overwrite checkbox
        self.overwrite_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_frame, text="Overwrite existing lyrics", 
                       variable=self.overwrite_var).grid(row=0, column=0, sticky=tk.W)
        
        # Auto-detect info
        info_label = ttk.Label(options_frame, text="✓ Automatically detects all audio formats (MP3, M4A, FLAC, OGG, WAV, etc.)", 
                              foreground="#008000")
        info_label.grid(row=1, column=0, sticky=tk.W, pady=(10, 0))
        
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
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.grid(row=5, column=0, sticky=(tk.W, tk.E), pady=(5, 0))
        
    def start_node_server(self):
        """Start the Node.js Puppeteer server"""
        try:
            self.log("Starting Puppeteer server...")
            # Check if node_modules exists, if not install dependencies
            if not os.path.exists('node_modules'):
                self.log("Installing Node.js dependencies...")
                subprocess.run(['npm', 'install'], check=True, shell=True)
            
            # Start the Node.js server
            self.node_process = subprocess.Popen(
                ['node', 'scraper.js'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=True
            )
            
            # Wait for server to start
            time.sleep(3)
            
            # Test connection
            try:
                response = requests.post(f"{self.scraper_url}/init", timeout=5)
                if response.status_code == 200:
                    self.log("✓ Puppeteer server started successfully")
                    self.status_var.set("Server running - Ready to process files")
            except:
                self.log("⚠ Waiting for server to initialize...")
                time.sleep(2)
                
        except Exception as e:
            self.log(f"Error starting server: {e}")
            messagebox.showerror("Error", "Failed to start Puppeteer server. Make sure Node.js is installed.")
    
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
                self.files_label.config(text=f"Folder: {path.name}", foreground="black")
            else:
                self.files_label.config(text=f"File: {path.name}", foreground="black")
        else:
            self.files_label.config(text=f"{len(self.selected_files)} files selected", foreground="black")
    
    def log(self, message):
        """Add message to progress text"""
        self.progress_text.insert(tk.END, f"{message}\n")
        self.progress_text.see(tk.END)
        self.root.update()
    
    def is_audio_file(self, filepath: Path) -> bool:
        """Check if file is an audio file that mutagen can handle"""
        try:
            audio = mutagen.File(str(filepath))
            return audio is not None
        except:
            return False
    
    def get_audio_files(self) -> List[Path]:
        """Get all audio files based on selection"""
        audio_files = []
        
        for item in self.selected_files:
            path = Path(item)
            if path.is_file():
                if self.is_audio_file(path):
                    audio_files.append(path)
            elif path.is_dir():
                # Try common audio extensions first for speed
                common_exts = ['.mp3', '.m4a', '.mp4', '.flac', '.ogg', '.wav', '.wma', '.aac', '.opus']
                found_files = set()
                
                # First pass: common extensions
                for ext in common_exts:
                    for file in path.rglob(f'*{ext}'):
                        if file not in found_files and self.is_audio_file(file):
                            audio_files.append(file)
                            found_files.add(file)
                
                # Second pass: check all other files
                for file in path.rglob('*'):
                    if file.is_file() and file not in found_files:
                        if self.is_audio_file(file):
                            audio_files.append(file)
                            found_files.add(file)
        
        return audio_files
    
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
    
    def fetch_lyrics(self, title: str, artist: str) -> Optional[str]:
        """Fetch lyrics using Puppeteer server"""
        try:
            response = requests.post(
                f"{self.scraper_url}/scrape",
                json={'title': title, 'artist': artist},
                timeout=30
            )
            if response.status_code == 200:
                data = response.json()
                return data.get('lyrics')
        except Exception as e:
            self.log(f"Error fetching lyrics: {e}")
        return None
    
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
                # Vorbis comments (FLAC, OGG, Opus)
                audio['lyrics'] = lyrics
            
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
                return 'lyrics' in audio or 'LYRICS' in audio
            
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
    
    def process_files(self):
        """Process all selected files"""
        audio_files = self.get_audio_files()
        total = len(audio_files)
        
        if total == 0:
            self.log("No audio files found with selected extensions")
            return
        
        self.log(f"Found {total} audio files to process")
        self.log("=" * 50)
        
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
                continue
            
            # Read metadata
            info = self.read_metadata(filepath)
            if not info['title']:
                self.log("  ✗ Could not determine song title")
                failed += 1
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
                else:
                    self.log("  ✗ Failed to write lyrics")
                    failed += 1
            else:
                self.log("  ✗ No lyrics found")
                failed += 1
            
            # Small delay
            time.sleep(0.5)
        
        # Final summary
        self.log("\n" + "=" * 50)
        self.log("COMPLETED!")
        self.log(f"✓ Success: {success}/{total}")
        self.log(f"⊖ Skipped: {skipped}/{total}")
        self.log(f"✗ Failed: {failed}/{total}")
        
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