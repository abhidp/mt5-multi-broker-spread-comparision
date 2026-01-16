# Future Enhancement: Total Trading Costs Calculator

## Overview

Enhance the Spread Monitor to calculate and compare **total trading costs** across brokers, factoring in both spreads and commissions.

---

## Problem Statement

Currently, the app only compares spreads. However, the true cost of trading includes:
- **Spread cost** (variable, changes with market conditions)
- **Commission** (fixed per broker/account type)

Some brokers offer tight spreads but charge commissions (e.g., Razor/ECN accounts), while others have wider spreads but zero commission (e.g., Standard accounts). A fair comparison requires looking at the total cost.

---

## Formula

```
Total Trading Cost = Spread Cost + Commission Cost
```

Where:
- **Spread Cost** = Spread (in points) × Point Value × Lot Size
- **Commission Cost** = Commission per Lot × Lot Size

### Example Calculation (XAUUSD, 1 standard lot)

| Broker | Spread (pts) | Spread Cost | Commission | Total Cost |
|--------|-------------|-------------|------------|------------|
| Pepperstone Razor | 15 | $15.00 | $7.00 | **$22.00** |
| FusionMarkets Zero | 12 | $12.00 | $4.50 | **$16.50** |
| ThinkMarkets Zero | 18 | $18.00 | $4.00 | **$22.00** |

*Note: Point value for XAUUSD ≈ $1 per point per standard lot*

---

## Implementation Plan

### Phase 1: Config Updates

Add commission fields to `config.json` for each broker:

```json
{
  "name": "Pepperstone Razor",
  "server": "Pepperstone-Demo",
  "login": 12345678,
  "password": "xxxx",
  "path": "C:/Program Files/Pepperstone MetaTrader 5/terminal64.exe",
  "symbol_suffix": ".a",
  "website": "pepperstone.com",
  "commission_per_lot": 7.00,
  "commission_type": "round_trip"
}
```

**New fields:**
- `commission_per_lot`: Commission amount in USD per standard lot
- `commission_type`: `"round_trip"` (entry + exit) or `"per_side"` (entry OR exit)

### Phase 2: Backend API

Create new API endpoint `/api/trading-costs`:

```
GET /api/trading-costs?start=YYYY-MM-DD&end=YYYY-MM-DD&symbol=XAUUSD&lot_size=1.0
```

Response:
```json
{
  "success": true,
  "data": [
    {
      "broker": "Pepperstone Razor",
      "avg_spread_points": 15.2,
      "spread_cost": 15.20,
      "commission": 7.00,
      "total_cost": 22.20,
      "point_value": 1.00
    },
    ...
  ],
  "lot_size": 1.0,
  "symbol": "XAUUSD"
}
```

### Phase 3: New Dashboard Page

Create `/costs` page with:

1. **Input Controls**
   - Lot size selector (0.01, 0.1, 0.5, 1.0, custom)
   - Date range picker (for spread averaging)
   - Symbol selector

2. **Cost Comparison Table**
   | Broker | Avg Spread | Spread Cost | Commission | Total Cost |
   |--------|-----------|-------------|------------|------------|
   | ... | ... | ... | ... | ... |

   - Highlight lowest total cost in green
   - Highlight highest in red
   - Sortable columns

3. **Visualization**
   - Stacked bar chart (spread cost + commission)
   - Pie chart showing cost breakdown per broker

4. **Savings Calculator**
   - "Switching from [Broker A] to [Broker B] saves you $X per lot"
   - Monthly savings estimate based on trades per month input

### Phase 4: Update Existing Pages

1. **Stats Page**
   - Add commission column to statistics table
   - Update recommendation to consider total cost

2. **Sessions Page**
   - Option to view "Best broker by total cost" per session
   - Factor commission into session recommendations

3. **Live Page**
   - Optional toggle to show "Estimated cost per lot" alongside spread

---

## Data Requirements

### Point Values by Symbol

Need to store or calculate point values for each symbol:

| Symbol | Point Value (per standard lot) |
|--------|-------------------------------|
| XAUUSD | ~$1.00 per point |
| EURUSD | $10.00 per pip |
| GBPUSD | $10.00 per pip |
| USDJPY | ~$6.70 per pip (varies with rate) |

**Options:**
1. Hardcode common values
2. Fetch from MT5 `symbol_info.trade_tick_value`
3. Allow manual override in config

### Commission Data Sources

Commission rates can be found on broker websites:
- Pepperstone: https://pepperstone.com/en/trading-fees
- Fusion Markets: https://fusionmarkets.com/fees
- ThinkMarkets: https://thinkmarkets.com/trading-costs

---

## File Structure (New/Modified)

```
spread_monitor/
├── config.json                    # Add commission fields
├── app.py                         # Add /costs route and /api/trading-costs
├── templates/
│   ├── costs.html                 # NEW: Trading costs page
│   ├── stats.html                 # UPDATE: Add commission column
│   └── sessions.html              # UPDATE: Factor in commission
└── utils/
    └── cost_calculator.py         # NEW: Cost calculation logic
```

---

## UI Mockup

```
┌─────────────────────────────────────────────────────────────┐
│  Trading Costs Calculator                                    │
├─────────────────────────────────────────────────────────────┤
│  Lot Size: [1.0 ▼]   Symbol: [XAUUSD ▼]   [Calculate]       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Broker              │ Spread │ Commission │ TOTAL   │    │
│  ├─────────────────────┼────────┼────────────┼─────────┤    │
│  │ 🟢 FusionMarkets    │ $12.00 │ $4.50      │ $16.50  │    │
│  │    Pepperstone      │ $15.00 │ $7.00      │ $22.00  │    │
│  │ 🔴 ThinkMarkets     │ $18.00 │ $4.00      │ $22.00  │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  💡 Recommendation: Trade with FusionMarkets Zero to save   │
│     $5.50 per lot compared to the most expensive option.    │
│                                                              │
│  [     Stacked Bar Chart: Spread vs Commission Cost     ]   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Notes

- Commission data is static (doesn't change often), so no need for real-time monitoring
- Point values may need periodic updates for JPY pairs
- Consider adding a "Commission Editor" in settings to update rates easily
- Future: Could fetch commission rates from broker APIs if available

---

## Priority: Medium

This enhancement would complete the tool's value proposition as a comprehensive trading cost comparison platform.

---

*Created: 2026-01-16*
*Status: Planned for future implementation*
