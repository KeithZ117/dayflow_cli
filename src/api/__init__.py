"""
Gemini API integration module.

This module provides functionality for interacting with Google's Gemini Files API,
including file uploads, metadata retrieval, and video analysis.
"""

from .files import (
    get_client,
    upload_file,
    get_file_metadata,
    list_files,
    wait_until_active,
    analyze_file_resource,
    metadata_pretty,
)

__all__ = [
    "get_client",
    "upload_file",
    "get_file_metadata",
    "list_files",
    "wait_until_active",
    "analyze_file_resource",
    "metadata_pretty",
]
