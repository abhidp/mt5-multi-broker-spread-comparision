# DEPLOYMENT.md

Comprehensive guide to deploying the MT5 Spread Monitor as a public website with ad monetization.

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Prerequisites](#2-prerequisites)
3. [Database Setup (Supabase)](#3-database-setup-supabase)
4. [Code Migration (CSV → PostgreSQL)](#4-code-migration-csv--postgresql)
5. [Production Flask Setup](#5-production-flask-setup)
6. [Railway Deployment](#6-railway-deployment)
7. [Cloudflare Setup](#7-cloudflare-setup)
8. [Collector Configuration](#8-collector-configuration)
9. [Ad Integration (Google AdSense)](#9-ad-integration-google-adsense)
10. [Legal Pages](#10-legal-pages)
11. [SEO Optimization](#11-seo-optimization)
12. [Monitoring & Maintenance](#12-monitoring--maintenance)
13. [Scaling & Cost Optimization](#13-scaling--cost-optimization)

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           YOUR WINDOWS MINI PC                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ MT5 Terminal│  │ MT5 Terminal│  │ MT5 Terminal│  │ MT5 Terminal│  ...    │
│  │ Pepperstone │  │ FusionMkts  │  │ ICMarkets   │  │ Vantage     │         │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘         │
│         └────────────────┴────────────────┴────────────────┘                │
│                                    │                                        │
│                          ┌─────────▼─────────┐                              │
│                          │   collector.py    │                              │
│                          │  (runs 24/7)      │                              │
│                          └─────────┬─────────┘                              │
└────────────────────────────────────┼────────────────────────────────────────┘
                                     │ HTTPS (every minute)
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              SUPABASE (Free Tier)                           │
│                          ┌─────────────────────┐                            │
│                          │    PostgreSQL DB    │                            │
│                          │  - spread_data      │                            │
│                          │  - brokers          │                            │
│                          └─────────────────────┘                            │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              RAILWAY (Free Tier)                            │
│                          ┌─────────────────────┐                            │
│                          │     Flask App       │                            │
│                          │  (Gunicorn + nginx) │                            │
│                          └─────────────────────┘                            │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                             CLOUDFLARE (Free Tier)                          │
│                    ┌───────────────────────────────────┐                    │
│                    │  CDN + SSL + DDoS Protection      │                    │
│                    │  spreadmonitor.railway.app        │                    │
│                    └───────────────────────────────────┘                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
                              [Public Internet]
                                 + AdSense
```

### Cost Summary

| Service | Free Tier Limits | Paid (if exceeded) |
|---------|------------------|-------------------|
| Supabase | 500MB DB, 50K rows, 2GB bandwidth | $25/mo |
| Railway | $5 credit/month, 512MB RAM | ~$5-10/mo |
| Cloudflare | Unlimited bandwidth, SSL | $0 |
| **Total** | **$0/month** | **$5-35/month** |

---

## 2. Prerequisites

### Accounts to Create

1. **GitHub** - https://github.com (for code hosting & Railway integration)
2. **Supabase** - https://supabase.com (database)
3. **Railway** - https://railway.app (web hosting)
4. **Cloudflare** - https://cloudflare.com (CDN & SSL)
5. **Google AdSense** - https://adsense.google.com (ads - apply after site is live)

### Local Development

```bash
# Ensure you have these installed
python --version  # 3.10+
git --version
pip --version

# Install additional packages for PostgreSQL
pip install psycopg2-binary sqlalchemy
```

---

## 3. Database Setup (Supabase)

### 3.1 Create Supabase Project

1. Go to https://supabase.com and sign up
2. Click "New Project"
3. Choose a name: `spread-monitor`
4. Set a strong database password (save it!)
5. Select region closest to your Railway deployment (e.g., `us-east-1`)
6. Wait for project to provision (~2 minutes)

### 3.2 Get Connection Details

1. Go to Project Settings → Database
2. Note down:
   - **Host**: `db.xxxxxxxxxxxx.supabase.co`
   - **Database name**: `postgres`
   - **Port**: `5432`
   - **User**: `postgres`
   - **Password**: (the one you set)

3. Connection string format:
```
postgresql://postgres:[PASSWORD]@db.[PROJECT_REF].supabase.co:5432/postgres
```

### 3.3 Create Database Schema

Go to SQL Editor in Supabase and run:

```sql
-- Spread data table (main data)
CREATE TABLE spread_data (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    broker VARCHAR(100) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    bid DECIMAL(15, 5) NOT NULL,
    ask DECIMAL(15, 5) NOT NULL,
    spread DECIMAL(15, 5) NOT NULL,
    spread_points DECIMAL(10, 2) NOT NULL,
    session VARCHAR(20),
    day_of_week VARCHAR(10),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for common queries
CREATE INDEX idx_spread_data_timestamp ON spread_data(timestamp DESC);
CREATE INDEX idx_spread_data_broker ON spread_data(broker);
CREATE INDEX idx_spread_data_symbol ON spread_data(symbol);
CREATE INDEX idx_spread_data_session ON spread_data(session);
CREATE INDEX idx_spread_data_composite ON spread_data(symbol, timestamp DESC);

-- Broker metadata table
CREATE TABLE brokers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    short_name VARCHAR(50),
    website VARCHAR(255),
    logo_url VARCHAR(500),
    commission_per_lot DECIMAL(10, 2),
    commission_currency VARCHAR(10) DEFAULT 'AUD',
    commission_free_symbols TEXT[], -- Array of symbol prefixes
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert broker data
INSERT INTO brokers (name, short_name, website, commission_per_lot, commission_currency, commission_free_symbols) VALUES
('Pepperstone Razor', 'Pepperstone', 'pepperstone.com', 7.00, 'AUD', ARRAY['XAU', 'XAG']),
('FusionMarkets Zero', 'Fusion', 'fusionmarkets.com', 4.50, 'AUD', ARRAY[]::TEXT[]),
('ThinkMarkets ThinkZero', 'ThinkMarkets', 'thinkmarkets.com', 7.00, 'AUD', ARRAY[]::TEXT[]),
('ICMarkets Raw', 'ICMarkets', 'icmarkets.com', 9.00, 'AUD', ARRAY[]::TEXT[]),
('VantageMarkets Raw', 'Vantage', 'vantagemarkets.com', 5.00, 'AUD', ARRAY['XAU', 'XAG']),
('FPMarkets Raw', 'FPMarkets', 'fpmarkets.com', 7.00, 'AUD', ARRAY[]::TEXT[]);

-- Function to auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_brokers_updated_at BEFORE UPDATE ON brokers
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- View for latest spreads (for live page)
CREATE VIEW latest_spreads AS
SELECT DISTINCT ON (broker, symbol)
    id, timestamp, broker, symbol, bid, ask, spread, spread_points, session
FROM spread_data
ORDER BY broker, symbol, timestamp DESC;

-- Data retention: Auto-delete data older than 90 days (optional)
-- Run this manually or set up a cron job
-- DELETE FROM spread_data WHERE timestamp < NOW() - INTERVAL '90 days';
```

### 3.4 Enable Row Level Security (Optional but Recommended)

```sql
-- Enable RLS
ALTER TABLE spread_data ENABLE ROW LEVEL SECURITY;
ALTER TABLE brokers ENABLE ROW LEVEL SECURITY;

-- Allow public read access
CREATE POLICY "Allow public read access on spread_data" ON spread_data
    FOR SELECT USING (true);

CREATE POLICY "Allow public read access on brokers" ON brokers
    FOR SELECT USING (true);

-- Create a service role for writes (collector will use this)
-- The service_role key bypasses RLS
```

---

## 4. Code Migration (CSV → PostgreSQL)

### 4.1 Create Database Utility Module

Create `spread_monitor/utils/db.py`:

```python
"""
Database utility module for PostgreSQL operations.
Replaces CSV-based storage with Supabase PostgreSQL.
"""

import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.pool import QueuePool
import pandas as pd

# Database URL from environment variable
DATABASE_URL = os.environ.get('DATABASE_URL')

# Create engine with connection pooling
engine = None

def get_engine():
    """Get or create database engine with connection pooling."""
    global engine
    if engine is None:
        if not DATABASE_URL:
            raise ValueError("DATABASE_URL environment variable not set")
        engine = create_engine(
            DATABASE_URL,
            poolclass=QueuePool,
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            pool_recycle=1800  # Recycle connections after 30 minutes
        )
    return engine

@contextmanager
def get_connection():
    """Context manager for database connections."""
    conn = get_engine().connect()
    try:
        yield conn
    finally:
        conn.close()

def save_spread_data(data_list: List[Dict[str, Any]]) -> int:
    """
    Save spread data to database.

    Args:
        data_list: List of spread data dictionaries

    Returns:
        Number of rows inserted
    """
    if not data_list:
        return 0

    df = pd.DataFrame(data_list)

    # Ensure correct column order
    columns = ['timestamp', 'broker', 'symbol', 'bid', 'ask', 'spread',
               'spread_points', 'session', 'day_of_week']
    df = df[columns]

    with get_connection() as conn:
        df.to_sql('spread_data', conn, if_exists='append', index=False)
        conn.commit()

    return len(data_list)

def get_latest_spreads(symbol: str = 'XAUUSD') -> List[Dict[str, Any]]:
    """Get latest spread for each broker."""
    query = """
        SELECT DISTINCT ON (broker)
            timestamp, broker, symbol, bid, ask, spread, spread_points, session
        FROM spread_data
        WHERE symbol = :symbol
        ORDER BY broker, timestamp DESC
    """

    with get_connection() as conn:
        result = conn.execute(text(query), {'symbol': symbol})
        rows = result.fetchall()

    return [dict(row._mapping) for row in rows]

def get_history(start_date: str, end_date: str, symbol: str = 'XAUUSD') -> List[Dict[str, Any]]:
    """Get historical spread data."""
    query = """
        SELECT timestamp, broker, symbol, bid, ask, spread, spread_points, session, day_of_week
        FROM spread_data
        WHERE symbol = :symbol
          AND timestamp >= :start_date
          AND timestamp < :end_date::date + INTERVAL '1 day'
        ORDER BY timestamp ASC
    """

    with get_connection() as conn:
        result = conn.execute(text(query), {
            'symbol': symbol,
            'start_date': start_date,
            'end_date': end_date
        })
        rows = result.fetchall()

    return [dict(row._mapping) for row in rows]

def get_stats(start_date: str, end_date: str, symbol: str = 'XAUUSD') -> List[Dict[str, Any]]:
    """Get aggregated statistics by broker."""
    query = """
        SELECT
            broker,
            AVG(spread_points) as avg,
            MIN(spread_points) as min,
            MAX(spread_points) as max,
            STDDEV(spread_points) as std,
            COUNT(*) as count
        FROM spread_data
        WHERE symbol = :symbol
          AND timestamp >= :start_date
          AND timestamp < :end_date::date + INTERVAL '1 day'
        GROUP BY broker
        ORDER BY avg ASC
    """

    with get_connection() as conn:
        result = conn.execute(text(query), {
            'symbol': symbol,
            'start_date': start_date,
            'end_date': end_date
        })
        rows = result.fetchall()

    return [dict(row._mapping) for row in rows]

def get_session_stats(start_date: str, end_date: str, symbol: str = 'XAUUSD') -> List[Dict[str, Any]]:
    """Get statistics grouped by session and broker."""
    query = """
        SELECT
            session,
            broker,
            AVG(spread_points) as avg,
            MIN(spread_points) as min,
            MAX(spread_points) as max,
            COUNT(*) as count
        FROM spread_data
        WHERE symbol = :symbol
          AND timestamp >= :start_date
          AND timestamp < :end_date::date + INTERVAL '1 day'
          AND session IS NOT NULL
        GROUP BY session, broker
        ORDER BY session, avg ASC
    """

    with get_connection() as conn:
        result = conn.execute(text(query), {
            'symbol': symbol,
            'start_date': start_date,
            'end_date': end_date
        })
        rows = result.fetchall()

    return [dict(row._mapping) for row in rows]

def get_brokers() -> List[Dict[str, Any]]:
    """Get all broker metadata."""
    query = """
        SELECT name, short_name, website, logo_url,
               commission_per_lot, commission_currency, commission_free_symbols
        FROM brokers
        WHERE is_active = true
        ORDER BY name
    """

    with get_connection() as conn:
        result = conn.execute(text(query))
        rows = result.fetchall()

    return [dict(row._mapping) for row in rows]

def cleanup_old_data(days: int = 90) -> int:
    """Delete data older than specified days."""
    query = """
        DELETE FROM spread_data
        WHERE timestamp < NOW() - INTERVAL ':days days'
    """

    with get_connection() as conn:
        result = conn.execute(text(query), {'days': days})
        conn.commit()

    return result.rowcount
```

### 4.2 Update Collector to Use Database

Modify `spread_monitor/collector.py` - replace CSV saving with database:

```python
# At the top, add:
from utils.db import save_spread_data

# Replace the save_to_csv function call with:
def collect_spreads():
    """Collect spreads from all brokers and save to database."""
    all_data = []

    for broker_config in config['brokers']:
        # ... existing collection logic ...

        if spread_data:
            all_data.append({
                'timestamp': spread_data.timestamp,
                'broker': spread_data.broker,
                'symbol': spread_data.symbol,
                'bid': spread_data.bid,
                'ask': spread_data.ask,
                'spread': spread_data.spread,
                'spread_points': spread_data.spread_points,
                'session': get_current_session(),
                'day_of_week': datetime.utcnow().strftime('%A')
            })

    if all_data:
        rows_saved = save_spread_data(all_data)
        logger.info(f"Saved {rows_saved} spread records to database")
```

### 4.3 Update Flask App to Use Database

Modify `spread_monitor/app.py` API endpoints:

```python
# At the top, add:
from utils.db import (
    get_latest_spreads,
    get_history,
    get_stats,
    get_session_stats,
    get_brokers
)

# Replace file-based endpoints with database queries:

@app.route('/api/live')
def api_live():
    """Get latest spreads for all brokers."""
    symbol = request.args.get('symbol', 'XAUUSD')
    data = get_latest_spreads(symbol)
    return jsonify({
        'success': True,
        'data': data,
        'timestamp': datetime.utcnow().isoformat()
    })

@app.route('/api/history')
def api_history():
    """Get historical spread data."""
    start_date = request.args.get('start')
    end_date = request.args.get('end')
    symbol = request.args.get('symbol', 'XAUUSD')

    if not start_date or not end_date:
        return jsonify({'success': False, 'error': 'start and end dates required'}), 400

    data = get_history(start_date, end_date, symbol)
    return jsonify({'success': True, 'data': data})

@app.route('/api/stats')
def api_stats():
    """Get aggregated statistics."""
    start_date = request.args.get('start')
    end_date = request.args.get('end')
    symbol = request.args.get('symbol', 'XAUUSD')

    if not start_date or not end_date:
        return jsonify({'success': False, 'error': 'start and end dates required'}), 400

    data = get_stats(start_date, end_date, symbol)
    return jsonify({'success': True, 'data': data})

@app.route('/api/sessions')
def api_sessions():
    """Get session-based statistics."""
    start_date = request.args.get('start')
    end_date = request.args.get('end')
    symbol = request.args.get('symbol', 'XAUUSD')

    if not start_date or not end_date:
        return jsonify({'success': False, 'error': 'start and end dates required'}), 400

    data = get_session_stats(start_date, end_date, symbol)
    return jsonify({'success': True, 'data': data})

@app.route('/api/brokers')
def api_brokers():
    """Get broker metadata."""
    brokers = get_brokers()
    # Convert to dict format expected by frontend
    broker_dict = {b['name']: b for b in brokers}
    return jsonify({'success': True, 'data': broker_dict})
```

### 4.4 Migrate Existing CSV Data (Optional)

Create a one-time migration script `spread_monitor/migrate_csv_to_db.py`:

```python
"""
One-time script to migrate existing CSV data to PostgreSQL.
Run this after setting up the database.
"""

import os
import glob
import pandas as pd
from utils.db import get_engine

def migrate_csv_files():
    """Migrate all CSV files to database."""
    csv_pattern = os.path.join('data', 'spread_data_*.csv')
    csv_files = sorted(glob.glob(csv_pattern))

    if not csv_files:
        print("No CSV files found to migrate")
        return

    print(f"Found {len(csv_files)} CSV files to migrate")

    engine = get_engine()
    total_rows = 0

    for csv_file in csv_files:
        print(f"Migrating {csv_file}...")
        df = pd.read_csv(csv_file)

        # Ensure timestamp is datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'])

        # Insert into database
        df.to_sql('spread_data', engine, if_exists='append', index=False)
        total_rows += len(df)
        print(f"  Migrated {len(df)} rows")

    print(f"\nMigration complete! Total rows migrated: {total_rows}")

if __name__ == '__main__':
    migrate_csv_files()
```

---

## 5. Production Flask Setup

### 5.1 Update Requirements

Update `spread_monitor/requirements.txt`:

```
# Core
Flask>=3.0.0
gunicorn>=21.0.0

# Database
psycopg2-binary>=2.9.9
SQLAlchemy>=2.0.0

# Data processing
pandas>=2.0.0
numpy>=1.24.0

# MT5 (for collector only, not needed on Railway)
MetaTrader5>=5.0.45

# Scheduling (for collector only)
APScheduler>=3.10.0

# Logging
python-json-logger>=2.0.0
```

### 5.2 Create Production Entry Point

Create `spread_monitor/wsgi.py`:

```python
"""
WSGI entry point for production deployment.
"""

import os
from app import app

# Ensure environment variables are set
if not os.environ.get('DATABASE_URL'):
    raise RuntimeError("DATABASE_URL environment variable must be set")

if __name__ == '__main__':
    app.run()
```

### 5.3 Create Procfile for Railway

Create `spread_monitor/Procfile`:

```
web: gunicorn wsgi:app --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 120
```

### 5.4 Create Railway Configuration

Create `spread_monitor/railway.json`:

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "gunicorn wsgi:app --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 120",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

### 5.5 Create .env.example

Create `spread_monitor/.env.example`:

```bash
# Database
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@db.YOUR_PROJECT.supabase.co:5432/postgres

# Flask
FLASK_ENV=production
SECRET_KEY=your-secret-key-change-this

# Optional: Sentry for error tracking
# SENTRY_DSN=https://xxx@sentry.io/xxx
```

### 5.6 Update .gitignore

Add to `.gitignore`:

```
# Environment
.env
*.env

# Don't deploy collector-specific files
config.json

# Python
__pycache__/
*.pyc
*.pyo
venv/
.venv/

# Data (now in database)
data/
logs/
```

---

## 6. Railway Deployment

### 6.1 Prepare Repository

```bash
# Create a new branch for production
git checkout -b production

# Commit all changes
git add .
git commit -m "Prepare for Railway deployment"

# Push to GitHub
git push -u origin production
```

### 6.2 Create Railway Project

1. Go to https://railway.app and sign in with GitHub
2. Click "New Project" → "Deploy from GitHub repo"
3. Select your `mt5-multi-broker-spread-comparision` repository
4. Select the `production` branch
5. Railway will auto-detect Python and start building

### 6.3 Configure Environment Variables

In Railway dashboard:

1. Click on your service
2. Go to "Variables" tab
3. Add these variables:

```
DATABASE_URL = postgresql://postgres:PASSWORD@db.PROJECT.supabase.co:5432/postgres
FLASK_ENV = production
SECRET_KEY = (generate a random 32+ character string)
```

### 6.4 Configure Root Directory

Since your Flask app is in `spread_monitor/`:

1. Go to Settings
2. Set "Root Directory" to `spread_monitor`

### 6.5 Deploy

1. Railway will auto-deploy on push
2. Check "Deployments" tab for build logs
3. Once deployed, click "Settings" → "Generate Domain"
4. Your app will be at `https://your-app.up.railway.app`

### 6.6 Verify Deployment

```bash
# Test the API
curl https://your-app.up.railway.app/api/brokers
curl https://your-app.up.railway.app/api/live
```

---

## 7. Cloudflare Setup

### 7.1 Add Site to Cloudflare

1. Sign up at https://cloudflare.com
2. Click "Add a Site"
3. Enter your Railway domain (or custom domain later)
4. Select Free plan

### 7.2 Configure DNS (if using custom domain)

If you get a custom domain later:

1. Add domain to Cloudflare
2. Update nameservers at your registrar
3. Add CNAME record: `@ → your-app.up.railway.app`

### 7.3 Configure Caching Rules

Go to Caching → Configuration:

```
Browser Cache TTL: 4 hours
```

Create Page Rules:

1. **Cache API responses** (careful with live data):
   - URL: `*your-domain.com/api/history*`
   - Cache Level: Cache Everything
   - Edge Cache TTL: 1 hour

2. **Don't cache live data**:
   - URL: `*your-domain.com/api/live*`
   - Cache Level: Bypass

### 7.4 Enable Performance Features

- Auto Minify: HTML, CSS, JS
- Brotli Compression: On
- HTTP/3: On
- 0-RTT Connection Resumption: On

### 7.5 Security Settings

- SSL/TLS: Full (strict)
- Always Use HTTPS: On
- Minimum TLS Version: 1.2
- Bot Fight Mode: On

---

## 8. Collector Configuration

### 8.1 Set Up Collector on Windows Mini PC

Create `spread_monitor/.env` on your mini PC:

```bash
DATABASE_URL=postgresql://postgres:PASSWORD@db.PROJECT.supabase.co:5432/postgres
```

### 8.2 Install Dependencies

```powershell
cd spread_monitor
pip install -r requirements.txt
pip install python-dotenv
```

### 8.3 Update Collector to Load Environment Variables

Add to top of `collector.py`:

```python
from dotenv import load_dotenv
load_dotenv()
```

### 8.4 Create Windows Service (Optional)

For reliable 24/7 operation, create a Windows service using NSSM:

1. Download NSSM: https://nssm.cc/download
2. Install as service:

```powershell
# Run PowerShell as Administrator
nssm install SpreadCollector "C:\Python310\python.exe" "C:\path\to\spread_monitor\collector.py"
nssm set SpreadCollector AppDirectory "C:\path\to\spread_monitor"
nssm set SpreadCollector DisplayName "MT5 Spread Collector"
nssm set SpreadCollector Start SERVICE_AUTO_START
nssm start SpreadCollector
```

### 8.5 Alternative: Task Scheduler

1. Open Task Scheduler
2. Create Basic Task: "Spread Collector"
3. Trigger: At startup
4. Action: Start a program
   - Program: `python.exe`
   - Arguments: `collector.py`
   - Start in: `C:\path\to\spread_monitor`
5. Check "Run whether user is logged on or not"

---

## 9. Ad Integration (Google AdSense)

### 9.1 Apply for AdSense

1. Go to https://adsense.google.com
2. Sign up with your Google account
3. Add your site URL
4. Wait for approval (can take 2-14 days)

**Tips for approval:**
- Have at least 10-15 pages of content
- Add Privacy Policy and Terms pages
- Site should be live for at least 2-3 weeks
- Have some organic traffic

### 9.2 Add Ad Slots to Templates

Update `spread_monitor/templates/base.html`:

```html
<!DOCTYPE html>
<html lang="en" data-bs-theme="light">
<head>
    <!-- ... existing head content ... -->

    <!-- Google AdSense -->
    <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-XXXXXXXXXXXXXXXX"
         crossorigin="anonymous"></script>

    <!-- Cookie Consent CSS -->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/cookieconsent@3/build/cookieconsent.min.css" />
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
        <!-- ... existing navbar ... -->
    </nav>

    <!-- Top Banner Ad -->
    <div class="container mt-3">
        <div class="ad-container text-center">
            <ins class="adsbygoogle"
                 style="display:block"
                 data-ad-client="ca-pub-XXXXXXXXXXXXXXXX"
                 data-ad-slot="XXXXXXXXXX"
                 data-ad-format="horizontal"
                 data-full-width-responsive="true"></ins>
            <script>(adsbygoogle = window.adsbygoogle || []).push({});</script>
        </div>
    </div>

    <main class="container mt-4">
        {% block content %}{% endblock %}
    </main>

    <!-- Bottom Banner Ad -->
    <div class="container mb-4">
        <div class="ad-container text-center">
            <ins class="adsbygoogle"
                 style="display:block"
                 data-ad-client="ca-pub-XXXXXXXXXXXXXXXX"
                 data-ad-slot="XXXXXXXXXX"
                 data-ad-format="horizontal"
                 data-full-width-responsive="true"></ins>
            <script>(adsbygoogle = window.adsbygoogle || []).push({});</script>
        </div>
    </div>

    <footer class="container mt-5 mb-3">
        <hr>
        <div class="row">
            <div class="col-md-6">
                <p class="text-muted small">MT5 Spread Monitor - Comparing spreads across brokers</p>
            </div>
            <div class="col-md-6 text-md-end">
                <a href="/privacy" class="text-muted small me-3">Privacy Policy</a>
                <a href="/terms" class="text-muted small">Terms of Service</a>
            </div>
        </div>
    </footer>

    <!-- Cookie Consent -->
    <script src="https://cdn.jsdelivr.net/npm/cookieconsent@3/build/cookieconsent.min.js"></script>
    <script>
        window.cookieconsent.initialise({
            palette: {
                popup: { background: "#212529" },
                button: { background: "#0d6efd" }
            },
            theme: "classic",
            content: {
                message: "This website uses cookies to ensure you get the best experience and to show relevant ads.",
                link: "Learn more",
                href: "/privacy"
            }
        });
    </script>

    <!-- ... existing scripts ... -->
</body>
</html>
```

### 9.3 Add Responsive Ad Styles

Add to your CSS:

```css
.ad-container {
    min-height: 90px;
    margin: 1rem 0;
}

@media (max-width: 768px) {
    .ad-container {
        min-height: 50px;
    }
}

/* Hide ads for print */
@media print {
    .ad-container {
        display: none;
    }
}
```

### 9.4 Ad Placement Strategy

| Location | Ad Type | Expected Revenue |
|----------|---------|-----------------|
| Header (below nav) | Horizontal banner | High visibility |
| Between content sections | In-article | Good engagement |
| Sidebar (desktop only) | Vertical banner | Moderate |
| Footer | Horizontal banner | Lower but non-intrusive |

---

## 10. Legal Pages

### 10.1 Create Privacy Policy Page

Create `spread_monitor/templates/privacy.html`:

```html
{% extends "base.html" %}

{% block title %}Privacy Policy - Spread Monitor{% endblock %}

{% block content %}
<div class="row">
    <div class="col-lg-8 mx-auto">
        <h1 class="mb-4">Privacy Policy</h1>
        <p class="text-muted">Last updated: {{ current_date }}</p>

        <h2>Introduction</h2>
        <p>Welcome to MT5 Spread Monitor ("we," "our," or "us"). This Privacy Policy explains how we collect, use, and protect information when you use our website.</p>

        <h2>Information We Collect</h2>
        <h3>Automatically Collected Information</h3>
        <ul>
            <li><strong>Usage Data:</strong> Pages visited, time spent, referral source</li>
            <li><strong>Device Information:</strong> Browser type, operating system, screen resolution</li>
            <li><strong>IP Address:</strong> For analytics and security purposes</li>
        </ul>

        <h3>Cookies</h3>
        <p>We use cookies for:</p>
        <ul>
            <li><strong>Essential cookies:</strong> Theme preference (dark/light mode)</li>
            <li><strong>Analytics cookies:</strong> Google Analytics to understand usage patterns</li>
            <li><strong>Advertising cookies:</strong> Google AdSense to show relevant ads</li>
        </ul>

        <h2>Third-Party Services</h2>
        <h3>Google Analytics</h3>
        <p>We use Google Analytics to analyze website traffic. Google may collect and process data according to their <a href="https://policies.google.com/privacy" target="_blank">Privacy Policy</a>.</p>

        <h3>Google AdSense</h3>
        <p>We display advertisements through Google AdSense. Google uses cookies to serve ads based on your visits to this and other websites. You can opt out of personalized advertising at <a href="https://www.google.com/settings/ads" target="_blank">Google Ads Settings</a>.</p>

        <h2>Data Retention</h2>
        <p>We retain spread data for up to 90 days for historical analysis. No personal user data is stored.</p>

        <h2>Your Rights</h2>
        <p>You can:</p>
        <ul>
            <li>Disable cookies in your browser settings</li>
            <li>Opt out of Google personalized ads</li>
            <li>Use browser extensions to block tracking</li>
        </ul>

        <h2>Contact Us</h2>
        <p>For privacy-related questions, contact us at: [your-email@example.com]</p>

        <h2>Changes to This Policy</h2>
        <p>We may update this Privacy Policy from time to time. Changes will be posted on this page with an updated revision date.</p>
    </div>
</div>
{% endblock %}
```

### 10.2 Create Terms of Service Page

Create `spread_monitor/templates/terms.html`:

```html
{% extends "base.html" %}

{% block title %}Terms of Service - Spread Monitor{% endblock %}

{% block content %}
<div class="row">
    <div class="col-lg-8 mx-auto">
        <h1 class="mb-4">Terms of Service</h1>
        <p class="text-muted">Last updated: {{ current_date }}</p>

        <h2>Acceptance of Terms</h2>
        <p>By accessing and using MT5 Spread Monitor, you agree to be bound by these Terms of Service.</p>

        <h2>Service Description</h2>
        <p>MT5 Spread Monitor provides real-time and historical spread data comparison across multiple forex brokers. The data is collected from demo accounts and is provided for informational purposes only.</p>

        <h2>Disclaimer</h2>
        <div class="alert alert-warning">
            <strong>Important:</strong> This service is for informational purposes only and does not constitute financial advice.
        </div>
        <ul>
            <li>Spread data is collected from demo accounts and may differ from live trading conditions</li>
            <li>We do not guarantee the accuracy, completeness, or timeliness of the data</li>
            <li>Past spread performance does not guarantee future results</li>
            <li>Trading forex involves significant risk of loss</li>
        </ul>

        <h2>No Financial Advice</h2>
        <p>Nothing on this website constitutes financial, investment, or trading advice. You should consult with qualified professionals before making any trading decisions.</p>

        <h2>Intellectual Property</h2>
        <p>The website design, code, and original content are protected by copyright. You may not reproduce, distribute, or create derivative works without permission.</p>

        <h2>Third-Party Links</h2>
        <p>We may display links to broker websites. We are not responsible for the content or practices of these third-party sites.</p>

        <h2>Limitation of Liability</h2>
        <p>To the maximum extent permitted by law, we shall not be liable for any indirect, incidental, special, consequential, or punitive damages resulting from your use of this service.</p>

        <h2>Modifications</h2>
        <p>We reserve the right to modify or discontinue the service at any time without notice.</p>

        <h2>Governing Law</h2>
        <p>These terms shall be governed by the laws of [Your Jurisdiction].</p>

        <h2>Contact</h2>
        <p>For questions about these terms, contact us at: [your-email@example.com]</p>
    </div>
</div>
{% endblock %}
```

### 10.3 Add Routes for Legal Pages

Add to `app.py`:

```python
from datetime import date

@app.route('/privacy')
def privacy():
    return render_template('privacy.html', current_date=date.today().strftime('%B %d, %Y'))

@app.route('/terms')
def terms():
    return render_template('terms.html', current_date=date.today().strftime('%B %d, %Y'))
```

---

## 11. SEO Optimization

### 11.1 Update Base Template Meta Tags

Add to `<head>` in `base.html`:

```html
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">

    <!-- SEO Meta Tags -->
    <meta name="description" content="{% block meta_description %}Compare real-time forex spreads across 6+ brokers. Free tool for traders to find the lowest spreads on XAUUSD and other instruments.{% endblock %}">
    <meta name="keywords" content="forex spreads, MT5 spreads, broker comparison, XAUUSD spread, trading costs, forex broker">
    <meta name="author" content="MT5 Spread Monitor">
    <meta name="robots" content="index, follow">

    <!-- Open Graph / Facebook -->
    <meta property="og:type" content="website">
    <meta property="og:url" content="{{ request.url }}">
    <meta property="og:title" content="{% block og_title %}{{ self.title() }}{% endblock %}">
    <meta property="og:description" content="{% block og_description %}Compare real-time forex spreads across multiple brokers.{% endblock %}">
    <meta property="og:image" content="{{ url_for('static', filename='images/og-image.png', _external=True) }}">

    <!-- Twitter -->
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{{ self.title() }}">
    <meta name="twitter:description" content="{{ self.meta_description() }}">

    <!-- Canonical URL -->
    <link rel="canonical" href="{{ request.url }}">

    <title>{% block title %}Spread Monitor{% endblock %}</title>

    <!-- ... rest of head ... -->
</head>
```

### 11.2 Create robots.txt

Create `spread_monitor/static/robots.txt`:

```
User-agent: *
Allow: /

Sitemap: https://your-domain.com/sitemap.xml

# Disallow API endpoints from being indexed
Disallow: /api/
```

Serve it in `app.py`:

```python
@app.route('/robots.txt')
def robots():
    return send_from_directory('static', 'robots.txt')
```

### 11.3 Create Dynamic Sitemap

Add to `app.py`:

```python
from flask import Response

@app.route('/sitemap.xml')
def sitemap():
    """Generate sitemap.xml dynamically."""
    pages = [
        {'loc': '/', 'priority': '1.0', 'changefreq': 'always'},
        {'loc': '/history', 'priority': '0.8', 'changefreq': 'daily'},
        {'loc': '/stats', 'priority': '0.8', 'changefreq': 'daily'},
        {'loc': '/sessions', 'priority': '0.7', 'changefreq': 'daily'},
        {'loc': '/costs', 'priority': '0.8', 'changefreq': 'daily'},
        {'loc': '/privacy', 'priority': '0.3', 'changefreq': 'monthly'},
        {'loc': '/terms', 'priority': '0.3', 'changefreq': 'monthly'},
    ]

    base_url = request.url_root.rstrip('/')

    xml = ['<?xml version="1.0" encoding="UTF-8"?>']
    xml.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')

    for page in pages:
        xml.append('  <url>')
        xml.append(f'    <loc>{base_url}{page["loc"]}</loc>')
        xml.append(f'    <changefreq>{page["changefreq"]}</changefreq>')
        xml.append(f'    <priority>{page["priority"]}</priority>')
        xml.append('  </url>')

    xml.append('</urlset>')

    return Response('\n'.join(xml), mimetype='application/xml')
```

### 11.4 Add Structured Data (JSON-LD)

Add to `base.html` before closing `</head>`:

```html
<!-- Structured Data -->
<script type="application/ld+json">
{
    "@context": "https://schema.org",
    "@type": "WebApplication",
    "name": "MT5 Spread Monitor",
    "description": "Compare real-time forex spreads across multiple MetaTrader 5 brokers",
    "url": "{{ request.url_root }}",
    "applicationCategory": "FinanceApplication",
    "operatingSystem": "Web",
    "offers": {
        "@type": "Offer",
        "price": "0",
        "priceCurrency": "USD"
    }
}
</script>
```

### 11.5 Submit to Search Engines

1. **Google Search Console**: https://search.google.com/search-console
   - Add property
   - Verify ownership (HTML file or DNS)
   - Submit sitemap

2. **Bing Webmaster Tools**: https://www.bing.com/webmasters
   - Similar process to Google

---

## 12. Monitoring & Maintenance

### 12.1 Free Uptime Monitoring

Sign up for free monitoring at:

1. **UptimeRobot** (https://uptimerobot.com) - 50 free monitors
   - Add HTTP monitor for your Railway URL
   - Set 5-minute check interval
   - Enable email alerts

2. **Healthchecks.io** (https://healthchecks.io) - For collector heartbeat
   - Create a check
   - Add ping to collector.py:

   ```python
   import requests

   HEALTHCHECK_URL = os.environ.get('HEALTHCHECK_URL')

   def ping_healthcheck():
       if HEALTHCHECK_URL:
           try:
               requests.get(HEALTHCHECK_URL, timeout=10)
           except:
               pass

   # Call after each successful collection
   ```

### 12.2 Error Tracking with Sentry (Free Tier)

1. Sign up at https://sentry.io
2. Create a Flask project
3. Install: `pip install sentry-sdk[flask]`
4. Add to `app.py`:

```python
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration

if os.environ.get('SENTRY_DSN'):
    sentry_sdk.init(
        dsn=os.environ.get('SENTRY_DSN'),
        integrations=[FlaskIntegration()],
        traces_sample_rate=0.1
    )
```

### 12.3 Database Maintenance

Create a weekly cleanup job. Add to `app.py` or a separate script:

```python
from apscheduler.schedulers.background import BackgroundScheduler
from utils.db import cleanup_old_data

def scheduled_cleanup():
    """Delete data older than 90 days."""
    deleted = cleanup_old_data(days=90)
    print(f"Cleaned up {deleted} old records")

# Add to app startup
scheduler = BackgroundScheduler()
scheduler.add_job(scheduled_cleanup, 'cron', day_of_week='sun', hour=3)
scheduler.start()
```

### 12.4 Backup Strategy

Supabase provides automatic backups on paid plans. For free tier:

```python
# Run weekly to export data
import pandas as pd
from utils.db import get_engine

def backup_to_csv():
    engine = get_engine()
    df = pd.read_sql("SELECT * FROM spread_data", engine)
    df.to_csv(f"backup_{date.today()}.csv", index=False)
```

---

## 13. Scaling & Cost Optimization

### 13.1 When to Upgrade

| Metric | Free Tier Limit | Action |
|--------|-----------------|--------|
| Database rows | 50,000 | Enable data retention (90 days) |
| Database size | 500MB | Upgrade Supabase ($25/mo) or migrate to VPS |
| Railway hours | ~500/month | Upgrade to Hobby ($5/mo) |
| Monthly visitors | ~10,000 | Should be fine, enable Cloudflare caching |

### 13.2 Cost-Saving Migrations

**Option A: Self-hosted VPS (if you outgrow free tiers)**

| Provider | Specs | Cost |
|----------|-------|------|
| Hetzner | 2GB RAM, 20GB SSD | €4/month |
| DigitalOcean | 1GB RAM, 25GB SSD | $6/month |
| Vultr | 1GB RAM, 25GB SSD | $5/month |

Setup with Docker:

```yaml
# docker-compose.yml
version: '3.8'
services:
  web:
    build: ./spread_monitor
    ports:
      - "5000:5000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/spreads
    depends_on:
      - db

  db:
    image: postgres:15
    volumes:
      - pgdata:/var/lib/postgresql/data
    environment:
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=spreads

volumes:
  pgdata:
```

### 13.3 Performance Optimization

1. **Enable Cloudflare caching** for static assets and historical API responses
2. **Add Redis caching** for frequently accessed data (optional)
3. **Optimize database queries** - add indexes for common query patterns
4. **Use CDN for static files** - Cloudflare handles this automatically

### 13.4 Revenue Scaling

| Monthly Pageviews | Ad Network | Expected RPM | Monthly Revenue |
|-------------------|------------|--------------|-----------------|
| 1,000 | AdSense | $1-2 | $1-2 |
| 10,000 | AdSense | $1-3 | $10-30 |
| 50,000 | Ezoic | $5-15 | $250-750 |
| 100,000+ | Mediavine | $15-30 | $1,500-3,000 |

**Additional Revenue Streams:**
- Broker affiliate links (CPA: $200-500 per signup)
- Premium API access (charge for higher rate limits)
- Sponsored broker listings

---

## Quick Start Checklist

- [ ] Create accounts: GitHub, Supabase, Railway, Cloudflare, AdSense
- [ ] Set up Supabase database with schema
- [ ] Create `utils/db.py` module
- [ ] Update `collector.py` to use database
- [ ] Update `app.py` to use database
- [ ] Create `wsgi.py` and `Procfile`
- [ ] Deploy to Railway
- [ ] Configure Cloudflare
- [ ] Set up collector on Windows mini PC
- [ ] Add legal pages (Privacy, Terms)
- [ ] Add AdSense code (after approval)
- [ ] Submit to Google Search Console
- [ ] Set up UptimeRobot monitoring

---

## Support Resources

- **Supabase Docs**: https://supabase.com/docs
- **Railway Docs**: https://docs.railway.app
- **Flask Deployment**: https://flask.palletsprojects.com/en/3.0.x/deploying/
- **AdSense Help**: https://support.google.com/adsense
- **Cloudflare Docs**: https://developers.cloudflare.com

---

*Good luck with your deployment! Feel free to ask Claude Code for help implementing any of these steps.*
