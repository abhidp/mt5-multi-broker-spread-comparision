# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

MT5 Multi-Broker Spread Comparison Tool - A Python application that monitors and compares real-time forex spreads across multiple MetaTrader 5 (MT5) brokers. The project collects spread data from demo accounts, stores it in CSV files, and is designed for future visualization via a Flask dashboard.

**Current Status**: Phase 1 (Data Collection) is implemented. Phase 2 (Flask Dashboard) is planned but not yet developed.

## Development Setup

### Prerequisites
- Python 3.10+
- MetaTrader 5 terminals installed for each broker
- MT5 demo accounts configured

### Installation
```pwsh
# Navigate to the spread_monitor directory
cd spread_monitor

# Install dependencies
pip install -r requirements.txt

# Copy and configure broker settings
Copy-Item config-example.json config.json
# Edit config.json with your actual broker credentials
```

### Configuration
Edit `spread_monitor/config.json` with:
- Broker credentials (name, server, login, password, MT5 terminal path)
- `symbol_suffix`: Each broker may append different suffixes to symbols (e.g., ".a", ".r", "x")
- Collection interval in minutes
- Symbols to monitor (default: XAUUSD)

## Running the Application

### Data Collection
```pwsh
# Run continuously (scheduled collection every N minutes)
python spread_monitor/collector.py

# Run once and exit
python spread_monitor/collector.py --once

# Specify custom config file
python spread_monitor/collector.py --config path/to/config.json
```

The collector:
- Connects sequentially to each broker's MT5 terminal
- Collects bid/ask prices and calculates spreads
- Tags data with trading session (Sydney/London/NewYork/Overlap)
- Saves to daily CSV files in `spread_monitor/data/`
- Logs to `spread_monitor/logs/`

### Testing Connection
To test a single broker connection without full scheduling:
```pwsh
python spread_monitor/collector.py --once
```

## Architecture

### Core Components

**collector.py**
- Main entry point for data collection
- Uses APScheduler for interval-based collection
- Handles graceful shutdown via signal handlers
- Implements market hours checking (skips weekends)

**utils/mt5_connector.py**
- `MT5Connector`: Handles all MT5 terminal connections
- `BrokerConfig`: Dataclass for broker configuration
- `SpreadData`: Dataclass for collected spread data
- Manages connection retries and broker-specific symbol suffixes
- Connects to one broker at a time (MT5 Python package limitation)

**utils/session_utils.py**
- Trading session detection based on UTC time
- Sessions: Sydney (21:00-06:00), London (07:00-16:00), NewYork (12:00-21:00), Overlap (12:00-16:00)
- Market hours validation (excludes weekends)

**utils/data_utils.py**
- CSV file operations with daily rotation
- File naming: `spread_data_YYYY-MM-DD.csv`
- Functions for loading historical data and getting latest spreads

### Data Flow
1. Scheduler triggers collection at configured intervals
2. For each broker in config:
   - Connect to broker's MT5 terminal
   - Fetch tick data for each symbol
   - Calculate spread and convert to points
   - Disconnect (required before connecting to next broker)
3. Append all collected data to today's CSV file
4. Session and day-of-week tags are added during CSV serialization

### Key Constraints
- **Single MT5 Connection**: The MetaTrader5 Python package can only connect to one terminal at a time. The connector must disconnect from one broker before connecting to another.
- **Symbol Suffixes**: Different brokers append different suffixes to symbol names (e.g., XAUUSD.a, XAUUSD.r). These are stored in config and normalized in the data.
- **Windows Only**: MetaTrader5 Python package only works on Windows.

## Data Storage

### CSV Format
Location: `spread_monitor/data/spread_data_YYYY-MM-DD.csv`

Columns:
- `timestamp`: UTC timestamp (YYYY-MM-DD HH:MM:SS)
- `broker`: Broker name
- `symbol`: Base symbol (normalized, without suffix)
- `bid`: Bid price
- `ask`: Ask price
- `spread`: Ask - Bid (price difference)
- `spread_points`: Spread in points (spread / point value)
- `session`: Trading session tag
- `day_of_week`: Day name (Monday-Friday)

### Logs
- `spread_monitor/logs/collector.log`: All log messages (DEBUG level)
- `spread_monitor/logs/error.log`: Errors and warnings only

## Future Development (Phase 2)

The Flask dashboard (not yet implemented) should be created as `spread_monitor/app.py` with:
- Live view: Current spreads with auto-refresh
- Historical comparison: Line charts of spreads over time
- Statistical analysis: Avg/min/max spreads, box plots
- Session analysis: Heatmaps showing best broker per session
- API endpoints: `/api/live`, `/api/history`, `/api/stats`, `/api/sessions`

Templates should go in `spread_monitor/templates/` and static files in `spread_monitor/static/`.

## Common Issues

**Connection Failures**
- Verify MT5 terminal is installed at the path specified in config
- Ensure demo account credentials are correct
- Check that the broker's server name matches exactly
- Some brokers require the terminal to be opened manually once before API access works

**Symbol Not Found**
- Verify the symbol suffix for each broker
- Check symbol spelling in config (case-sensitive)
- Ensure symbol is available in broker's Market Watch

**No Data on Weekends**
- The collector checks market hours and skips collection when markets are closed (weekends)
- Forex market: Closed Friday 21:00 UTC to Sunday 21:00 UTC

## Documentation

- `spread_monitor_spec.md`: Full technical specification for the project
- `claude_code_prompt.md`: Original prompts used to build the tool
- `spread_monitor/config-example.json`: Template configuration file
