# Claude Code Prompt - Spread Monitor Tool

---

## Prompt to Copy-Paste:

---

Build a Python spread monitoring tool to compare real-time MT5 spreads across 3 brokers. Split into 2 phases.

## PHASE 1: Data Collector

Create a Python script that:

1. **Connects to 3 MT5 demo accounts simultaneously** (Pepperstone, Fusion Markets, FPMarkets)
   - Read broker credentials from `config.json`
   - Each broker has: name, server, login, password, terminal path

2. **Collects spread data every 5 minutes** (configurable)
   - Capture: timestamp (UTC), broker, symbol, bid, ask, spread, spread_points
   - Add session tag (Sydney/London/NewYork/Overlap) based on UTC time:
     - Sydney: 21:00-06:00
     - London: 07:00-16:00  
     - New York: 12:00-21:00
     - Overlap: 12:00-16:00
   - Add day_of_week field

3. **Saves to CSV** with daily file rotation (`spread_data_YYYY-MM-DD.csv`)

4. **Error handling**: retry 3 times on connection failure, log errors, continue if one broker fails

Create a sample `config.json` template with placeholder credentials.

## PHASE 2: Flask Dashboard

Create a Flask web app with:

1. **Live View page**: Current spread per broker, auto-refresh every 60s, color-coded (green=lowest, red=highest)

2. **History page**: Line chart with all 3 brokers overlaid, date range picker

3. **Stats page**: Table showing avg/min/max/stddev per broker, plus box plot

4. **Session Analysis page**: Heatmap (broker vs session), recommendation for best broker per session

Use Plotly for charts, Bootstrap 5 for styling.

## File Structure
```
spread_monitor/
├── config.json
├── collector.py
├── app.py
├── requirements.txt
├── data/
├── logs/
├── templates/
├── static/
└── utils/
    ├── mt5_connector.py
    ├── session_utils.py
    └── data_utils.py
```

Start with Phase 1. Once working, proceed to Phase 2.

---

## Alternative: Phased Prompts

If you prefer to build incrementally, use these separate prompts:

---

### Prompt 1A - Core Collector
```
Create a Python script using MetaTrader5 package that:
1. Reads broker credentials from config.json (name, server, login, password, path)
2. Connects to MT5 terminal
3. Fetches current bid/ask for XAUUSD
4. Calculates spread
5. Prints the values

Include a sample config.json with placeholder values.
```

---

### Prompt 1B - Multi-Broker + Scheduler
```
Extend the collector to:
1. Connect to 3 brokers from config.json sequentially
2. Run collection every 5 minutes using APScheduler
3. Save results to CSV with columns: timestamp, broker, symbol, bid, ask, spread, spread_points
4. Add session detection (Sydney/London/NewYork/Overlap) based on UTC time
5. Add error handling with retries and logging
```

---

### Prompt 2A - Basic Flask App
```
Create a Flask app that:
1. Reads CSV files from ./data directory
2. Shows a home page with current spread per broker (last row from today's CSV)
3. Auto-refreshes every 60 seconds
4. Color codes: green for lowest spread, red for highest
Use Bootstrap 5 for styling.
```

---

### Prompt 2B - Charts
```
Add to the Flask app:
1. /history page with Plotly line chart showing spread over time
2. All 3 brokers on same chart with different colors
3. Date range selector
4. /stats page with avg/min/max table and box plot
```

---

### Prompt 2C - Session Analysis
```
Add to the Flask app:
1. /sessions page with:
   - Heatmap: brokers (y-axis) vs sessions (x-axis), cell color = avg spread
   - Text recommendation: "Best broker for [session] is [broker] with avg spread [X]"
2. Add API endpoints: /api/live, /api/history, /api/stats
```

---

## Tips for Claude Code

1. Run Phase 1 first and test with one broker before adding all three
2. Keep MT5 terminal open while testing
3. Use demo accounts only
4. If connection issues occur, check terminal path in config.json
5. Test Flask app with sample CSV data before connecting live collector
