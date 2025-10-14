// API Integration Module for Yellowknife Grocery Tracker
// This file demonstrates how the UI connects to your Flask backend APIs

class GroceryTrackerAPI {
    constructor() {
        this.baseURL = window.location.origin;
    }

    // Dashboard API calls
    async getDashboardData() {
        try {
            const [stores, items, prices, summary] = await Promise.all([
                this.fetchStores(),
                this.fetchItems(),
                this.fetchPriceComparison(),
                this.fetchDailySummary()
            ]);
            
            return {
                stores,
                items,
                prices,
                summary
            };
        } catch (error) {
            console.error('Error loading dashboard data:', error);
            throw error;
        }
    }

    // Store Management
    async fetchStores() {
        const response = await fetch(`${this.baseURL}/api/stores`);
        if (!response.ok) throw new Error('Failed to fetch stores');
        return response.json();
    }

    async addStore(storeData) {
        const response = await fetch(`${this.baseURL}/api/stores`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(storeData)
        });
        
        if (!response.ok) throw new Error('Failed to add store');
        return response.json();
    }

    // Items Management
    async fetchItems(filters = {}) {
        const params = new URLSearchParams(filters);
        const response = await fetch(`${this.baseURL}/api/items?${params}`);
        if (!response.ok) throw new Error('Failed to fetch items');
        return response.json();
    }

    async addItem(itemData) {
        const response = await fetch(`${this.baseURL}/api/items`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(itemData)
        });
        
        if (!response.ok) throw new Error('Failed to add item');
        return response.json();
    }

    // Price Data
    async fetchPrices(filters = {}) {
        const params = new URLSearchParams(filters);
        const response = await fetch(`${this.baseURL}/api/prices?${params}`);
        if (!response.ok) throw new Error('Failed to fetch prices');
        return response.json();
    }

    async fetchPriceComparison() {
        const response = await fetch(`${this.baseURL}/api/price-comparison`);
        if (!response.ok) throw new Error('Failed to fetch price comparison');
        return response.json();
    }

    // Trends and Analytics
    async fetchPriceTrends(itemId, period = '30d') {
        const response = await fetch(`${this.baseURL}/api/price-trends/${itemId}?period=${period}`);
        if (!response.ok) throw new Error('Failed to fetch price trends');
        return response.json();
    }

    async fetchDailySummary() {
        const response = await fetch(`${this.baseURL}/api/daily-summary`);
        if (!response.ok) throw new Error('Failed to fetch daily summary');
        return response.json();
    }

    // Scraping Operations
    async triggerScrapeAll() {
        const response = await fetch(`${this.baseURL}/api/scrape`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        
        if (!response.ok) throw new Error('Failed to trigger scrape');
        return response.json();
    }

    async triggerScrapeStore(storeName) {
        const response = await fetch(`${this.baseURL}/api/scrape/store/${storeName}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        
        if (!response.ok) throw new Error(`Failed to scrape ${storeName}`);
        return response.json();
    }

    async getScrapeStatus() {
        const response = await fetch(`${this.baseURL}/api/scrape/status`);
        if (!response.ok) throw new Error('Failed to get scrape status');
        return response.json();
    }

    // Categories
    async fetchCategories() {
        const response = await fetch(`${this.baseURL}/api/categories`);
        if (!response.ok) throw new Error('Failed to fetch categories');
        return response.json();
    }

    async addCategory(categoryData) {
        const response = await fetch(`${this.baseURL}/api/categories`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(categoryData)
        });
        
        if (!response.ok) throw new Error('Failed to add category');
        return response.json();
    }
}

// Enhanced UI Integration Functions
class UIDataLoader {
    constructor() {
        this.api = new GroceryTrackerAPI();
    }

    async loadDashboard() {
        try {
            const data = await this.api.getDashboardData();
            
            // Update summary cards
            this.updateSummaryCards(data.summary);
            
            // Update price comparison table
            this.updatePriceTable(data.prices);
            
            // Update store status
            this.updateStoreStatus(data.stores);
            
        } catch (error) {
            console.error('Dashboard load failed:', error);
            this.showError('Failed to load dashboard data');
        }
    }

    async loadTrends(period = '30d') {
        try {
            // This would fetch trend data for multiple items
            const trendData = await this.api.fetchPriceTrends('all', period);
            
            // Update trend charts
            this.updateTrendCharts(trendData);
            
        } catch (error) {
            console.error('Trends load failed:', error);
            this.showError('Failed to load trend data');
        }
    }

    async loadStores() {
        try {
            const stores = await this.api.fetchStores();
            
            // Update store list
            this.updateStoreList(stores);
            
        } catch (error) {
            console.error('Stores load failed:', error);
            this.showError('Failed to load store data');
        }
    }

    async loadItems(filters = {}) {
        try {
            const items = await this.api.fetchItems(filters);
            
            // Update items table
            this.updateItemsTable(items);
            
        } catch (error) {
            console.error('Items load failed:', error);
            this.showError('Failed to load items data');
        }
    }

    // UI Update Methods
    updateSummaryCards(summary) {
        // Update the dashboard summary cards with real data
        if (summary.totalItems) {
            document.querySelector('.summary-items .fw-bold').textContent = summary.totalItems.toLocaleString();
        }
        if (summary.activeStores) {
            document.querySelector('.summary-stores .fw-bold').textContent = summary.activeStores;
        }
        if (summary.avgSavings) {
            document.querySelector('.summary-savings .fw-bold').textContent = `$${summary.avgSavings}`;
        }
        if (summary.lastUpdate) {
            document.querySelector('#lastUpdate').textContent = new Date(summary.lastUpdate).toLocaleString();
        }
    }

    updatePriceTable(prices) {
        const tbody = document.querySelector('#priceTable tbody');
        if (!tbody || !prices) return;

        tbody.innerHTML = '';
        
        prices.forEach(item => {
            const row = this.createPriceRow(item);
            tbody.appendChild(row);
        });
    }

    createPriceRow(item) {
        const row = document.createElement('tr');
        
        // Find best price
        const prices = [
            { store: 'independent', price: item.independent_price },
            { store: 'extrafoods', price: item.extrafoods_price },
            { store: 'coop', price: item.coop_price },
            { store: 'saveon', price: item.saveon_price }
        ].filter(p => p.price);
        
        const bestPrice = prices.reduce((min, p) => p.price < min.price ? p : min);

        row.innerHTML = `
            <td>
                <div class="d-flex align-items-center">
                    <div class="bg-light rounded p-2 me-3">
                        <i class="${this.getCategoryIcon(item.category)}"></i>
                    </div>
                    <div>
                        <div class="fw-bold">${item.name}</div>
                        <small class="text-muted">${item.description || ''}</small>
                    </div>
                </div>
            </td>
            <td class="text-center">
                <span class="badge bg-${this.getCategoryColor(item.category)} bg-opacity-10 text-${this.getCategoryColor(item.category)}">
                    ${item.category}
                </span>
            </td>
            ${prices.map(p => `
                <td class="text-center">
                    <div class="price-cell ${p.price === bestPrice.price ? 'best-price' : ''}">
                        <span class="fw-bold ${p.price === bestPrice.price ? 'text-success' : ''}">
                            $${p.price.toFixed(2)}
                        </span>
                    </div>
                </td>
            `).join('')}
            <td class="text-center">
                <div class="best-price-badge">
                    <span class="badge bg-success">$${bestPrice.price.toFixed(2)}</span>
                    <div class="small text-muted">${this.getStoreDisplayName(bestPrice.store)}</div>
                </div>
            </td>
            <td class="text-center">
                <div class="trend-indicator">
                    <i class="fas fa-arrow-${item.trend > 0 ? 'up text-danger' : 'down text-success'}"></i>
                    <small class="${item.trend > 0 ? 'text-danger' : 'text-success'}">${Math.abs(item.trend)}%</small>
                </div>
            </td>
        `;

        return row;
    }

    getCategoryIcon(category) {
        const icons = {
            'produce': 'fas fa-apple-alt text-success',
            'dairy': 'fas fa-cheese text-info',
            'meat': 'fas fa-drumstick-bite text-danger',
            'bakery': 'fas fa-bread-slice text-warning',
            'frozen': 'fas fa-snowflake text-primary',
            'pantry': 'fas fa-box text-secondary'
        };
        return icons[category] || 'fas fa-shopping-basket text-muted';
    }

    getCategoryColor(category) {
        const colors = {
            'produce': 'success',
            'dairy': 'info',
            'meat': 'danger',
            'bakery': 'warning',
            'frozen': 'primary',
            'pantry': 'secondary'
        };
        return colors[category] || 'muted';
    }

    getStoreDisplayName(store) {
        const names = {
            'independent': 'Independent',
            'extrafoods': 'Extra Foods',
            'coop': 'Co-op',
            'saveon': 'Save-On'
        };
        return names[store] || store;
    }

    showError(message) {
        if (window.GroceryTracker && window.GroceryTracker.showNotification) {
            window.GroceryTracker.showNotification(message, 'danger');
        } else {
            console.error(message);
        }
    }
}

// Global instance for use across templates
window.groceryAPI = new GroceryTrackerAPI();
window.uiLoader = new UIDataLoader();

// Export for module use
export { GroceryTrackerAPI, UIDataLoader };