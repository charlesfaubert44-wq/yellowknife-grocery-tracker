"""
Scraper Manager for Yellowknife Grocery Tracker
Handles web scraping operations for different grocery stores
"""

import sqlite3
import logging
from datetime import datetime
from typing import List, Dict, Optional
import random
import time

logger = logging.getLogger(__name__)

class ScraperManager:
    """Manages web scraping operations for grocery stores"""
    
    def __init__(self, database_path: str, use_demo: bool = False):
        """
        Initialize the scraper manager
        
        Args:
            database_path: Path to the SQLite database
            use_demo: Whether to use demo data instead of actual scraping
        """
        self.database_path = database_path
        self.use_demo = use_demo
        self.logger = logging.getLogger(__name__)
        
        # Store configurations - empty initially, can be added dynamically
        self.store_configs = {}
    
    def get_db_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.database_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def initialize_database(self):
        """Initialize database tables if they don't exist"""
        conn = self.get_db_connection()
        try:
            cursor = conn.cursor()
            
            # Create tables if they don't exist
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS stores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    location TEXT,
                    website_url TEXT,
                    scraping_enabled BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    category_id INTEGER,
                    unit TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (category_id) REFERENCES categories (id)
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS prices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_id INTEGER NOT NULL,
                    store_id INTEGER NOT NULL,
                    price REAL NOT NULL,
                    date DATE NOT NULL,
                    notes TEXT,
                    source TEXT DEFAULT 'scraper',
                    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (item_id) REFERENCES items (id),
                    FOREIGN KEY (store_id) REFERENCES stores (id)
                )
            ''')
            
            conn.commit()
            self.logger.info("Database tables initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Error initializing database: {str(e)}")
            raise
        finally:
            conn.close()
    
    def add_store_config(self, store_id: str, name: str, base_url: str = None, location: str = None):
        """
        Add a new store configuration
        
        Args:
            store_id: Unique identifier for the store
            name: Display name of the store
            base_url: Base URL for scraping (optional)
            location: Store location (optional)
        """
        self.store_configs[store_id] = {
            'name': name,
            'base_url': base_url or '',
            'location': location or '',
            'selectors': {
                'price': '.price',
                'name': '.product-name', 
                'category': '.category'
            }
        }
        
        # Add to database
        conn = self.get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO stores (name, location, website_url, scraping_enabled) 
                VALUES (?, ?, ?, 1)
            ''', (name, location or '', base_url or ''))
            conn.commit()
            self.logger.info(f"Added store configuration: {name}")
        except Exception as e:
            self.logger.error(f"Error adding store to database: {str(e)}")
        finally:
            conn.close()
    
    def scrape_store_prices(self, store_id: str) -> List[Dict]:
        """
        Scrape prices from a specific store
        
        Args:
            store_id: Identifier for the store to scrape
            
        Returns:
            List of scraped product data
        """
        if self.use_demo:
            return self._generate_demo_data(store_id)
        
        # In a real implementation, this would perform actual web scraping
        self.logger.info(f"Starting price scrape for store: {store_id}")
        
        try:
            # Placeholder for actual scraping logic
            # This would use libraries like requests, BeautifulSoup, or Selenium
            scraped_data = self._scrape_store_real(store_id)
            
            self.logger.info(f"Successfully scraped {len(scraped_data)} items from {store_id}")
            return scraped_data
            
        except Exception as e:
            self.logger.error(f"Error scraping store {store_id}: {str(e)}")
            return []
    
    def _scrape_store_real(self, store_id: str) -> List[Dict]:
        """
        Perform actual web scraping (placeholder implementation)
        
        In a real implementation, this would:
        1. Use requests to fetch web pages
        2. Parse HTML with BeautifulSoup
        3. Extract product information using CSS selectors
        4. Handle pagination and rate limiting
        """
        # This is a placeholder - real implementation would go here
        return self._generate_demo_data(store_id)
    
    def _generate_demo_data(self, store_id: str) -> List[Dict]:
        """
        Generate demo data for testing purposes
        
        Args:
            store_id: Store identifier
            
        Returns:
            List of demo product data
        """
        demo_products = [
            {
                'name': 'Bananas',
                'category': 'Produce',
                'unit': 'per lb',
                'price': round(random.uniform(1.19, 1.49), 2),
                'brand': None,
                'size': '1 lb'
            },
            {
                'name': 'Milk 2%',
                'category': 'Dairy',
                'unit': 'each',
                'price': round(random.uniform(5.49, 5.99), 2),
                'brand': 'Dairyland',
                'size': '4L'
            },
            {
                'name': 'White Bread',
                'category': 'Bakery',
                'unit': 'each',
                'price': round(random.uniform(2.79, 3.19), 2),
                'brand': 'Wonder',
                'size': '675g'
            },
            {
                'name': 'Ground Beef',
                'category': 'Meat',
                'unit': 'per lb',
                'price': round(random.uniform(8.99, 12.49), 2),
                'brand': None,
                'size': '1 lb'
            },
            {
                'name': 'Cheddar Cheese',
                'category': 'Dairy',
                'unit': 'each',
                'price': round(random.uniform(6.99, 8.49), 2),
                'brand': 'Black Diamond',
                'size': '400g'
            }
        ]
        
        # Add store-specific price variations
        store_multipliers = {
            'independent': 1.0,
            'extrafoods': 1.05,
            'coop': 0.95,
            'saveon': 1.08
        }
        
        multiplier = store_multipliers.get(store_id, 1.0)
        
        for product in demo_products:
            product['price'] = round(product['price'] * multiplier, 2)
            product['store_id'] = store_id
            product['scraped_at'] = datetime.now().isoformat()
        
        return demo_products
    
    def update_all_stores(self) -> Dict[str, int]:
        """
        Update prices for all configured stores
        
        Returns:
            Dictionary with store_id as key and number of updated items as value
        """
        results = {}
        
        if not self.store_configs:
            self.logger.warning("No stores configured for scraping")
            return results
        
        for store_id in self.store_configs.keys():
            try:
                scraped_data = self.scrape_store_prices(store_id)
                updated_count = self._save_scraped_data(store_id, scraped_data)
                results[store_id] = updated_count
                
                # Add delay between stores to be respectful
                if not self.use_demo:
                    time.sleep(2)
                    
            except Exception as e:
                self.logger.error(f"Failed to update store {store_id}: {str(e)}")
                results[store_id] = 0
        
        return results
    
    def _save_scraped_data(self, store_id: str, scraped_data: List[Dict]) -> int:
        """
        Save scraped data to the database
        
        Args:
            store_id: Store identifier
            scraped_data: List of scraped product data
            
        Returns:
            Number of items saved
        """
        if not scraped_data:
            return 0
        
        conn = self.get_db_connection()
        try:
            cursor = conn.cursor()
            saved_count = 0
            
            # Ensure store exists in database
            store_name = self.store_configs[store_id]['name']
            cursor.execute('SELECT id FROM stores WHERE name = ?', (store_name,))
            store_result = cursor.fetchone()
            if not store_result:
                # Store doesn't exist, create it
                cursor.execute('''
                    INSERT INTO stores (name, location, website_url, scraping_enabled) 
                    VALUES (?, ?, ?, 1)
                ''', (
                    store_name,
                    self.store_configs[store_id].get('location', ''),
                    self.store_configs[store_id].get('base_url', '')
                ))
                store_db_id = cursor.lastrowid
                self.logger.info(f"Created new store in database: {store_name}")
            else:
                store_db_id = store_result[0]
            
            for item in scraped_data:
                
                # Get or create the category
                cursor.execute('SELECT id FROM categories WHERE name = ?', (item['category'],))
                category_result = cursor.fetchone()
                if not category_result:
                    cursor.execute('INSERT INTO categories (name) VALUES (?)', (item['category'],))
                    category_id = cursor.lastrowid
                else:
                    category_id = category_result[0]
                
                # Get or create the item
                cursor.execute('SELECT id FROM items WHERE name = ? AND category_id = ?', 
                             (item['name'], category_id))
                item_result = cursor.fetchone()
                if not item_result:
                    cursor.execute('INSERT INTO items (name, category_id, unit) VALUES (?, ?, ?)',
                                 (item['name'], category_id, item['unit']))
                    item_id = cursor.lastrowid
                else:
                    item_id = item_result[0]
                
                # Insert the price
                cursor.execute('''
                    INSERT INTO prices (item_id, store_id, price, date, notes, source)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    item_id,
                    store_db_id,
                    item['price'],
                    datetime.now().strftime('%Y-%m-%d'),
                    f"Brand: {item.get('brand', 'N/A')}, Size: {item.get('size', 'N/A')}",
                    'scraper'
                ))
                saved_count += 1
            
            conn.commit()
            self.logger.info(f"Saved {saved_count} items for store {store_id}")
            return saved_count
            
        except Exception as e:
            self.logger.error(f"Error saving data for store {store_id}: {str(e)}")
            conn.rollback()
            return 0
        finally:
            conn.close()
    
    def get_store_status(self, store_id: str) -> Dict:
        """
        Get status information for a specific store
        
        Args:
            store_id: Store identifier
            
        Returns:
            Dictionary with store status information
        """
        conn = self.get_db_connection()
        try:
            cursor = conn.cursor()
            
            # Get latest scrape time and item count
            cursor.execute('''
                SELECT 
                    COUNT(*) as item_count,
                    MAX(scraped_at) as last_scrape
                FROM prices 
                WHERE store_id = ?
            ''', (store_id,))
            
            result = cursor.fetchone()
            
            return {
                'store_id': store_id,
                'name': self.store_configs.get(store_id, {}).get('name', store_id),
                'item_count': result['item_count'] if result else 0,
                'last_scrape': result['last_scrape'] if result else None,
                'status': 'active' if result and result['item_count'] > 0 else 'inactive'
            }
            
        except Exception as e:
            self.logger.error(f"Error getting status for store {store_id}: {str(e)}")
            return {
                'store_id': store_id,
                'name': store_id,
                'item_count': 0,
                'last_scrape': None,
                'status': 'error'
            }
        finally:
            conn.close()
    
    def test_store_connection(self, store_id: str) -> bool:
        """
        Test connection to a store's website
        
        Args:
            store_id: Store identifier
            
        Returns:
            True if connection successful, False otherwise
        """
        if self.use_demo:
            # Simulate random success/failure for demo
            return random.random() > 0.2  # 80% success rate
        
        try:
            # In real implementation, this would test HTTP connection
            # For now, return True as placeholder
            self.logger.info(f"Testing connection to store: {store_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Connection test failed for store {store_id}: {str(e)}")
            return False
    
    def scrape_all_stores(self, save_to_db: bool = False) -> Dict[str, Dict]:
        """
        Scrape all stores and optionally save to database
        
        Args:
            save_to_db: Whether to save results to database
            
        Returns:
            Dictionary with results for each store
        """
        results = {}
        
        for store_id in self.store_configs.keys():
            try:
                scraped_data = self.scrape_store_prices(store_id)
                
                result = {
                    'success': True,
                    'products_count': len(scraped_data),
                    'saved_count': 0
                }
                
                if save_to_db:
                    result['saved_count'] = self._save_scraped_data(store_id, scraped_data)
                
                results[store_id] = result
                
            except Exception as e:
                self.logger.error(f"Error scraping store {store_id}: {str(e)}")
                results[store_id] = {
                    'success': False,
                    'error': str(e),
                    'products_count': 0,
                    'saved_count': 0
                }
        
        return results
    
    def scrape_store(self, store_id: str, save_to_db: bool = False) -> Dict:
        """
        Scrape a single store
        
        Args:
            store_id: Store identifier
            save_to_db: Whether to save results to database
            
        Returns:
            Dictionary with scraping results
        """
        try:
            scraped_data = self.scrape_store_prices(store_id)
            
            result = {
                'success': True,
                'store_id': store_id,
                'products_count': len(scraped_data),
                'saved_count': 0
            }
            
            if save_to_db:
                result['saved_count'] = self._save_scraped_data(store_id, scraped_data)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error scraping store {store_id}: {str(e)}")
            return {
                'success': False,
                'store_id': store_id,
                'error': str(e),
                'products_count': 0,
                'saved_count': 0
            }
    
    def get_last_scrape_time(self) -> Optional[str]:
        """
        Get the timestamp of the last scrape operation
        
        Returns:
            ISO timestamp string of last scrape, or None if never scraped
        """
        conn = self.get_db_connection()
        try:
            cursor = conn.cursor()
            
            # Get the most recent scrape time from any store
            cursor.execute('''
                SELECT MAX(scraped_at) as last_scrape
                FROM prices
                WHERE source = 'scraper'
            ''')
            
            result = cursor.fetchone()
            return result['last_scrape'] if result and result['last_scrape'] else None
            
        except Exception as e:
            self.logger.error(f"Error getting last scrape time: {str(e)}")
            return None
        finally:
            conn.close()
    
    def add_test_stores(self):
        """Add test stores for demonstration and testing"""
        test_stores = [
            {
                'id': 'test_independent',
                'name': 'Test Independent Grocer',
                'location': 'Yellowknife, NT',
                'url': 'https://example.com/independent'
            },
            {
                'id': 'test_extrafoods', 
                'name': 'Test Extra Foods',
                'location': 'Yellowknife, NT',
                'url': 'https://example.com/extrafoods'
            },
            {
                'id': 'test_coop',
                'name': 'Test Co-op',
                'location': 'Yellowknife, NT', 
                'url': 'https://example.com/coop'
            }
        ]
        
        for store in test_stores:
            self.add_store_config(
                store['id'], 
                store['name'], 
                store['url'], 
                store['location']
            )
        
        self.logger.info(f"Added {len(test_stores)} test stores")
        return len(test_stores)
    
    def get_all_stores(self):
        """Get all stores from database"""
        conn = self.get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM stores ORDER BY name')
            stores = cursor.fetchall()
            return [dict(store) for store in stores]
        except Exception as e:
            self.logger.error(f"Error fetching stores: {str(e)}")
            return []
        finally:
            conn.close()
    
    def test_system(self):
        """Test the complete scraping system"""
        test_results = {
            'database_init': False,
            'stores_added': 0,
            'scraping_test': {},
            'data_saved': 0,
            'errors': []
        }
        
        try:
            # Test 1: Initialize database
            self.initialize_database()
            test_results['database_init'] = True
            self.logger.info("✅ Database initialization successful")
            
            # Test 2: Add test stores
            test_results['stores_added'] = self.add_test_stores()
            self.logger.info(f"✅ Added {test_results['stores_added']} test stores")
            
            # Test 3: Test scraping
            scraping_results = self.scrape_all_stores(save_to_db=True)
            test_results['scraping_test'] = scraping_results
            
            # Calculate total data saved
            total_saved = sum(r.get('saved_count', 0) for r in scraping_results.values())
            test_results['data_saved'] = total_saved
            
            self.logger.info(f"✅ Scraping test complete. Saved {total_saved} price records")
            
            # Test 4: Verify data in database
            stores = self.get_all_stores()
            if stores:
                self.logger.info(f"✅ Database contains {len(stores)} stores")
            else:
                test_results['errors'].append("No stores found in database")
                
        except Exception as e:
            error_msg = f"System test failed: {str(e)}"
            test_results['errors'].append(error_msg)
            self.logger.error(error_msg)
        
        return test_results