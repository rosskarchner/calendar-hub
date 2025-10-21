"""Configuration management for Calendar Hub."""
import os
import json
from typing import Dict, List, Optional


class Config:
    """Base configuration."""
    
    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    # AWS settings
    DYNAMODB_TABLE = os.environ.get('SUBMISSIONS_TABLE', 'DCTechEventsSubmissions')
    SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'outgoing@dctech.events')
    
    # Secrets Manager
    CSRF_SECRET_NAME = os.environ.get('CSRF_SECRET_NAME', 'dctech-events/csrf-secret')
    GITHUB_TOKEN_SECRET_NAME = os.environ.get('GITHUB_TOKEN_SECRET_NAME', 'dctech-events/github-token')
    NEWSLETTER_CSRF_SECRET_NAME = os.environ.get('NEWSLETTER_CSRF_SECRET_NAME', 'newsletter/csrf_secret')
    
    # KMS settings
    CONFIRMATION_KEY_ID = os.environ.get('CONFIRMATION_KEY_ID')
    
    # Domain settings
    DOMAIN_NAME = os.environ.get('DOMAIN_NAME', 'localhost:5000')
    
    # Sites configuration
    SITES_CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'sites.json')
    
    @classmethod
    def load_sites(cls) -> List[Dict]:
        """Load sites configuration from JSON file."""
        with open(cls.SITES_CONFIG_PATH) as f:
            return json.load(f)['sites']
    
    @classmethod
    def get_site_by_slug(cls, slug: str) -> Optional[Dict]:
        """Get site configuration by slug."""
        sites = cls.load_sites()
        for site in sites:
            if site['slug'] == slug:
                return site
        return None


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False


# Config dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
