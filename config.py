"""Configuration management for Calendar Hub."""
import os
import json
from typing import Dict, List, Optional


class Config:
    """Base configuration."""

    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'

    # Database settings
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'postgresql://calendar_user:calendar_pass@localhost:5432/calendar_hub'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }

    # GitHub OAuth settings
    GITHUB_CLIENT_ID = os.environ.get('GITHUB_CLIENT_ID')
    GITHUB_CLIENT_SECRET = os.environ.get('GITHUB_CLIENT_SECRET')

    # AWS settings (for newsletter functionality)
    SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'outgoing@dctech.events')
    CONFIRMATION_KEY_ID = os.environ.get('CONFIRMATION_KEY_ID')  # AWS KMS key for newsletter confirmations
    AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')

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
