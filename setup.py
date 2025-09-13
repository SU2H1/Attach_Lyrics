#!/usr/bin/env python3
"""
Lyrics Updater - Setup Script
Automatically adds lyrics to your music files using web scraping
"""

from setuptools import setup, find_packages
import os
import sys

# Read README for long description
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Read requirements
with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="lyrics-updater",
    version="1.0.0",
    author="Music Lover",
    author_email="your.email@example.com",
    description="Automatically add lyrics to your music files using web scraping",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/lyrics-updater",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Multimedia :: Sound/Audio",
        "Topic :: Internet :: WWW/HTTP :: Indexing/Search",
    ],
    python_requires=">=3.7",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=6.0",
            "black>=21.0",
            "flake8>=3.9",
        ],
    },
    entry_points={
        "console_scripts": [
            "lyrics-updater=gui_app:main",
            "lyrics-cli=lyrics_scraper:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.md", "*.txt", "*.json", "*.js"],
    },
    data_files=[
        ("", ["package.json", "scraper.js", "CLAUDE.md"]),
    ],
    zip_safe=False,
)