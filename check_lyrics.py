#!/usr/bin/env python3
"""
Quick script to check if lyrics were actually written to audio files
"""

import sys
import mutagen
from pathlib import Path

def check_lyrics_in_file(filepath):
    """Check what lyrics data exists in an audio file"""
    print(f"Checking: {filepath}")
    print("=" * 50)
    
    try:
        audio = mutagen.File(str(filepath))
        if not audio:
            print("❌ Could not read audio file")
            return
        
        print(f"📄 Format: {type(audio).__name__}")
        print(f"📊 File size: {Path(filepath).stat().st_size / 1024 / 1024:.1f} MB")
        
        lyrics_found = False
        
        # Check all possible lyrics fields
        if hasattr(audio, 'tags') and audio.tags:
            print("\n🏷️  ID3 Tags found:")
            for key, value in audio.tags.items():
                if hasattr(value, 'FrameID'):
                    if value.FrameID == 'USLT':
                        print(f"   ✅ USLT (Lyrics): {len(str(value.text))} characters")
                        print(f"      Preview: {str(value.text)[:100]}...")
                        lyrics_found = True
        
        # Check direct key access
        lyrics_keys = ['lyrics', 'LYRICS', '\xa9lyr', 'WM/Lyrics', 'Lyrics']
        print(f"\n📋 Direct field check:")
        for key in lyrics_keys:
            if key in audio:
                value = audio[key]
                if isinstance(value, list):
                    value = value[0] if value else ""
                print(f"   ✅ {key}: {len(str(value))} characters")
                if len(str(value)) > 50:
                    print(f"      Preview: {str(value)[:100]}...")
                lyrics_found = True
        
        # List all available keys
        print(f"\n📚 All available fields:")
        if hasattr(audio, 'keys'):
            for key in sorted(audio.keys()):
                value = audio[key]
                if isinstance(value, list) and value:
                    value = value[0]
                value_str = str(value)[:50] + "..." if len(str(value)) > 50 else str(value)
                print(f"   📝 {key}: {value_str}")
        
        if not lyrics_found:
            print("\n❌ No lyrics found in any standard field")
        else:
            print(f"\n✅ Lyrics data found!")
            
    except Exception as e:
        print(f"❌ Error reading file: {e}")

def main():
    if len(sys.argv) != 2:
        print("Usage: python check_lyrics.py <audio_file>")
        sys.exit(1)
    
    filepath = sys.argv[1]
    if not Path(filepath).exists():
        print(f"❌ File not found: {filepath}")
        sys.exit(1)
    
    check_lyrics_in_file(filepath)

if __name__ == "__main__":
    main()