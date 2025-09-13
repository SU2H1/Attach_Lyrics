import os
import re
import json
import time
from pathlib import Path
from typing import Dict, Optional, Tuple
import mutagen
from mutagen.id3 import ID3, USLT, TIT2, TPE1, TPE2, TCOM
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4
from mutagen.flac import FLAC
from mutagen.oggvorbis import OggVorbis
import requests
from dataclasses import dataclass


@dataclass
class SongInfo:
    title: str = ""
    artist: str = ""
    album_artist: str = ""
    composer: str = ""
    album: str = ""
    lyrics: str = ""


class LyricsUpdater:
    def __init__(self, genius_token: Optional[str] = None):
        self.genius_token = genius_token
        self.genius_base_url = "https://api.genius.com"
        self.lyrics_ovh_url = "https://api.lyrics.ovh/v1"
        
    def extract_info_from_filename(self, filename: str) -> SongInfo:
        base_name = Path(filename).stem
        
        patterns = [
            r'^(?P<artist>[^-]+)\s*-\s*(?P<title>.+)$',
            r'^(?P<title>[^-]+)\s*-\s*(?P<artist>.+)$',
            r'^(?P<artist>[^\[\]]+)\s*\[(?P<album>[^\]]+)\]\s*-\s*(?P<title>.+)$',
            r'^(?P<title>.+)\s*\((?P<artist>[^\)]+)\)$',
        ]
        
        for pattern in patterns:
            match = re.match(pattern, base_name)
            if match:
                info = SongInfo()
                groups = match.groupdict()
                info.title = groups.get('title', '').strip()
                info.artist = groups.get('artist', '').strip()
                info.album = groups.get('album', '').strip()
                return info
        
        return SongInfo(title=base_name)
    
    def read_metadata(self, filepath: str) -> SongInfo:
        info = SongInfo()
        
        try:
            audio = mutagen.File(filepath)
            if audio is None:
                return self.extract_info_from_filename(filepath)
            
            if isinstance(audio, MP3) or hasattr(audio, 'tags'):
                tags = audio.tags
                if tags:
                    info.title = str(tags.get('TIT2', [''])[0]) if tags.get('TIT2') else ''
                    info.artist = str(tags.get('TPE1', [''])[0]) if tags.get('TPE1') else ''
                    info.album_artist = str(tags.get('TPE2', [''])[0]) if tags.get('TPE2') else ''
                    info.composer = str(tags.get('TCOM', [''])[0]) if tags.get('TCOM') else ''
                    info.album = str(tags.get('TALB', [''])[0]) if tags.get('TALB') else ''
                    
            elif isinstance(audio, MP4):
                info.title = audio.get('\xa9nam', [''])[0]
                info.artist = audio.get('\xa9ART', [''])[0]
                info.album_artist = audio.get('aART', [''])[0]
                info.composer = audio.get('\xa9wrt', [''])[0]
                info.album = audio.get('\xa9alb', [''])[0]
                
            elif isinstance(audio, (FLAC, OggVorbis)):
                info.title = audio.get('title', [''])[0]
                info.artist = audio.get('artist', [''])[0]
                info.album_artist = audio.get('albumartist', [''])[0]
                info.composer = audio.get('composer', [''])[0]
                info.album = audio.get('album', [''])[0]
            
            if not info.title and not info.artist:
                filename_info = self.extract_info_from_filename(filepath)
                info.title = filename_info.title or info.title
                info.artist = filename_info.artist or info.artist
                
        except Exception as e:
            print(f"Error reading metadata from {filepath}: {e}")
            info = self.extract_info_from_filename(filepath)
        
        return info
    
    def fetch_lyrics_genius(self, title: str, artist: str) -> Optional[str]:
        if not self.genius_token:
            return None
            
        headers = {'Authorization': f'Bearer {self.genius_token}'}
        
        search_url = f"{self.genius_base_url}/search"
        params = {'q': f"{artist} {title}"}
        
        try:
            response = requests.get(search_url, headers=headers, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                hits = data.get('response', {}).get('hits', [])
                
                if hits:
                    song_path = hits[0]['result']['path']
                    lyrics_url = f"https://genius.com{song_path}"
                    
                    import lyricsgenius
                    genius = lyricsgenius.Genius(self.genius_token, verbose=False)
                    song = genius.search_song(title, artist)
                    if song:
                        return song.lyrics
        except Exception as e:
            print(f"Genius API error: {e}")
        
        return None
    
    def fetch_lyrics_ovh(self, title: str, artist: str) -> Optional[str]:
        try:
            response = requests.get(
                f"{self.lyrics_ovh_url}/{artist}/{title}",
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                return data.get('lyrics', '')
        except Exception as e:
            print(f"Lyrics.ovh API error: {e}")
        
        return None
    
    def fetch_lyrics_chartlyrics(self, title: str, artist: str) -> Optional[str]:
        try:
            search_url = "http://api.chartlyrics.com/apiv1.asmx/SearchLyricDirect"
            params = {'artist': artist, 'song': title}
            response = requests.get(search_url, params=params, timeout=10)
            
            if response.status_code == 200:
                import xml.etree.ElementTree as ET
                root = ET.fromstring(response.content)
                lyrics_elem = root.find('.//{http://api.chartlyrics.com/}Lyric')
                if lyrics_elem is not None and lyrics_elem.text:
                    return lyrics_elem.text
        except Exception as e:
            print(f"ChartLyrics API error: {e}")
        
        return None
    
    def fetch_lyrics(self, title: str, artist: str) -> Optional[str]:
        if not title or not artist:
            return None
        
        print(f"Fetching lyrics for: {artist} - {title}")
        
        lyrics = self.fetch_lyrics_genius(title, artist)
        if lyrics:
            print("Found lyrics via Genius API")
            return lyrics
        
        lyrics = self.fetch_lyrics_ovh(title, artist)
        if lyrics:
            print("Found lyrics via Lyrics.ovh API")
            return lyrics
        
        lyrics = self.fetch_lyrics_chartlyrics(title, artist)
        if lyrics:
            print("Found lyrics via ChartLyrics API")
            return lyrics
        
        print("No lyrics found from any source")
        return None
    
    def write_lyrics_to_file(self, filepath: str, lyrics: str) -> bool:
        try:
            audio = mutagen.File(filepath)
            if audio is None:
                print(f"Cannot open audio file: {filepath}")
                return False
            
            if isinstance(audio, MP3):
                if audio.tags is None:
                    audio.add_tags()
                audio.tags.add(USLT(encoding=3, lang='eng', desc='', text=lyrics))
                
            elif isinstance(audio, MP4):
                audio['\xa9lyr'] = lyrics
                
            elif isinstance(audio, (FLAC, OggVorbis)):
                audio['lyrics'] = lyrics
            else:
                print(f"Unsupported file format for: {filepath}")
                return False
            
            audio.save()
            print(f"Successfully added lyrics to: {filepath}")
            return True
            
        except Exception as e:
            print(f"Error writing lyrics to {filepath}: {e}")
            return False
    
    def process_file(self, filepath: str) -> bool:
        print(f"\nProcessing: {filepath}")
        
        info = self.read_metadata(filepath)
        
        if not info.title:
            print(f"Could not determine song title for: {filepath}")
            return False
        
        print(f"Identified: {info.artist or 'Unknown Artist'} - {info.title}")
        
        lyrics = self.fetch_lyrics(info.title, info.artist)
        
        if lyrics:
            return self.write_lyrics_to_file(filepath, lyrics)
        else:
            print(f"No lyrics found for: {info.artist} - {info.title}")
            return False
    
    def process_directory(self, directory: str, extensions: list = None):
        if extensions is None:
            extensions = ['.mp3', '.m4a', '.mp4', '.flac', '.ogg']
        
        path = Path(directory)
        audio_files = []
        
        for ext in extensions:
            audio_files.extend(path.rglob(f'*{ext}'))
        
        total = len(audio_files)
        success = 0
        
        print(f"Found {total} audio files to process")
        
        for i, file in enumerate(audio_files, 1):
            print(f"\n[{i}/{total}] ", end='')
            if self.process_file(str(file)):
                success += 1
            time.sleep(0.5)
        
        print(f"\n\nCompleted! Successfully added lyrics to {success}/{total} files")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Add lyrics to audio files')
    parser.add_argument('path', help='File or directory to process')
    parser.add_argument('--genius-token', help='Genius API token for better results')
    parser.add_argument('--extensions', nargs='+', default=['.mp3', '.m4a', '.mp4', '.flac', '.ogg'],
                      help='File extensions to process')
    
    args = parser.parse_args()
    
    updater = LyricsUpdater(genius_token=args.genius_token)
    
    path = Path(args.path)
    if path.is_file():
        updater.process_file(str(path))
    elif path.is_dir():
        updater.process_directory(str(path), args.extensions)
    else:
        print(f"Error: {args.path} is not a valid file or directory")


if __name__ == "__main__":
    main()