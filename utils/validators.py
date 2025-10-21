"""Validation utilities."""
import re


def sanitize_filename(name: str) -> str:
    """Sanitize a string to be safe for use in filenames, preventing subdirectories."""
    # Replace slashes and other problematic characters with dashes
    sanitized = re.sub(r'[/\\<>:"|?*]', '-', name)
    # Replace spaces with dashes
    sanitized = sanitized.replace(' ', '-')
    # Remove multiple consecutive dashes
    sanitized = re.sub(r'-+', '-', sanitized)
    # Remove leading/trailing dashes
    sanitized = sanitized.strip('-')
    # Ensure it's not empty
    if not sanitized:
        sanitized = 'untitled'
    return sanitized.lower()
