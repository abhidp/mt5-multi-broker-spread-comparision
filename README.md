# MT5 Multi-Broker Spread Comparison Tool

A Python-based tool to monitor, collect, and compare real-time spreads and trading costs across multiple MetaTrader 5 (MT5) brokers. Helps traders identify the best broker for their instruments by analyzing spread variations and total trading costs.

## Features

### Data Collection
- **Automated spread monitoring** across 6+ brokers simultaneously
- **Configurable collection intervals** (default: 1 minute)
- **Trading session tagging** (Sydney, London, Overlap, New York)
- **CSV storage** with daily file rotation
- **Market hours detection** (skips weekends)

### Web Dashboard

#### Live View (`/`)
- Real-time spread display for all brokers
- Tile and Table view modes
- Auto-refresh every 60 seconds
- Color-coded spread indicators (lowest/highest)
- Broker logos

#### History (`/history`)
- Interactive spread charts over time
- Date range filtering
- Toggle between Points and Price view
- Consistent broker color coding

#### Statistics (`/stats`)
- Aggregated statistics (avg/min/max/std dev)
- Sortable data table
- Box plot and histogram visualizations
- **Excel export**

#### Sessions (`/sessions`)
- Trading session analysis with heatmap
- Tightest spreads by session with country flags
- Session comparison bar chart
- Detailed statistics table

#### Trading Costs (`/costs`)
- **Total cost comparison** (spread + commission)
- Commission-free symbol support (e.g., Pepperstone metals/indices)
- Lot size selector (0.01 - 10.0)
- Cost breakdown stacked bar chart
- **Potential savings calculator** (per lot, monthly, yearly)
- **Excel export**
- All costs in AUD for Australian accounts

## Supported Brokers

| Broker | Account Type | Commission (AUD) | XAUUSD Commission |
|--------|-------------|------------------|-------------------|
| Pepperstone | Razor | A$7.00/lot | FREE |
| FusionMarkets | Zero | A$4.50/lot | A$4.50/lot |
| ThinkMarkets | ThinkZero | A$7.00/lot | A$7.00/lot |
| ICMarkets | Raw | A$9.00/lot | A$9.00/lot |
| VantageMarkets | Raw | A$5.00/lot | FREE |
| FPMarkets | Raw | A$7.00/lot | A$7.00/lot |

## Installation

### Prerequisites
- Windows OS (MT5 Python package requirement)
- Python 3.10+
- MetaTrader 5 terminal installed

### Setup

1. Clone the repository:
```bash
git clone https://github.com/abhidp/mt5-multi-broker-spread-comparision.git
cd mt5-multi-broker-spread-comparision
```

2. Create virtual environment:
```bash
python -m venv venv
venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r spread_monitor/requirements.txt
```

4. Configure brokers:
```bash
cp spread_monitor/config-example.json spread_monitor/config.json
# Edit config.json with your broker credentials
```

## Configuration

Edit `spread_monitor/config.json`:

```json
{
  "collection_interval_minutes": 1,
  "symbols": ["XAUUSD"],
  "brokers": [
    {
      "name": "Broker Name",
      "server": "BrokerServer-Demo",
      "login": 12345678,
      "password": "your_password",
      "path": "C:/Program Files/MT5 Terminal/terminal64.exe",
      "symbol_suffix": ".a",
      "website": "broker.com",
      "commission_per_lot": 7.00,
      "commission_currency": "AUD",
      "commission_free_symbols": ["XAU", "XAG"]
    }
  ]
}
```

### Configuration Fields

| Field | Description |
|-------|-------------|
| `name` | Display name for the broker |
| `server` | MT5 server name |
| `login` | Account number |
| `password` | Account password |
| `path` | Path to MT5 terminal executable |
| `symbol_suffix` | Broker-specific symbol suffix (e.g., ".a", ".r", "+") |
| `website` | Broker website (for logo fetching) |
| `commission_per_lot` | Round-trip commission per standard lot |
| `commission_currency` | Commission currency (AUD/USD) |
| `commission_free_symbols` | Array of symbol prefixes exempt from commission |

## Usage

### Start Data Collection

```bash
cd spread_monitor
python collector.py
```

Options:
- `--once` - Run single collection and exit
- `--config path/to/config.json` - Use custom config file

### Start Web Dashboard

```bash
cd spread_monitor
python app.py
```

Access at: http://localhost:5000

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/config` | Collection interval and symbols |
| `GET /api/brokers` | Broker metadata (names, logos) |
| `GET /api/live` | Current spreads for all brokers |
| `GET /api/history?start=YYYY-MM-DD&end=YYYY-MM-DD&symbol=XAUUSD` | Historical data |
| `GET /api/stats?start=YYYY-MM-DD&end=YYYY-MM-DD&symbol=XAUUSD` | Aggregated statistics |
| `GET /api/sessions?start=YYYY-MM-DD&end=YYYY-MM-DD&symbol=XAUUSD` | Session-based analysis |
| `GET /api/trading-costs?start=YYYY-MM-DD&end=YYYY-MM-DD&symbol=XAUUSD&lot_size=1.0` | Trading costs comparison |
| `GET /api/commissions` | Broker commission data |

## Project Structure

```
spread_monitor/
├── app.py                    # Flask web dashboard
├── collector.py              # Data collection script
├── config.json               # Broker configuration (gitignored)
├── config-example.json       # Configuration template
├── requirements.txt          # Python dependencies
├── data/                     # CSV data storage
├── logs/                     # Log files
├── templates/                # HTML templates
│   ├── base.html            # Base template with navigation
│   ├── index.html           # Live view
│   ├── history.html         # Historical charts
│   ├── stats.html           # Statistics
│   ├── sessions.html        # Session analysis
│   └── costs.html           # Trading costs calculator
└── utils/
    ├── mt5_connector.py     # MT5 connection handling
    ├── session_utils.py     # Trading session detection
    ├── data_utils.py        # CSV operations
    └── cost_calculator.py   # Trading cost calculations
```

## Tech Stack

- **Backend**: Python 3.10+, Flask
- **Data**: Pandas, NumPy
- **MT5 Integration**: MetaTrader5 Python package
- **Frontend**: Bootstrap 5, Plotly.js
- **Scheduling**: APScheduler
- **Export**: SheetJS (xlsx)

## Trading Sessions (UTC)

| Session | Time (UTC) | Flag |
|---------|------------|------|
| Sydney | 21:00 - 06:00 | 🇦🇺 |
| London | 07:00 - 16:00 | 🇬🇧 |
| Overlap | 12:00 - 16:00 | 🇬🇧🇺🇸 |
| New York | 12:00 - 21:00 | 🇺🇸 |

## Notes

- MT5 only allows one terminal connection at a time, so brokers are connected sequentially
- Symbol availability and suffixes vary by broker
- Commission-free symbols are broker-specific (check your broker's fee schedule)
- Point values for AUD accounts assume AUDUSD rate of ~0.645


# Deployment on Windows Server

- Terminal - Run as Administrator to allow firewall rule creation.
`netsh advfirewall firewall add rule name="Flask App" dir=in action=allow protocol=tcp localport=5000`

- Access the app at `http://<tailscale-ip>:5000`


## License

MIT
