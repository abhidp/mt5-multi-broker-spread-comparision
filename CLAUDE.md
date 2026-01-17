# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MT5 Multi-Broker Spread Comparison Tool - A Python application that monitors and compares real-time forex spreads and trading costs across multiple MetaTrader 5 (MT5) brokers. Collects spread data from demo accounts, stores in CSV files, and provides a Flask web dashboard for visualization and analysis.

**Platform**: Windows only (MT5 Python package limitation)

## Commands

### Setup
```bash
cd spread_monitor
pip install -r requirements.txt
cp config-example.json config.json  # Then edit with broker credentials
```

### Run Data Collector
```bash
cd spread_monitor
python collector.py           # Continuous collection (scheduled)
python collector.py --once    # Single collection cycle
python collector.py --config path/to/config.json  # Custom config
```

### Run Web Dashboard
```bash
cd spread_monitor
python app.py                 # Access at http://localhost:5000
```

### Windows Server Deployment
```bash
# Run terminal as Administrator
netsh advfirewall firewall add rule name="Flask App" dir=in action=allow protocol=tcp localport=5000
```

## Architecture

### Data Flow
```
Scheduler → For each broker (sequential, MT5 limitation):
  ├── Connect to MT5 terminal
  ├── Fetch tick data for symbols
  ├── Calculate spreads in points
  └── Disconnect
     → Append to daily CSV (spread_data_YYYY-MM-DD.csv)
        → Flask API serves data to frontend
```

### Key Components

| File | Purpose |
|------|---------|
| `spread_monitor/collector.py` | Data collection daemon with APScheduler |
| `spread_monitor/app.py` | Flask web dashboard and API |
| `spread_monitor/utils/mt5_connector.py` | MT5 terminal connections, retry logic, symbol suffix handling |
| `spread_monitor/utils/data_utils.py` | CSV operations, data loading/filtering |
| `spread_monitor/utils/session_utils.py` | Trading session detection (Sydney/London/Overlap/NewYork) |
| `spread_monitor/utils/cost_calculator.py` | Spread costs, commission calculations |

### Frontend Templates
All in `spread_monitor/templates/`:
- `base.html` - Navigation, dark mode toggle, Plotly theme helper
- `index.html` - Live spreads (tile/table views)
- `history.html` - Historical line charts
- `stats.html` - Statistics with box plots, histograms
- `sessions.html` - Session heatmap analysis
- `costs.html` - Trading cost calculator

## Key Constraints

- **Single MT5 Connection**: MetaTrader5 Python package can only connect to one terminal at a time. Collector disconnects from each broker before connecting to the next.
- **Symbol Suffixes**: Different brokers append different suffixes (e.g., `.a`, `.r`, `+`). Configured per-broker in `config.json`, normalized in stored data.
- **Market Hours**: Collector skips weekends (Friday 21:00 UTC to Sunday 21:00 UTC).

## Configuration

Edit `spread_monitor/config.json` (gitignored). Key fields per broker:
- `symbol_suffix`: Broker-specific suffix for symbols
- `commission_per_lot`: Round-trip commission in AUD
- `commission_free_symbols`: Symbol prefixes exempt from commission (e.g., `["XAU", "XAG"]`)

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `/api/live` | Current spreads |
| `/api/history?start=&end=&symbol=` | Historical data |
| `/api/stats?start=&end=&symbol=` | Aggregated statistics |
| `/api/sessions?start=&end=&symbol=` | Session-based analysis |
| `/api/trading-costs?start=&end=&symbol=&lot_size=` | Cost comparison |
| `/api/commissions` | Broker commission data |
| `/api/brokers` | Broker metadata (names, logos) |

## Trading Sessions (UTC)

- Sydney: 21:00-06:00
- London: 07:00-16:00
- New York: 12:00-21:00
- Overlap: 12:00-16:00

## Frontend Patterns

- Dark mode: Uses Bootstrap 5.3 `data-bs-theme` attribute, persisted to localStorage
- Charts: Plotly.js with `getPlotlyThemeLayout()` helper in base.html for theme-aware colors
- Broker colors: Consistent color mapping in `BROKER_COLORS` object in base.html
- CSS variables: `--hover-bg`, `--table-header-bg`, `--text-muted-custom` for theme support
