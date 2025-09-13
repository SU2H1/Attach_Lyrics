#!/usr/bin/env python3
"""
Lyrics Updater - Automatic Installation Script
This script automatically installs all dependencies and sets up the application
"""

import subprocess
import sys
import os
import platform
from pathlib import Path

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"📦 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error during {description}:")
        print(f"   Command: {command}")
        print(f"   Error: {e.stderr}")
        return False

def check_python_version():
    """Check if Python version is compatible"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 7):
        print("❌ Python 3.7 or higher is required")
        print(f"   Current version: {version.major}.{version.minor}.{version.micro}")
        return False
    print(f"✅ Python version {version.major}.{version.minor}.{version.micro} is compatible")
    return True

def check_node_version():
    """Check if Node.js is installed"""
    try:
        result = subprocess.run("node --version", shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            version = result.stdout.strip()
            print(f"✅ Node.js {version} is installed")
            return True
    except:
        pass
    
    print("❌ Node.js is not installed or not in PATH")
    print("   Please install Node.js from: https://nodejs.org/")
    return False

def install_python_dependencies():
    """Install Python dependencies"""
    commands = [
        ("python -m pip install --upgrade pip", "Upgrading pip"),
        ("pip install -r requirements.txt", "Installing Python dependencies"),
    ]
    
    for command, description in commands:
        if not run_command(command, description):
            return False
    return True

def install_node_dependencies():
    """Install Node.js dependencies"""
    return run_command("npm install", "Installing Node.js dependencies")

def create_desktop_shortcut():
    """Create desktop shortcut (Windows only)"""
    if platform.system() != "Windows":
        return True
    
    try:
        import winshell
        from win32com.client import Dispatch
        
        desktop = winshell.desktop()
        script_path = Path(__file__).parent / "gui_app.py"
        
        shell = Dispatch('WScript.Shell')
        shortcut = shell.CreateShortCut(os.path.join(desktop, "Lyrics Updater.lnk"))
        shortcut.Targetpath = sys.executable
        shortcut.Arguments = f'"{script_path}"'
        shortcut.WorkingDirectory = str(Path(__file__).parent)
        shortcut.IconLocation = sys.executable
        shortcut.save()
        
        print("✅ Desktop shortcut created")
        return True
    except ImportError:
        print("⚠️  Could not create desktop shortcut (missing winshell/pywin32)")
        return True
    except Exception as e:
        print(f"⚠️  Could not create desktop shortcut: {e}")
        return True

def main():
    """Main installation process"""
    print("🎵 Lyrics Updater - Installation Script")
    print("=" * 50)
    
    # Check system requirements
    if not check_python_version():
        sys.exit(1)
    
    if not check_node_version():
        print("\n📝 Installation Steps:")
        print("1. Install Node.js from https://nodejs.org/")
        print("2. Restart your terminal/command prompt")
        print("3. Run this script again")
        sys.exit(1)
    
    print("\n🔧 Installing dependencies...")
    
    # Install Python dependencies
    if not install_python_dependencies():
        print("❌ Failed to install Python dependencies")
        sys.exit(1)
    
    # Install Node.js dependencies
    if not install_node_dependencies():
        print("❌ Failed to install Node.js dependencies")
        sys.exit(1)
    
    # Create desktop shortcut (Windows only)
    create_desktop_shortcut()
    
    print("\n🎉 Installation completed successfully!")
    print("=" * 50)
    print("🚀 To start the application:")
    print("   • Run: python gui_app.py")
    print("   • Or double-click the desktop shortcut (Windows)")
    print("\n📚 For more information, see README.md")

if __name__ == "__main__":
    main()