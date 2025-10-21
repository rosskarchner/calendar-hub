import json
import os

def load_newsletter_config():
    """Load newsletter configuration from JSON file"""
    config_path = os.path.join(os.path.dirname(__file__), 'chalicelib', 'newsletters.json')
    with open(config_path, 'r') as f:
        return json.load(f)

def get_newsletter_by_slug(slug):
    """Get newsletter configuration by slug"""
    config = load_newsletter_config()
    return config.get(slug)

def get_all_newsletters():
    """Get all newsletter configurations"""
    return load_newsletter_config()

def validate_newsletter_slug(slug):
    """Check if a newsletter slug exists"""
    config = load_newsletter_config()
    return slug in config