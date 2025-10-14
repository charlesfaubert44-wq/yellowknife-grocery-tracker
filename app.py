from flask import Flask, render_template, request, jsonify, redirect, url_for
from datetime import datetime, timedelta
import sqlite3
import json
import os
from pathlib import Path
from apscheduler.schedulers.background import BackgroundScheduler
from scrapers.scraper_manager import ScraperManager
from config import Config
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config.from_object(Config)

# Database setup
DATABASE = 'grocery_prices.db'

# Initialize scraper manager
scraper_manager = ScraperManager(DATABASE, use_demo=True)

# Initialize scheduler for automatic price updates
scheduler = BackgroundScheduler()
scheduler.start()

def get_db():
    """Get database connection"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize the database with tables"""
    with app.app_context():
        db = get_db()
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
        
        # Add some default stores in Yellowknife
        stores = [
            ('Independent Grocer', 'Yellowknife, NT', 'https://www.atlanticsuperstore.ca/', 1),
            ('Extra Foods', 'Yellowknife, NT', 'https://www.extrafoods.ca/', 1),
            ('The Co-op', 'Yellowknife, NT', 'https://www.coopathome.ca/', 1),
            ('Save-On-Foods', 'Yellowknife, NT', 'https://www.saveonfoods.com/', 1)
        ]
        
        for store_name, location, url, scraping in stores:
            try:
                db.execute(
                    'INSERT INTO stores (name, location, website_url, scraping_enabled) VALUES (?, ?, ?, ?)', 
                    (store_name, location, url, scraping)
                )
            except sqlite3.IntegrityError:
                # Update existing stores to enable scraping
                db.execute(
                    'UPDATE stores SET scraping_enabled = ?, website_url = ? WHERE name = ?',
                    (scraping, url, store_name)
                )
        
        # Add default categories
        categories = ['Produce', 'Dairy', 'Meat', 'Bakery', 'Pantry', 'Frozen', 'Beverages', 'Snacks']
        for category in categories:
            try:
                db.execute('INSERT INTO categories (name) VALUES (?)', (category,))
            except sqlite3.IntegrityError:
                pass  # Category already exists
        
        db.commit()
        
        # Add some sample items for testing if using demo mode
        if Config.USE_DEMO_DATA:
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
    if not Config.SCRAPING_ENABLED:
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
    db = get_db()
    
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
    db = get_db()
    
    if request.method == 'POST':
        data = request.json
        try:
            db.execute(
                'INSERT INTO stores (name, location, website_url, scraping_enabled) VALUES (?, ?, ?, ?)', 
                (data['name'], data.get('location', ''), data.get('website_url', ''), 
                 data.get('scraping_enabled', 0))
            )
            db.commit()
            return jsonify({'success': True})
        except sqlite3.IntegrityError:
            return jsonify({'success': False, 'error': 'Store already exists'}), 400
    
    stores_data = db.execute('SELECT * FROM stores ORDER BY name').fetchall()
    return jsonify([dict(store) for store in stores_data])

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
    db = get_db()
    
    if request.method == 'POST':
        data = request.json
        db.execute('INSERT INTO items (name, category_id, unit) VALUES (?, ?, ?)',
                  (data['name'], data['category_id'], data.get('unit', 'each')))
        db.commit()
        return jsonify({'success': True})
    
    items_data = db.execute('''
        SELECT items.*, categories.name as category_name 
        FROM items 
        LEFT JOIN categories ON items.category_id = categories.id 
        ORDER BY items.name
    ''').fetchall()
    return jsonify([dict(item) for item in items_data])

@app.route('/api/prices', methods=['GET', 'POST'])
def api_prices():
    """Get all prices or add a new price entry"""
    db = get_db()
    
    if request.method == 'POST':
        data = request.json
        db.execute('''
            INSERT INTO prices (item_id, store_id, price, date, notes, source) 
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (data['item_id'], data['store_id'], data['price'], 
              data.get('date', datetime.now().strftime('%Y-%m-%d')), 
              data.get('notes', ''), data.get('source', 'manual')))
        db.commit()
        return jsonify({'success': True})
    
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
    if not Config.SCRAPING_ENABLED:
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
    if not Config.SCRAPING_ENABLED:
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
        'enabled': Config.SCRAPING_ENABLED,
        'interval_hours': Config.SCRAPING_INTERVAL_HOURS,
        'last_scrape': last_scrape,
        'mode': 'demo' if scraper_manager.use_demo else 'production'
    })

if __name__ == '__main__':
    # Initialize database
    init_db()
    
    # Schedule automatic scraping if enabled
    if Config.SCRAPING_ENABLED:
        # Run initial scrape
        logger.info("Running initial price scrape...")
        scheduled_scrape()
        
        # Schedule periodic scraping
        scheduler.add_job(
            func=scheduled_scrape,
            trigger='interval',
            hours=Config.SCRAPING_INTERVAL_HOURS,
            id='scrape_prices',
            replace_existing=True
        )
        logger.info(f"Scheduled automatic scraping every {Config.SCRAPING_INTERVAL_HOURS} hours")
    
    # Run the app
    print("\n" + "="*60)
    print("🛒 Yellowknife Grocery Price Tracker - ONLINE VERSION")
    print("="*60)
    print(f"\n🌐 Server: http://{Config.HOST}:{Config.PORT}")
    print(f"🤖 Auto-scraping: {'ENABLED' if Config.SCRAPING_ENABLED else 'DISABLED'}")
    if Config.SCRAPING_ENABLED:
        print(f"⏰ Scraping interval: Every {Config.SCRAPING_INTERVAL_HOURS} hours")
        print(f"🎭 Mode: {'DEMO (sample data)' if scraper_manager.use_demo else 'PRODUCTION'}")
    print("\n💡 Press CTRL+C to quit\n")
    print("="*60 + "\n")
    
    app.run(debug=(Config.FLASK_ENV == 'development'), host=Config.HOST, port=Config.PORT)