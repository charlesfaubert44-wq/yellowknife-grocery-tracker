// Main JavaScript file for Yellowknife Grocery Tracker

// Global variables
let updateInProgress = false;
let chartInstances = {};

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    // Setup global event listeners
    setupGlobalEventListeners();
    
    // Initialize tooltips and popovers
    initializeBootstrapComponents();
    
    // Setup periodic updates
    setupPeriodicUpdates();
    
    // Load initial data
    loadInitialData();
    
    console.log('Yellowknife Grocery Tracker initialized successfully');
}

function setupGlobalEventListeners() {
    // Global update price button
    const updateButtons = document.querySelectorAll('[onclick*="triggerUpdate"]');
    updateButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            triggerUpdate();
        });
    });
    
    // Global refresh buttons
    const refreshButtons = document.querySelectorAll('[onclick*="refreshData"]');
    refreshButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            refreshData();
        });
    });
    
    // Keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        // Ctrl+R or Cmd+R - Refresh data
        if ((e.ctrlKey || e.metaKey) && e.key === 'r') {
            e.preventDefault();
            refreshData();
        }
        
        // Ctrl+U or Cmd+U - Update prices
        if ((e.ctrlKey || e.metaKey) && e.key === 'u') {
            e.preventDefault();
            triggerUpdate();
        }
    });
}

function initializeBootstrapComponents() {
    // Initialize all tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Initialize all popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
}

function setupPeriodicUpdates() {
    // Update timestamp every minute
    setInterval(updateTimestamp, 60000);
    
    // Check for updates every 5 minutes
    setInterval(checkForUpdates, 300000);
    
    // Update status indicator every 30 seconds
    setInterval(updateStatusIndicator, 30000);
}

function loadInitialData() {
    // Load last update time
    updateTimestamp();
    
    // Load initial status
    updateStatusIndicator();
    
    // Load any page-specific data
    const currentPage = getCurrentPage();
    switch(currentPage) {
        case 'dashboard':
            loadDashboardData();
            break;
        case 'trends':
            loadTrendsData();
            break;
        case 'stores':
            loadStoresData();
            break;
    }
}

function getCurrentPage() {
    const path = window.location.pathname;
    if (path.includes('trends')) return 'trends';
    if (path.includes('stores')) return 'stores';
    if (path.includes('items')) return 'items';
    return 'dashboard';
}

// Global Update Functions
async function triggerUpdate() {
    if (updateInProgress) {
        showNotification('Update already in progress', 'warning');
        return;
    }
    
    updateInProgress = true;
    showLoadingState('Updating prices from all stores...');
    
    try {
        // Simulate API call
        await simulateApiCall('/api/update-prices', 8000);
        
        showNotification('Price update completed successfully!', 'success');
        
        // Refresh current page data
        await refreshData();
        
    } catch (error) {
        console.error('Update failed:', error);
        showNotification('Price update failed. Please try again.', 'danger');
    } finally {
        updateInProgress = false;
        hideLoadingState();
    }
}

async function refreshData() {
    showLoadingState('Refreshing data...');
    
    try {
        // Simulate API call
        await simulateApiCall('/api/refresh-data', 2000);
        
        // Refresh page-specific data
        const currentPage = getCurrentPage();
        switch(currentPage) {
            case 'dashboard':
                await loadDashboardData();
                break;
            case 'trends':
                await loadTrendsData();
                break;
            case 'stores':
                await loadStoresData();
                break;
        }
        
        updateTimestamp();
        showNotification('Data refreshed successfully!', 'success');
        
    } catch (error) {
        console.error('Refresh failed:', error);
        showNotification('Data refresh failed. Please try again.', 'danger');
    } finally {
        hideLoadingState();
    }
}

// Data Loading Functions
async function loadDashboardData() {
    console.log('Loading dashboard data...');
    // Dashboard-specific data loading would go here
}

async function loadTrendsData() {
    console.log('Loading trends data...');
    // Trends-specific data loading would go here
}

async function loadStoresData() {
    console.log('Loading stores data...');
    // Stores-specific data loading would go here
}

// UI Helper Functions
function showLoadingState(message = 'Loading...') {
    const loadingOverlay = document.getElementById('loadingOverlay');
    if (loadingOverlay) {
        const loadingText = loadingOverlay.querySelector('h5');
        if (loadingText) {
            loadingText.textContent = message;
        }
        loadingOverlay.style.display = 'flex';
    }
    
    // Disable all buttons during loading
    const buttons = document.querySelectorAll('button:not(.btn-close)');
    buttons.forEach(btn => {
        btn.disabled = true;
        if (!btn.dataset.originalText) {
            btn.dataset.originalText = btn.innerHTML;
        }
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Loading...';
    });
}

function hideLoadingState() {
    const loadingOverlay = document.getElementById('loadingOverlay');
    if (loadingOverlay) {
        loadingOverlay.style.display = 'none';
    }
    
    // Re-enable all buttons
    const buttons = document.querySelectorAll('button:not(.btn-close)');
    buttons.forEach(btn => {
        btn.disabled = false;
        if (btn.dataset.originalText) {
            btn.innerHTML = btn.dataset.originalText;
        }
    });
}

function showNotification(message, type = 'info', duration = 4000) {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    notification.style.cssText = `
        top: 20px;
        right: 20px;
        z-index: 9999;
        min-width: 300px;
        max-width: 500px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    `;
    
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(notification);
    
    // Auto-dismiss after specified duration
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, duration);
}

function updateTimestamp() {
    const timestampElement = document.getElementById('lastUpdate');
    if (timestampElement) {
        const now = new Date();
        timestampElement.textContent = now.toLocaleString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }
}

function updateStatusIndicator() {
    const statusElement = document.getElementById('statusIndicator');
    if (statusElement) {
        // Simulate status check
        const isOnline = Math.random() > 0.1; // 90% uptime simulation
        
        if (isOnline) {
            statusElement.className = 'badge bg-success';
            statusElement.innerHTML = '<i class="fas fa-circle me-1"></i>Online';
        } else {
            statusElement.className = 'badge bg-danger';
            statusElement.innerHTML = '<i class="fas fa-circle me-1"></i>Offline';
        }
    }
}

async function checkForUpdates() {
    try {
        // Check if new data is available
        const hasUpdates = Math.random() > 0.8; // 20% chance of updates
        
        if (hasUpdates) {
            showNotification('New price data available. Click refresh to update.', 'info', 6000);
        }
    } catch (error) {
        console.error('Update check failed:', error);
    }
}

// Utility Functions
function simulateApiCall(endpoint, duration = 2000) {
    return new Promise((resolve, reject) => {
        setTimeout(() => {
            // Simulate 95% success rate
            if (Math.random() > 0.05) {
                resolve({ success: true, endpoint });
            } else {
                reject(new Error(`API call to ${endpoint} failed`));
            }
        }, duration);
    });
}

function formatCurrency(amount, currency = 'CAD') {
    return new Intl.NumberFormat('en-CA', {
        style: 'currency',
        currency: currency
    }).format(amount);
}

function formatPercentage(value, decimals = 1) {
    return (value * 100).toFixed(decimals) + '%';
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function throttle(func, limit) {
    let inThrottle;
    return function() {
        const args = arguments;
        const context = this;
        if (!inThrottle) {
            func.apply(context, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

// Export functions for use in other scripts
window.GroceryTracker = {
    triggerUpdate,
    refreshData,
    showNotification,
    showLoadingState,
    hideLoadingState,
    formatCurrency,
    formatPercentage,
    simulateApiCall,
    debounce,
    throttle
};

// Service Worker Registration (for PWA capabilities)
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/sw.js')
            .then((registration) => {
                console.log('SW registered: ', registration);
            })
            .catch((registrationError) => {
                console.log('SW registration failed: ', registrationError);
            });
    });
}