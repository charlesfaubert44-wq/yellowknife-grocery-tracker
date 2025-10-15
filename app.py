from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_cors import CORS
from datetime import datetime, timedelta
import sqlite3
import json
import os
from pathlib import Path
from apscheduler.schedulers.background import BackgroundScheduler
from scrapers.scraper_manager import ScraperManager
from config import Config, get_config
import logging
from contextlib import contextmanager
from functools import wraps
import re

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
config = get_config()
app.config.from_object(config)

# Enable CORS for API endpoints
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Database setup
DATABASE = getattr(config, 'DATABASE_PATH', 'grocery_prices.db')

# Initialize scraper manager
scraper_manager = ScraperManager(DATABASE, use_demo=getattr(config, 'USE_DEMO_DATA', True))

# Initialize scheduler for automatic price updates
scheduler = BackgroundScheduler()
scheduler.start()

@contextmanager
def get_db():
    """Get database connection with automatic cleanup"""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE, timeout=10.0)
        conn.row_factory = sqlite3.Row
        # Enable foreign key constraints
        conn.execute('PRAGMA foreign_keys = ON')
        yield conn
    except sqlite3.Error as e:
        logger.error(f"Database error: {str(e)}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

def validate_input(data, required_fields, field_types=None):
    """Validate input data against required fields and types"""
    if not data:
        return False, "No data provided"

    # Check required fields
    for field in required_fields:
        if field not in data or data[field] is None or str(data[field]).strip() == '':
            return False, f"Missing required field: {field}"

    # Check field types if provided
    if field_types:
        for field, expected_type in field_types.items():
            if field in data and data[field] is not None:
                if expected_type == 'string' and not isinstance(data[field], str):
                    return False, f"Field {field} must be a string"
                elif expected_type == 'number':
                    try:
                        float(data[field])
                    except (ValueError, TypeError):
                        return False, f"Field {field} must be a number"
                elif expected_type == 'boolean' and not isinstance(data[field], bool):
                    return False, f"Field {field} must be a boolean"

    return True, None

def sanitize_string(value, max_length=255):
    """Sanitize string input to prevent XSS and injection attacks"""
    if not isinstance(value, str):
        value = str(value)

    # Remove potentially harmful characters
    value = re.sub(r'[<>"\']', '', value)

    # Limit length
    value = value[:max_length].strip()

    return value

def init_db():
    """Initialize the database with tables"""
    with app.app_context():
        with get_db() as db:
        db.execute('''
            CREATE TABLE IF NOT EXISTS stores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                location TEXT,
                website_url TEXT,
                scraping_enabled BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        db.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        db.execute('''
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category_id INTEGER,
                unit TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES categories (id)
            )
        ''')
        db.execute('''
            CREATE TABLE IF NOT EXISTS prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id INTEGER NOT NULL,
                store_id INTEGER NOT NULL,
                price REAL NOT NULL,
                date DATE NOT NULL,
                notes TEXT,
                source TEXT DEFAULT 'manual',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (item_id) REFERENCES items (id),
                FOREIGN KEY (store_id) REFERENCES stores (id)
            )
        ''')
        
        # Note: Stores will be dynamically added when they are scraped or manually added
        # No pre-filled stores to test the system's ability to work with empty data
        
        # Add default categories
        categories = ['Produce', 'Dairy', 'Meat', 'Bakery', 'Pantry', 'Frozen', 'Beverages', 'Snacks']
        for category in categories:
            try:
                db.execute('INSERT INTO categories (name) VALUES (?)', (category,))
            except sqlite3.IntegrityError:
                pass  # Category already exists
        
        db.commit()
        
        # Add some sample items for testing if using demo mode
        if getattr(config, 'USE_DEMO_DATA', True):
            sample_items = [
                ('Bananas', 1, 'per lb'),  # Produce
                ('Milk 2%', 2, '4L'),      # Dairy  
                ('Ground Beef', 3, 'per lb'), # Meat
                ('White Bread', 4, 'loaf'), # Bakery
                ('Frozen Pizza', 6, 'each'), # Frozen
                ('Orange Juice', 7, '1L'),  # Beverages
            ]
            
            for item_name, category_id, unit in sample_items:
                try:
                    db.execute('INSERT INTO items (name, category_id, unit) VALUES (?, ?, ?)',
                             (item_name, category_id, unit))
                except sqlite3.IntegrityError:
                    pass  # Item already exists
            
            db.commit()
        
        logger.info("Database initialized successfully")

def scheduled_scrape():
    """Scheduled task to scrape all stores"""
    if not getattr(config, 'SCRAPING_ENABLED', True):
        logger.info("Scraping is disabled in configuration")
        return
    
    logger.info("Starting scheduled scrape...")
    try:
        results = scraper_manager.scrape_all_stores(save_to_db=True)
        total = sum(r.get('saved_count', 0) for r in results.values())
        logger.info(f"Scheduled scrape complete. Saved {total} prices.")
    except Exception as e:
        logger.error(f"Error in scheduled scrape: {str(e)}")

@app.route('/')
def index():
    """Main dashboard with real data"""
    try:
        with get_db() as db:
            # Get summary statistics
            stats = {
                'total_items': db.execute('SELECT COUNT(*) as count FROM items').fetchone()['count'],
                'active_stores': db.execute('SELECT COUNT(*) as count FROM stores WHERE scraping_enabled = 1').fetchone()['count'],
                'total_prices': db.execute('SELECT COUNT(*) as count FROM prices WHERE date = DATE("now")').fetchone()['count'],
                'last_update': db.execute('SELECT MAX(created_at) as last_update FROM prices').fetchone()['last_update']
            }

            # Get recent price comparisons
            recent_prices = db.execute('''
                SELECT i.name, i.id, c.name as category,
                       GROUP_CONCAT(s.name || ':' || p.price) as store_prices
                FROM items i
                LEFT JOIN categories c ON i.category_id = c.id
                LEFT JOIN prices p ON i.id = p.item_id AND p.date = DATE("now")
                LEFT JOIN stores s ON p.store_id = s.id
                GROUP BY i.id, i.name, c.name
                LIMIT 10
            ''').fetchall()

            return render_template('index.html', stats=stats, recent_prices=recent_prices)
    except Exception as e:
        logger.error(f"Error loading dashboard: {str(e)}")
        return render_template('error.html', error="Failed to load dashboard data"), 500

@app.route('/price-trends')
def price_trends():
    """Price trends page with trend data"""
    db = get_db()
    
    # Get trending items
    trending_items = db.execute('''
        SELECT i.name, i.id, 
               AVG(p.price) as avg_price,
               COUNT(p.id) as price_count,
               c.name as category
        FROM items i
        JOIN prices p ON i.id = p.item_id
        LEFT JOIN categories c ON i.category_id = c.id
        WHERE p.date >= DATE('now', '-30 days')
        GROUP BY i.id, i.name, c.name
        HAVING price_count > 5
        ORDER BY price_count DESC
        LIMIT 20
    ''').fetchall()
    
    return render_template('price_trends.html', trending_items=trending_items)

@app.route('/stores')
def stores():
    """Store management page with store data"""
    db = get_db()
    
    # Get all stores with statistics
    stores_data = db.execute('''
        SELECT s.*, 
               COUNT(p.id) as total_prices,
               COUNT(CASE WHEN p.date = DATE('now') THEN 1 END) as today_prices,
               MAX(p.created_at) as last_update
        FROM stores s
        LEFT JOIN prices p ON s.id = p.store_id
        GROUP BY s.id, s.name
        ORDER BY s.name
    ''').fetchall()
    
    return render_template('stores.html', stores=stores_data)

@app.route('/items')
def items():
    """Items management page with item data"""
    db = get_db()
    
    # Get items with category and recent prices
    items_data = db.execute('''
        SELECT i.*, c.name as category_name,
               COUNT(p.id) as price_count,
               MIN(p.price) as min_price,
               MAX(p.price) as max_price,
               AVG(p.price) as avg_price,
               MAX(p.created_at) as last_price_update
        FROM items i
        LEFT JOIN categories c ON i.category_id = c.id
        LEFT JOIN prices p ON i.id = p.item_id
        GROUP BY i.id, i.name, c.name
        ORDER BY i.name
    ''').fetchall()
    
    # Get category statistics
    category_stats = db.execute('''
        SELECT c.name, COUNT(i.id) as item_count
        FROM categories c
        LEFT JOIN items i ON c.id = i.category_id
        GROUP BY c.id, c.name
        ORDER BY item_count DESC
    ''').fetchall()
    
    return render_template('items.html', items=items_data, categories=category_stats)

@app.route('/api/stores', methods=['GET', 'POST'])
def api_stores():
    """Get all stores or add a new one"""
    try:
        with get_db() as db:
            if request.method == 'POST':
                data = request.json

                # Validate input
                is_valid, error_msg = validate_input(
                    data,
                    required_fields=['name'],
                    field_types={'name': 'string', 'location': 'string', 'website_url': 'string'}
                )
                if not is_valid:
                    return jsonify({'success': False, 'error': error_msg}), 400

                # Sanitize inputs
                name = sanitize_string(data['name'], max_length=100)
                location = sanitize_string(data.get('location', ''), max_length=200)
                website_url = sanitize_string(data.get('website_url', ''), max_length=500)
                scraping_enabled = int(data.get('scraping_enabled', 0))

                try:
                    db.execute(
                        'INSERT INTO stores (name, location, website_url, scraping_enabled) VALUES (?, ?, ?, ?)',
                        (name, location, website_url, scraping_enabled)
                    )
                    db.commit()
                    return jsonify({'success': True, 'message': 'Store added successfully'})
                except sqlite3.IntegrityError:
                    return jsonify({'success': False, 'error': 'Store already exists'}), 400

            # GET request
            stores_data = db.execute('SELECT * FROM stores ORDER BY name').fetchall()
            return jsonify([dict(store) for store in stores_data])
    except Exception as e:
        logger.error(f"Error in api_stores: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@app.route('/api/categories', methods=['GET', 'POST'])
def api_categories():
    """Get all categories or add a new one"""
    db = get_db()
    
    if request.method == 'POST':
        data = request.json
        try:
            db.execute('INSERT INTO categories (name) VALUES (?)', (data['name'],))
            db.commit()
            return jsonify({'success': True})
        except sqlite3.IntegrityError:
            return jsonify({'success': False, 'error': 'Category already exists'}), 400
    
    categories_data = db.execute('SELECT * FROM categories ORDER BY name').fetchall()
    return jsonify([dict(category) for category in categories_data])

@app.route('/api/items', methods=['GET', 'POST'])
def api_items():
    """Get all items or add a new one"""
    try:
        with get_db() as db:
            if request.method == 'POST':
                data = request.json

                # Validate input
                is_valid, error_msg = validate_input(
                    data,
                    required_fields=['name', 'category_id'],
                    field_types={'name': 'string', 'category_id': 'number', 'unit': 'string'}
                )
                if not is_valid:
                    return jsonify({'success': False, 'error': error_msg}), 400

                # Sanitize inputs
                name = sanitize_string(data['name'], max_length=100)
                category_id = int(data['category_id'])
                unit = sanitize_string(data.get('unit', 'each'), max_length=50)

                # Verify category exists
                category = db.execute('SELECT id FROM categories WHERE id = ?', (category_id,)).fetchone()
                if not category:
                    return jsonify({'success': False, 'error': 'Invalid category_id'}), 400

                db.execute('INSERT INTO items (name, category_id, unit) VALUES (?, ?, ?)',
                          (name, category_id, unit))
                db.commit()
                return jsonify({'success': True, 'message': 'Item added successfully'})

            # GET request
            items_data = db.execute('''
                SELECT items.*, categories.name as category_name
                FROM items
                LEFT JOIN categories ON items.category_id = categories.id
                ORDER BY items.name
            ''').fetchall()
            return jsonify([dict(item) for item in items_data])
    except Exception as e:
        logger.error(f"Error in api_items: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@app.route('/api/prices', methods=['GET', 'POST'])
def api_prices():
    """Get all prices or add a new price entry"""
    try:
        with get_db() as db:
            if request.method == 'POST':
                data = request.json

                # Validate input
                is_valid, error_msg = validate_input(
                    data,
                    required_fields=['item_id', 'store_id', 'price'],
                    field_types={'item_id': 'number', 'store_id': 'number', 'price': 'number'}
                )
                if not is_valid:
                    return jsonify({'success': False, 'error': error_msg}), 400

                # Sanitize and validate inputs
                item_id = int(data['item_id'])
                store_id = int(data['store_id'])
                price = float(data['price'])

                if price < 0:
                    return jsonify({'success': False, 'error': 'Price cannot be negative'}), 400

                date_str = data.get('date', datetime.now().strftime('%Y-%m-%d'))
                notes = sanitize_string(data.get('notes', ''), max_length=500)
                source = sanitize_string(data.get('source', 'manual'), max_length=50)

                # Verify item and store exist
                item = db.execute('SELECT id FROM items WHERE id = ?', (item_id,)).fetchone()
                store = db.execute('SELECT id FROM stores WHERE id = ?', (store_id,)).fetchone()

                if not item:
                    return jsonify({'success': False, 'error': 'Invalid item_id'}), 400
                if not store:
                    return jsonify({'success': False, 'error': 'Invalid store_id'}), 400

                db.execute('''
                    INSERT INTO prices (item_id, store_id, price, date, notes, source)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (item_id, store_id, price, date_str, notes, source))
                db.commit()
                return jsonify({'success': True, 'message': 'Price added successfully'})
    
    # Get query parameters for filtering
    days = request.args.get('days', 30, type=int)
    item_id = request.args.get('item_id', type=int)
    
    query = '''
        SELECT prices.*, items.name as item_name, items.unit,
               stores.name as store_name, categories.name as category_name
        FROM prices
        JOIN items ON prices.item_id = items.id
        JOIN stores ON prices.store_id = stores.id
        LEFT JOIN categories ON items.category_id = categories.id
        WHERE date >= date('now', '-' || ? || ' days')
    '''
    params = [days]
    
    if item_id:
        query += ' AND prices.item_id = ?'
        params.append(item_id)
    
    query += ' ORDER BY prices.date DESC, items.name'
    
    prices_data = db.execute(query, params).fetchall()
    return jsonify([dict(price) for price in prices_data])

@app.route('/api/price-trends/<int:item_id>')
def api_price_trends(item_id):
    """Get price trends for a specific item"""
    db = get_db()
    days = request.args.get('days', 90, type=int)
    
    trends = db.execute('''
        SELECT prices.date, prices.price, stores.name as store_name, 
               prices.notes, prices.source
        FROM prices
        JOIN stores ON prices.store_id = stores.id
        WHERE prices.item_id = ? AND date >= date('now', '-' || ? || ' days')
        ORDER BY prices.date DESC
    ''', (item_id, days)).fetchall()
    
    return jsonify([dict(trend) for trend in trends])

@app.route('/api/daily-summary')
def daily_summary():
    """Get summary of prices entered today"""
    db = get_db()
    today = datetime.now().strftime('%Y-%m-%d')
    
    summary = db.execute('''
        SELECT prices.*, items.name as item_name, items.unit,
               stores.name as store_name, categories.name as category_name
        FROM prices
        JOIN items ON prices.item_id = items.id
        JOIN stores ON prices.store_id = stores.id
        LEFT JOIN categories ON items.category_id = categories.id
        WHERE date = ?
        ORDER BY items.name
    ''', (today,)).fetchall()
    
    return jsonify([dict(row) for row in summary])

@app.route('/api/price-comparison')
def price_comparison():
    """Compare latest prices across stores"""
    db = get_db()
    
    # Get the latest price for each item at each store
    comparison = db.execute('''
        WITH LatestPrices AS (
            SELECT item_id, store_id, price, date, source,
                   ROW_NUMBER() OVER (PARTITION BY item_id, store_id ORDER BY date DESC) as rn
            FROM prices
        )
        SELECT items.name as item_name, items.unit,
               stores.name as store_name,
               LatestPrices.price, LatestPrices.date, LatestPrices.source,
               categories.name as category_name
        FROM LatestPrices
        JOIN items ON LatestPrices.item_id = items.id
        JOIN stores ON LatestPrices.store_id = stores.id
        LEFT JOIN categories ON items.category_id = categories.id
        WHERE rn = 1
        ORDER BY items.name, stores.name
    ''').fetchall()
    
    return jsonify([dict(row) for row in comparison])

@app.route('/api/scrape', methods=['POST'])
def trigger_scrape():
    """Manually trigger a scrape of all stores"""
    if not getattr(config, 'SCRAPING_ENABLED', True):
        return jsonify({
            'success': False, 
            'error': 'Scraping is disabled in configuration'
        }), 400
    
    try:
        logger.info("Manual scrape triggered")
        results = scraper_manager.scrape_all_stores(save_to_db=True)
        
        total_products = sum(r.get('products_count', 0) for r in results.values())
        total_saved = sum(r.get('saved_count', 0) for r in results.values())
        
        return jsonify({
            'success': True,
            'total_products': total_products,
            'total_saved': total_saved,
            'results': results
        })
    except Exception as e:
        logger.error(f"Error in manual scrape: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/scrape/store/<store_name>', methods=['POST'])
def scrape_store(store_name):
    """Manually trigger a scrape of a specific store"""
    if not getattr(config, 'SCRAPING_ENABLED', True):
        return jsonify({
            'success': False, 
            'error': 'Scraping is disabled in configuration'
        }), 400
    
    try:
        logger.info(f"Manual scrape triggered for {store_name}")
        result = scraper_manager.scrape_store(store_name, save_to_db=True)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error scraping {store_name}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/scrape/status')
def scrape_status():
    """Get status of automatic scraping"""
    last_scrape = scraper_manager.get_last_scrape_time()
    
    return jsonify({
        'enabled': getattr(config, 'SCRAPING_ENABLED', True),
        'interval_hours': getattr(config, 'SCRAPING_INTERVAL_HOURS', 6),
        'last_scrape': last_scrape,
        'mode': 'demo' if scraper_manager.use_demo else 'production',
        'environment': getattr(config, 'RAILWAY_ENVIRONMENT', 'development')
    })

# Initialize database and setup when module is imported
try:
    # Use scraper manager's database initialization
    scraper_manager.initialize_database()
    logger.info("Database initialized successfully")
    
    # Load test stores for demo mode
    if scraper_manager.use_demo:
        stores_added = scraper_manager.add_test_stores()
        logger.info(f"Added {stores_added} test stores for demo mode")
    
except Exception as e:
    logger.error(f"Database initialization failed: {e}")
    # Fallback to manual init
    init_db()

# Schedule automatic scraping if enabled
if getattr(config, 'SCRAPING_ENABLED', True):
    try:
        # Run initial scrape
        logger.info("Running initial price scrape...")
        scheduled_scrape()
        
        # Schedule periodic scraping
        scheduler.add_job(
            func=scheduled_scrape,
            trigger='interval',
            hours=getattr(config, 'SCRAPING_INTERVAL_HOURS', 6),
            id='scrape_prices',
            replace_existing=True
        )
        logger.info(f"Scheduled automatic scraping every {getattr(config, 'SCRAPING_INTERVAL_HOURS', 6)} hours")
    except Exception as e:
        logger.error(f"Failed to setup scraping: {e}")

if __name__ == '__main__':
    # This runs when executing directly (not when imported by gunicorn)
    environment = getattr(config, 'RAILWAY_ENVIRONMENT') or 'development'
    
    print("\n" + "="*60)
    print("🛒 Yellowknife Grocery Price Tracker")
    print("="*60)
    print(f"\n🌐 Environment: {environment.upper()}")
    print(f"🌐 Server: http://{getattr(config, 'HOST', '0.0.0.0')}:{getattr(config, 'PORT', 5000)}")
    print(f"🤖 Auto-scraping: {'ENABLED' if getattr(config, 'SCRAPING_ENABLED', True) else 'DISABLED'}")
    if getattr(config, 'SCRAPING_ENABLED', True):
        print(f"⏰ Scraping interval: Every {getattr(config, 'SCRAPING_INTERVAL_HOURS', 6)} hours")
        print(f"🎭 Mode: {'DEMO (sample data)' if scraper_manager.use_demo else 'PRODUCTION'}")
    print("\n💡 Press CTRL+C to quit\n")
    print("="*60 + "\n")
    
    app.run(
        debug=getattr(config, 'DEBUG', False), 
        host=getattr(config, 'HOST', '0.0.0.0'), 
        port=getattr(config, 'PORT', 5000)
    )