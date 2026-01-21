# Basket Cost Analysis Feature - Implementation Plan

## Overview

Add multi-symbol selection to the Trading Costs page, allowing traders to analyze which broker is most cost-effective across a "basket" of symbols they frequently trade together.

## Current State

- Costs page allows selecting **one symbol** at a time
- Shows spread cost + commission per broker for that symbol
- Trader must manually compare across symbols to decide

## Desired State

- Costs page allows selecting **multiple symbols** as a basket
- Shows **aggregate costs** across all selected symbols per broker
- Highlights the **best overall broker** for the entire basket
- Provides **preset baskets** (Forex Majors, Commodities, Indices, All)

---

## Implementation Plan

### Phase 1: Backend API Changes

#### 1.1 Modify `/api/trading-costs` endpoint

**Current signature:**
```
GET /api/trading-costs?start=&end=&symbol=XAUUSD&lot_size=1.0
```

**New signature:**
```
GET /api/trading-costs?start=&end=&symbols=XAUUSD,EURUSD,GBPUSD&lot_size=1.0
```

**Changes needed in `app.py`:**
- Accept `symbols` as comma-separated list (keep backward compat with `symbol` for single)
- Loop through each symbol, calculate costs per broker
- Aggregate costs per broker across all symbols
- Return both per-symbol breakdown AND total aggregate

#### 1.2 New Response Structure

```json
{
  "success": true,
  "symbols": ["XAUUSD", "EURUSD", "GBPUSD"],
  "lot_size": 1.0,
  "data": [
    {
      "broker": "FusionMarkets Zero",
      "total_cost": 15.50,
      "total_spread_cost": 11.00,
      "total_commission": 4.50,
      "symbol_count": 3,
      "breakdown": [
        {"symbol": "XAUUSD", "avg_spread_points": 12.5, "spread_cost": 5.00, "commission": 4.50, "total": 9.50},
        {"symbol": "EURUSD", "avg_spread_points": 0.8, "spread_cost": 3.00, "commission": 0, "total": 3.00},
        {"symbol": "GBPUSD", "avg_spread_points": 1.0, "spread_cost": 3.00, "commission": 0, "total": 3.00}
      ]
    }
  ],
  "savings": {
    "best_broker": "FusionMarkets Zero",
    "best_cost": 15.50,
    "worst_broker": "ICMarkets Raw",
    "worst_cost": 22.00,
    "savings_per_trade": 6.50,
    "savings_percent": 29.5
  },
  "currency": {"symbol": "A$", "code": "AUD"}
}
```

---

### Phase 2: Frontend UI Changes

#### 2.1 Replace Single-Select with Multi-Select Checkboxes

Convert the symbol dropdown to a checkbox list that allows multiple selections:

```
Symbol Selection:
[x] XAUUSD (Gold)
[x] EURUSD
[x] GBPUSD
[ ] USDJPY
[ ] AUDUSD
```

Show selected count: "3 of 5 symbols selected"

#### 2.2 Add Preset Basket Buttons

Add quick-select buttons above the symbol list:

```
Quick Select: [All] [Forex Only] [Clear]
```

For now with your current symbols:
- **All**: XAUUSD, EURUSD, GBPUSD, USDJPY, AUDUSD
- **Forex Only**: EURUSD, GBPUSD, USDJPY, AUDUSD (excludes gold)

Later when you add more symbols:
- **Commodities**: XAUUSD, XAGUSD, Oil, etc.
- **Indices**: US500, GER40, etc.

#### 2.3 Update Results Table

**New table structure:**

| Broker | Symbols | Total Spread | Total Commission | Total Cost |
|--------|---------|--------------|------------------|------------|
| Fusion | 5 [+]   | A$8.50       | A$4.50           | A$13.00 ★  |
| Vantage| 5 [+]   | A$7.00       | A$5.00           | A$12.00    |

The `[+]` expands to show per-symbol breakdown.

#### 2.4 Expandable Per-Symbol Breakdown

When user clicks expand on a broker row:

```
▼ FusionMarkets Zero                              A$13.00 total
  ┌─────────┬────────────┬─────────┬────────────┬─────────┐
  │ Symbol  │ Avg Spread │ Spread$ │ Commission │ Total   │
  ├─────────┼────────────┼─────────┼────────────┼─────────┤
  │ XAUUSD  │ 10.2 pts   │ A$5.10  │ A$4.50     │ A$9.60  │
  │ EURUSD  │ 0.3 pts    │ A$0.30  │ A$0.00     │ A$0.30  │
  │ GBPUSD  │ 0.5 pts    │ A$0.50  │ A$0.00     │ A$0.50  │
  │ USDJPY  │ 0.4 pts    │ A$0.40  │ A$0.00     │ A$0.40  │
  │ AUDUSD  │ 0.3 pts    │ A$0.30  │ A$0.00     │ A$0.30  │
  └─────────┴────────────┴─────────┴────────────┴─────────┘
```

#### 2.5 Update Stacked Bar Chart

Show cost breakdown by symbol for each broker:

```
                    Fusion    Vantage   Pepper    IC       FP
XAUUSD              ████████  ██████    ████████  ████████ ████████
EURUSD              ██        ████      ████      ██████   ████
GBPUSD              ██        ████      ████      ██████   ████
USDJPY              ██        ████      ████      ████     ████
AUDUSD              ██        ████      ████      ████     ████
                    ────────────────────────────────────────────
Total:              $13.00    $15.00    $18.00    $22.00   $19.00
```

#### 2.6 Update Savings Card

Show aggregate savings:

```
┌─────────────────────────────────────────────────────────────┐
│  Potential Savings (5 symbols, 1.0 lot each)                │
│                                                             │
│  A$9.00 per trade saved using FusionMarkets Zero           │
│                                                             │
│  vs ICMarkets Raw (A$22.00/trade) · 41% lower costs!       │
└─────────────────────────────────────────────────────────────┘
```

---

### Phase 3: Future Enhancements (Optional)

#### 3.1 Trade Weighting

Let users specify how frequently they trade each symbol:

```
Trade Frequency (% of trades):
XAUUSD:  [====░░░░░░] 40%
EURUSD:  [===░░░░░░░] 30%
GBPUSD:  [==░░░░░░░░] 20%
USDJPY:  [=░░░░░░░░░] 10%
```

Weighted cost gives more realistic comparison.

#### 3.2 Different Lot Sizes per Symbol

Allow different position sizes:
- XAUUSD: 0.5 lot (smaller due to higher value)
- EURUSD: 2.0 lots (larger, lower risk)

---

## Files to Modify

| File | Changes |
|------|---------|
| `app.py` | Update `/api/trading-costs` for multi-symbol |
| `utils/cost_calculator.py` | Add basket aggregation logic |
| `templates/costs.html` | Multi-select UI, expandable table, updated charts |

---

## Implementation Tasks (Ordered)

### Task 1: Backend - Multi-Symbol API
- [ ] Modify `/api/trading-costs` to accept `symbols` param (comma-separated)
- [ ] Keep backward compatibility with single `symbol` param
- [ ] Calculate costs for each symbol per broker
- [ ] Aggregate totals per broker
- [ ] Return new response structure with breakdown

### Task 2: Frontend - Multi-Select UI
- [ ] Replace dropdown with checkbox list
- [ ] Add "selected count" display
- [ ] Update form submission to send multiple symbols

### Task 3: Frontend - Preset Buttons
- [ ] Add "All" / "Forex Only" / "Clear" buttons
- [ ] Wire up click handlers to select/deselect symbols

### Task 4: Frontend - Results Table
- [ ] Update table to show aggregate totals
- [ ] Add expandable row functionality
- [ ] Show per-symbol breakdown when expanded

### Task 5: Frontend - Charts & Savings
- [ ] Update stacked bar chart for multi-symbol
- [ ] Update savings card text for basket context

---

## Questions Before Starting

1. **Equal weighting?** Should all symbols count equally, or weight by trade frequency?
   - Recommend: Start with equal weighting, add frequency weighting later

2. **Same lot size?** Use same lot size for all symbols in basket?
   - Recommend: Yes for simplicity, per-symbol lots as future enhancement

3. **Preset baskets?** Just "All" and "Forex Only" for now?
   - Can add more (Commodities, Indices) when you add those symbols

---

## Ready to Implement

This is absolutely doable. The core changes are:
1. API accepts array of symbols instead of single symbol
2. Frontend uses checkboxes instead of dropdown
3. Table shows expandable aggregate results

Let me know which task to start with, or if you want to adjust the plan first.
