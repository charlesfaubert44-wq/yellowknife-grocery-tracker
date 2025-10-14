# 🛒 Yellowknife Grocery Price Tracker - ONLINE VERSION

An automated web application that tracks grocery prices across Yellowknife stores with automatic price scraping, trend analysis, and multi-store comparison. Deploy online and access from anywhere!

## 🌟 Key Features

### 🤖 **Automatic Price Scraping**
- Scheduled automatic updates every 6 hours
- Fetches prices from multiple Yellowknife stores
- Smart item matching and categorization
- Demo mode with realistic sample data (production scrapers customizable)

### 📊 **Price Intelligence**
- **Live Price Comparison**: See best prices across all stores at a glance
- **Trend Analysis**: Historical price tracking with min/max/average statistics
- **Daily Updates**: View today's price changes
- **Source Tracking**: See which prices are auto-fetched vs manually entered

### 🏪 **Multi-Store Support**
Pre-configured with major Yellowknife stores:
- Independent Grocer
- Extra Foods
- The Co-op
- Save-On-Foods

### 🌐 **Online Deployment**
- Deploy to Railway, Render, or Heroku with one click
- PostgreSQL support for production
- Scheduled background tasks
- Environment-based configuration

### 📱 **Modern Interface**
- Responsive design (works on all devices)
- Real-time status indicators
- Manual trigger for immediate updates
- Beautiful, intuitive UI

## 🚀 Quick Start

### Deploy to Railway (Recommended)

1. **Fork this repository** to your GitHub account

2. **Create a Railway account** at [railway.app](https://railway.app)

3. **Deploy from GitHub**:
   - Click "New Project" in Railway
   - Select "Deploy from GitHub repo"
   - Choose your forked repository
   - Railway will automatically detect the configuration

4. **Set Environment Variables** (optional):
   ```
   SECRET_KEY=your-super-secret-key-here
   USE_DEMO_DATA=True
   SCRAPING_ENABLED=True
   ```

5. **Access your app**: Railway will provide a URL like `https://your-app.railway.app`

### Local Development

```bash
# Clone the repository
git clone https://github.com/yourusername/yellowknife-grocery-tracker.git
cd yellowknife-grocery-tracker

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py
```

Visit `http://localhost:5000` to see your app!

## 🛠 Railway Deployment Guide

### Automatic Configuration
Railway automatically detects and configures:
- **Python Environment**: Uses `runtime.txt` (Python 3.11)
- **Dependencies**: Installs from `requirements.txt`
- **Web Process**: Runs via `Procfile` with Gunicorn
- **Build System**: Uses Nixpacks for optimal builds

### Key Configuration Files

#### `railway.toml`
```toml
[build]
builder = "nixpacks"

[deploy]
startCommand = "gunicorn --bind 0.0.0.0:$PORT --timeout 120 app:app"
healthcheckPath = "/"
restartPolicyType = "on_failure"
restartPolicyMaxRetries = 3
```

#### `Procfile`
```
web: gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 120 app:app
```

### Environment Variables
Configure these in Railway's dashboard (Variables tab):

| Variable | Description | Default Value |
|----------|-------------|---------------|
| `SECRET_KEY` | Flask session security | Auto-generated |
| `USE_DEMO_DATA` | Enable sample data | `True` |
| `SCRAPING_ENABLED` | Enable price scraping | `True` |
| `DATABASE_URL` | Database connection | Auto-provided |
| `PORT` | Application port | Auto-provided |

### Production Features
- **Auto-scaling**: Railway handles traffic spikes
- **SSL/HTTPS**: Automatic secure connections
- **Custom Domains**: Add your own domain
- **Database**: PostgreSQL auto-provisioned
- **Monitoring**: Built-in metrics and logs

### Deployment Steps
1. **Connect GitHub**: Link your forked repository
2. **Auto-Deploy**: Railway builds and deploys automatically
3. **Environment Setup**: Configure variables if needed
4. **Custom Domain**: Optional - add your domain
5. **Monitor**: Use Railway's dashboard for metrics

### Deployment Checklist
Before deploying to Railway, ensure:
- [ ] All files are committed to your GitHub repository
- [ ] `requirements.txt` contains all dependencies
- [ ] `runtime.txt` specifies Python version (3.11)
- [ ] `Procfile` defines the web process
- [ ] `railway.toml` contains deployment configuration
- [ ] Environment variables are configured (if needed)

### Troubleshooting
- **Build Failures**: Check `requirements.txt` compatibility
- **Database Issues**: Verify `DATABASE_URL` is set
- **Port Binding**: Ensure app uses `$PORT` environment variable
- **Timeouts**: Adjust Gunicorn timeout in `Procfile`
- **Dependencies**: Ensure all imports are in `requirements.txt`