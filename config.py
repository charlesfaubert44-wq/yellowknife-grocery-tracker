"""
Configuration settings for Yellowknife Grocery Tracker
"""

import os
from datetime import timedelta

class Config:
    """Base configuration class"""
    
    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    FLASK_ENV = os.environ.get('FLASK_ENV', 'development')
    HOST = os.environ.get('HOST', '0.0.0.0')
    PORT = int(os.environ.get('PORT', 5000))
    
    # Database settings
    DATABASE_URL = os.environ.get('DATABASE_URL') or 'sqlite:///grocery_prices.db'
    
    # Scraping settings
    SCRAPING_ENABLED = os.environ.get('SCRAPING_ENABLED', 'True').lower() == 'true'
    SCRAPING_INTERVAL_HOURS = int(os.environ.get('SCRAPING_INTERVAL_HOURS', '6'))
    USE_DEMO_DATA = os.environ.get('USE_DEMO_DATA', 'True').lower() == 'true'
    
    # Rate limiting for scraping
    REQUEST_DELAY_SECONDS = float(os.environ.get('REQUEST_DELAY_SECONDS', '2.0'))
    MAX_RETRIES = int(os.environ.get('MAX_RETRIES', '3'))
    
    # Application settings
    ITEMS_PER_PAGE = int(os.environ.get('ITEMS_PER_PAGE', '25'))
    CACHE_TIMEOUT = int(os.environ.get('CACHE_TIMEOUT', '300'))  # 5 minutes
    
    # Store configurations
    STORES = {
        'independent': {
            'name': 'Independent Grocer',
            'location': '5016 49 St, Yellowknife, NT',
            'website': 'https://www.yourindependentgrocer.ca',
            'phone': '(867) 873-3003',
            'enabled': True
        },
        'extrafoods': {
            'name': 'Extra Foods',
            'location': '201 Range Lake Rd, Yellowknife, NT',
            'website': 'https://www.extrafoods.ca',
            'phone': '(867) 873-4601',
            'enabled': True
        },
        'coop': {
            'name': 'The Co-op',
            'location': '4910 50 St, Yellowknife, NT',
            'website': 'https://www.co-op.coop',
            'phone': '(867) 920-4571',
            'enabled': True
        },
        'saveon': {
            'name': 'Save-On-Foods',
            'location': '5015 50 Ave, Yellowknife, NT',
            'website': 'https://www.saveonfoods.com',
            'phone': '(867) 766-4600',
            'enabled': True
        }
    }

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    USE_DEMO_DATA = True

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    USE_DEMO_DATA = False
    
    def __init__(self):
        if not os.environ.get('SECRET_KEY'):
            raise ValueError("No SECRET_KEY set for production environment")
        self.SECRET_KEY = os.environ.get('SECRET_KEY')

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    USE_DEMO_DATA = True
    DATABASE_URL = 'sqlite:///:memory:'