# Spread Monitor Tool - Technical Specification

## Overview
A Python-based tool to monitor and compare real-time spreads across multiple MT5 brokers (Pepperstone, Fusion Markets, FPMarkets) for XAUUSD and other instruments.

---

## Objectives
1. Collect live spread data from 3 MT5 demo accounts simultaneously
2. Store data in structured format for analysis
3. Visualize spread comparisons via web dashboard
4. Identify optimal trading times per broker

---

## Phase 1: Data Collector

### Technical Requirements
- Python 3.10+
- MetaTrader5 package
- Pandas for data handling
- Schedule/APScheduler for timing

### MT5 Connection
```
Broker credentials stored in config.json:
{
  "brokers": [
    {
      "name": "Pepperstone",
      "server": "Pepperstone-Demo",
      "login": 12345678,
      "password": "xxxx",
      "path": "C:/Program Files/Pepperstone MetaTrader 5/terminal64.exe"
    },
    {
      "name": "Fusion",
      "server": "FusionMarkets-Demo",
      "login": 12345678,
      "password": "xxxx",
      "path": "C:/Program Files/Fusion Markets MetaTrader 5/terminal64.exe"
    },
    {
      "name": "FPMarkets",
      "server": "FPMarkets-Demo",
      "login": 12345678,
      "password": "xxxx",
      "path": "C:/Program Files/FP Markets MetaTrader 5/terminal64.exe"
    }
  ]
}
```

### Data Points to Capture
| Field | Type | Description |
|-------|------|-------------|
| timestamp | datetime | UTC time of capture |
| broker | string | Broker name |
| symbol | string | e.g., XAUUSD |
| bid | float | Bid price |
| ask | float | Ask price |
| spread | float | Ask - Bid |
| spread_points | int | Spread in points |
| session | string | Sydney/London/NewYork/Overlap |
| day_of_week | string | Monday-Friday |

### Collection Frequency
- Default: Every 5 minutes
- Configurable via config.json
- Option for 1-minute during high volatility

### Data Storage
- Primary: CSV file (daily rotation)
- Format: `spread_data_YYYY-MM-DD.csv`
- Location: `./data/` directory

### Session Detection Logic
```
UTC Times:
- Sydney:    21:00 - 06:00
- London:    07:00 - 16:00
- New York:  12:00 - 21:00
- Overlap:   12:00 - 16:00 (London/NY)
```

### Error Handling
- Retry connection 3 times on failure
- Log errors to `./logs/error.log`
- Continue collecting from other brokers if one fails
- Graceful shutdown on keyboard interrupt

---

## Phase 2: Visualization Dashboard

### Technical Requirements
- Flask web framework
- Plotly for interactive charts
- Bootstrap 5 for styling
- Pandas for data aggregation

### Dashboard Pages

#### 1. Home / Live View
- Current spread for each broker (auto-refresh every 60s)
- Color coding: Green (lowest), Yellow (mid), Red (highest)
- Last updated timestamp

#### 2. Historical Comparison
- Date range selector
- Line chart: Spread over time (all 3 brokers overlaid)
- Toggle brokers on/off

#### 3. Statistical Analysis
- Average spread per broker
- Min/Max spread per broker
- Standard deviation
- Box plot comparison

#### 4. Session Analysis
- Heatmap: Broker vs Session (avg spread)
- Bar chart: Best broker per session
- Recommendation engine: "Trade XAUUSD with [Broker] during [Session]"

#### 5. Histogram
- Spread distribution per broker
- Overlay option
- Bin size configurable

### API Endpoints
```
GET /api/live          - Current spreads
GET /api/history       - Historical data (with date params)
GET /api/stats         - Aggregated statistics
GET /api/sessions      - Session-based analysis
```

---

## File Structure
```
spread_monitor/
├── config.json
├── collector.py          # Main data collection script
├── app.py                # Flask application
├── requirements.txt
├── data/
│   └── spread_data_YYYY-MM-DD.csv
├── logs/
│   └── error.log
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── history.html
│   ├── stats.html
│   └── sessions.html
├── static/
│   ├── css/
│   └── js/
└── utils/
    ├── mt5_connector.py  # MT5 connection handling
    ├── session_utils.py  # Session detection
    └── data_utils.py     # Data processing
```

---

## Configuration Options (config.json)
```json
{
  "collection_interval_minutes": 5,
  "symbols": ["XAUUSD", "EURUSD"],
  "data_directory": "./data",
  "log_directory": "./logs",
  "flask_port": 5000,
  "auto_refresh_seconds": 60,
  "brokers": [...]
}
```

---

## Running the Tool

### Data Collector
```bash
python collector.py
```
- Runs continuously
- Ctrl+C to stop gracefully

### Web Dashboard
```bash
python app.py
```
- Access at http://localhost:5000

---

## Future Enhancements (Out of Scope for MVP)
- Telegram/Discord alerts for spread spikes
- News event calendar integration
- Multi-symbol support
- Database storage (SQLite/PostgreSQL)
- Docker deployment
- Historical data export (Excel)
