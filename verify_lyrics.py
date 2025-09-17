#!/usr/bin/env python3
"""
Comprehensive lyrics verification tool
Checks if lyrics are properly embedded in audio files
"""

import sys
import mutagen
from pathlib import Path
import argparse

def check_file_lyrics(filepath, show_preview=False):
    """Check lyrics in a single audio file"""
    path = Path(filepath)
    if not path.exists():
        print(f"❌ File not found: {filepath}")
        return False
    
    print(f"\n🎵 Checking: {path.name}")
    print("=" * 60)
    
    try:
        audio = mutagen.File(str(path))
        if not audio:
            print("❌ Could not read audio file")
            return False
        
        print(f"📁 Format: {type(audio).__name__}")
        print(f"📊 File size: {path.stat().st_size / 1024 / 1024:.1f} MB")
        
        lyrics_found = False
        total_lyrics_chars = 0
        
        # Check different lyrics field formats
        lyrics_fields = {
            'LYRICS': 'Standard lyrics field',
            'lyrics': 'Lowercase lyrics field', 
            'UNSYNCED LYRICS': 'MP3Tag FLAC format',
            'UNSYNCEDLYRICS': 'Alternative unsynced format',
            '\xa9lyr': 'MP4/iTunes lyrics',
            'WM/Lyrics': 'Windows Media lyrics',
            'Lyrics': 'Generic lyrics field'
        }
        
        print(f"\n🔍 Lyrics Field Check:")
        for field, description in lyrics_fields.items():
            if field in audio:
                content = audio[field]
                if isinstance(content, list):
                    content = content[0] if content else ""
                
                content_str = str(content)
                if content_str.strip():
                    print(f"   ✅ {field}: {len(content_str)} characters ({description})")
                    total_lyrics_chars = max(total_lyrics_chars, len(content_str))
                    lyrics_found = True
                    
                    if show_preview and len(content_str) > 50:
                        # Show first line only (avoid reproducing full lyrics)
                        first_line = content_str.split('\n')[0][:100]
                        print(f"      Preview: {first_line}...")
                else:
                    print(f"   ⚠️  {field}: Empty")
        
        # Check ID3 tags for USLT frames
        if hasattr(audio, 'tags') and audio.tags:
            print(f"\n🏷️  ID3 Tag Check:")
            uslt_found = False
            for frame in audio.tags.values():
                if hasattr(frame, 'FrameID') and frame.FrameID == 'USLT':
                    lyrics_text = str(frame.text) if hasattr(frame, 'text') else str(frame)
                    print(f"   ✅ USLT Frame: {len(lyrics_text)} characters")
                    total_lyrics_chars = max(total_lyrics_chars, len(lyrics_text))
                    lyrics_found = True
                    uslt_found = True
                    
                    if show_preview and len(lyrics_text) > 50:
                        first_line = lyrics_text.split('\n')[0][:100]
                        print(f"      Preview: {first_line}...")
            
            if not uslt_found:
                print(f"   ❌ No USLT frames found")
        
        # Show compatibility info
        print(f"\n🎛️  Player Compatibility:")
        if isinstance(audio, mutagen.mp3.MP3):
            if any(hasattr(frame, 'FrameID') and frame.FrameID == 'USLT' for frame in audio.tags.values() if audio.tags):
                print("   ✅ MP3Tag, Foobar2000, MusicBee")
            else:
                print("   ❌ Missing USLT tag for MP3")
        
        elif isinstance(audio, mutagen.flac.FLAC):
            if 'LYRICS' in audio or 'UNSYNCED LYRICS' in audio:
                print("   ✅ MP3Tag, MusicBee, Foobar2000")
            else:
                print("   ❌ Missing standard FLAC lyrics fields")
        
        elif isinstance(audio, mutagen.mp4.MP4):
            if '\xa9lyr' in audio:
                print("   ✅ iTunes, VLC, most players")
            else:
                print("   ❌ Missing ©lyr field for MP4")
        
        # Final result
        print(f"\n📋 Summary:")
        if lyrics_found:
            print(f"   ✅ LYRICS FOUND: {total_lyrics_chars} characters")
            print(f"   🎯 Status: Properly embedded")
        else:
            print(f"   ❌ NO LYRICS FOUND")
            print(f"   🎯 Status: Needs lyrics")
        
        return lyrics_found
        
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return False

def scan_directory(directory, show_preview=False):
    """Scan all audio files in a directory"""
    path = Path(directory)
    if not path.is_dir():
        print(f"❌ Directory not found: {directory}")
        return
    
    # Common audio extensions
    audio_extensions = {'.mp3', '.m4a', '.mp4', '.flac', '.ogg', '.wav', '.wma', '.aac'}
    
    audio_files = []
    for ext in audio_extensions:
        audio_files.extend(path.rglob(f'*{ext}'))
    
    if not audio_files:
        print(f"❌ No audio files found in: {directory}")
        return
    
    print(f"🎵 Found {len(audio_files)} audio files")
    
    with_lyrics = 0
    without_lyrics = 0
    
    for audio_file in sorted(audio_files):
        has_lyrics = check_file_lyrics(audio_file, show_preview)
        if has_lyrics:
            with_lyrics += 1
        else:
            without_lyrics += 1
    
    print(f"\n📊 FINAL SUMMARY:")
    print(f"=" * 60)
    print(f"✅ Files with lyrics: {with_lyrics}")
    print(f"❌ Files without lyrics: {without_lyrics}")
    print(f"📁 Total files: {len(audio_files)}")

def main():
    parser = argparse.ArgumentParser(
        description='Verify lyrics are properly embedded in audio files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python verify_lyrics.py song.mp3              # Check single file
  python verify_lyrics.py /Music                # Check directory
  python verify_lyrics.py song.flac --preview   # Show lyrics preview
        """
    )
    
    parser.add_argument('path', help='Audio file or directory to check')
    parser.add_argument('--preview', action='store_true', 
                       help='Show preview of lyrics content')
    
    args = parser.parse_args()
    
    path = Path(args.path)
    
    if path.is_file():
        check_file_lyrics(args.path, args.preview)
    elif path.is_dir():
        scan_directory(args.path, args.preview)
    else:
        print(f"❌ Path not found: {args.path}")

if __name__ == "__main__":
    main()