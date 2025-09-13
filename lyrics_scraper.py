import os
import re
import time
import urllib.parse
from pathlib import Path
from typing import Dict, Optional, List
import mutagen
from mutagen.id3 import ID3, USLT, TIT2, TPE1, TPE2, TCOM
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4
from mutagen.flac import FLAC
from mutagen.oggvorbis import OggVorbis
import requests
from bs4 import BeautifulSoup
from dataclasses import dataclass
import json


@dataclass
class SongInfo:
    title: str = ""
    artist: str = ""
    album_artist: str = ""
    composer: str = ""
    album: str = ""
    lyrics: str = ""


class LyricsScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
    def clean_text(self, text: str) -> str:
        text = re.sub(r'\([^)]*\)', '', text)
        text = re.sub(r'\[[^\]]*\]', '', text)
        text = re.sub(r'feat\.|ft\.|featuring', '', text, flags=re.IGNORECASE)
        text = re.sub(r'[^\w\s-]', '', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
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
    
    def scrape_genius(self, title: str, artist: str) -> Optional[str]:
        try:
            clean_artist = self.clean_text(artist).replace(' ', '-')
            clean_title = self.clean_text(title).replace(' ', '-')
            
            url = f"https://genius.com/{clean_artist}-{clean_title}-lyrics"
            
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                lyrics_divs = soup.find_all('div', {'data-lyrics-container': 'true'})
                if lyrics_divs:
                    lyrics = []
                    for div in lyrics_divs:
                        for br in div.find_all('br'):
                            br.replace_with('\n')
                        lyrics.append(div.get_text())
                    return '\n'.join(lyrics).strip()
                
                lyrics_div = soup.find('div', class_='lyrics')
                if lyrics_div:
                    return lyrics_div.get_text().strip()
                    
        except Exception as e:
            print(f"Genius scraping error: {e}")
        
        return None
    
    def scrape_azlyrics(self, title: str, artist: str) -> Optional[str]:
        try:
            clean_artist = re.sub(r'[^a-z0-9]', '', artist.lower())
            clean_title = re.sub(r'[^a-z0-9]', '', title.lower())
            
            url = f"https://www.azlyrics.com/lyrics/{clean_artist}/{clean_title}.html"
            
            response = self.session.get(url, timeout=10)
            time.sleep(1)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                lyrics_div = soup.find('div', class_=None, id=None)
                if lyrics_div:
                    comment = soup.find(string=lambda text: isinstance(text, str) and "Usage of azlyrics" in text)
                    if comment:
                        parent = comment.parent
                        lyrics_div = parent.find_next_sibling('div')
                        if lyrics_div:
                            lyrics = lyrics_div.get_text().strip()
                            return lyrics
                
                for div in soup.find_all('div'):
                    if not div.get('class') and not div.get('id'):
                        text = div.get_text().strip()
                        if len(text) > 200 and '\n' in text:
                            return text
                            
        except Exception as e:
            print(f"AZLyrics scraping error: {e}")
        
        return None
    
    def scrape_musixmatch(self, title: str, artist: str) -> Optional[str]:
        try:
            search_query = urllib.parse.quote(f"{artist} {title}")
            search_url = f"https://www.musixmatch.com/search/{search_query}"
            
            response = self.session.get(search_url, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                first_result = soup.find('a', class_='title')
                if first_result and 'href' in first_result.attrs:
                    lyrics_url = f"https://www.musixmatch.com{first_result['href']}"
                    
                    lyrics_response = self.session.get(lyrics_url, timeout=10)
                    if lyrics_response.status_code == 200:
                        lyrics_soup = BeautifulSoup(lyrics_response.text, 'html.parser')
                        
                        lyrics_spans = lyrics_soup.find_all('span', class_='lyrics__content__ok')
                        if lyrics_spans:
                            lyrics = '\n'.join([span.get_text() for span in lyrics_spans])
                            return lyrics.strip()
                            
        except Exception as e:
            print(f"Musixmatch scraping error: {e}")
        
        return None
    
    def scrape_songlyrics(self, title: str, artist: str) -> Optional[str]:
        try:
            clean_artist = re.sub(r'[^a-z0-9]', '-', artist.lower()).strip('-')
            clean_title = re.sub(r'[^a-z0-9]', '-', title.lower()).strip('-')
            
            url = f"http://www.songlyrics.com/{clean_artist}/{clean_title}-lyrics/"
            
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                lyrics_div = soup.find('p', id='songLyricsDiv')
                if lyrics_div:
                    lyrics = lyrics_div.get_text().strip()
                    if lyrics and not lyrics.startswith("We do not have"):
                        return lyrics
                        
        except Exception as e:
            print(f"SongLyrics scraping error: {e}")
        
        return None
    
    def scrape_lyrics_com(self, title: str, artist: str) -> Optional[str]:
        try:
            search_query = urllib.parse.quote(f"{artist} {title}")
            search_url = f"https://www.lyrics.com/serp.php?st={search_query}"
            
            response = self.session.get(search_url, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                first_result = soup.find('a', class_='lyric-meta-title')
                if first_result and 'href' in first_result.attrs:
                    lyrics_url = f"https://www.lyrics.com{first_result['href']}"
                    
                    lyrics_response = self.session.get(lyrics_url, timeout=10)
                    if lyrics_response.status_code == 200:
                        lyrics_soup = BeautifulSoup(lyrics_response.text, 'html.parser')
                        
                        lyrics_div = lyrics_soup.find('pre', id='lyric-body-text')
                        if lyrics_div:
                            return lyrics_div.get_text().strip()
                            
        except Exception as e:
            print(f"Lyrics.com scraping error: {e}")
        
        return None
    
    def google_search_lyrics(self, title: str, artist: str) -> Optional[str]:
        try:
            query = f"{artist} {title} lyrics"
            search_url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
            
            response = self.session.get(search_url, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                lyrics_div = soup.find('div', {'data-lyricid': True})
                if lyrics_div:
                    spans = lyrics_div.find_all('span')
                    if spans:
                        lyrics = '\n'.join([span.get_text() for span in spans])
                        return lyrics.strip()
                
                lyrics_div = soup.find('div', class_='PZPZlf')
                if lyrics_div:
                    return lyrics_div.get_text().strip()
                    
        except Exception as e:
            print(f"Google search error: {e}")
        
        return None
    
    def fetch_lyrics(self, title: str, artist: str) -> Optional[str]:
        if not title or not artist:
            return None
        
        print(f"Searching lyrics for: {artist} - {title}")
        
        scrapers = [
            ("Genius", self.scrape_genius),
            ("AZLyrics", self.scrape_azlyrics),
            ("Google", self.google_search_lyrics),
            ("Musixmatch", self.scrape_musixmatch),
            ("SongLyrics", self.scrape_songlyrics),
            ("Lyrics.com", self.scrape_lyrics_com),
        ]
        
        for name, scraper in scrapers:
            try:
                print(f"  Trying {name}...", end=' ')
                lyrics = scraper(title, artist)
                if lyrics and len(lyrics) > 100:
                    print("✓ Found!")
                    return lyrics
                else:
                    print("✗ Not found")
                time.sleep(0.5)
            except Exception as e:
                print(f"✗ Error: {e}")
        
        print("  No lyrics found from any source")
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
            print(f"✓ Successfully added lyrics to: {filepath}")
            return True
            
        except Exception as e:
            print(f"Error writing lyrics to {filepath}: {e}")
            return False
    
    def process_file(self, filepath: str, overwrite: bool = False) -> bool:
        print(f"\n{'='*60}")
        print(f"Processing: {Path(filepath).name}")
        print(f"{'='*60}")
        
        if not overwrite:
            try:
                audio = mutagen.File(filepath)
                if audio:
                    has_lyrics = False
                    if isinstance(audio, MP3) and audio.tags:
                        has_lyrics = any(frame.FrameID == 'USLT' for frame in audio.tags.values())
                    elif isinstance(audio, MP4):
                        has_lyrics = '\xa9lyr' in audio
                    elif isinstance(audio, (FLAC, OggVorbis)):
                        has_lyrics = 'lyrics' in audio
                    
                    if has_lyrics:
                        print("✓ File already has lyrics, skipping...")
                        return True
            except:
                pass
        
        info = self.read_metadata(filepath)
        
        if not info.title:
            print(f"✗ Could not determine song title")
            return False
        
        print(f"Song: {info.title}")
        print(f"Artist: {info.artist or 'Unknown Artist'}")
        
        lyrics = self.fetch_lyrics(info.title, info.artist)
        
        if lyrics:
            preview = lyrics[:200] + '...' if len(lyrics) > 200 else lyrics
            print(f"\nLyrics preview:\n{preview}\n")
            return self.write_lyrics_to_file(filepath, lyrics)
        else:
            print(f"✗ No lyrics found")
            return False
    
    def process_directory(self, directory: str, extensions: list = None, overwrite: bool = False):
        if extensions is None:
            extensions = ['.mp3', '.m4a', '.mp4', '.flac', '.ogg']
        
        path = Path(directory)
        audio_files = []
        
        for ext in extensions:
            audio_files.extend(path.rglob(f'*{ext}'))
        
        total = len(audio_files)
        success = 0
        skipped = 0
        failed = 0
        
        print(f"Found {total} audio files to process")
        print(f"Extensions: {', '.join(extensions)}")
        print(f"Overwrite existing lyrics: {overwrite}")
        print(f"\n{'='*60}\n")
        
        for i, file in enumerate(audio_files, 1):
            print(f"[{i}/{total}]", end=' ')
            result = self.process_file(str(file), overwrite)
            if result:
                success += 1
            else:
                failed += 1
            time.sleep(1)
        
        print(f"\n{'='*60}")
        print(f"COMPLETED!")
        print(f"{'='*60}")
        print(f"✓ Success: {success}/{total}")
        print(f"✗ Failed: {failed}/{total}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Add lyrics to audio files using web scraping',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s song.mp3                    # Process single file
  %(prog)s /Music                      # Process all audio files in directory
  %(prog)s /Music --overwrite          # Overwrite existing lyrics
  %(prog)s /Music --extensions .mp3    # Process only MP3 files
        """
    )
    parser.add_argument('path', help='File or directory to process')
    parser.add_argument('--overwrite', action='store_true', 
                       help='Overwrite existing lyrics in files')
    parser.add_argument('--extensions', nargs='+', 
                       default=['.mp3', '.m4a', '.mp4', '.flac', '.ogg'],
                       help='File extensions to process (default: .mp3 .m4a .mp4 .flac .ogg)')
    
    args = parser.parse_args()
    
    scraper = LyricsScraper()
    
    path = Path(args.path)
    if path.is_file():
        scraper.process_file(str(path), args.overwrite)
    elif path.is_dir():
        scraper.process_directory(str(path), args.extensions, args.overwrite)
    else:
        print(f"Error: {args.path} is not a valid file or directory")


if __name__ == "__main__":
    main()