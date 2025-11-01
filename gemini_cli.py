#!/usr/bin/env python3
"""
Gemini Files API CLI - Command-line interface for managing files with Gemini API.

Usage:
    python gemini_cli.py upload --file video.mp4 --display-name "My Video"
    python gemini_cli.py list
    python gemini_cli.py get --name files/abc123
    python gemini_cli.py analyze --name files/abc123 --prompt "分析这个视频"
"""

from src.api.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
