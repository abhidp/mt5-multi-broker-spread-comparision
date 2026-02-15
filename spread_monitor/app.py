#!/usr/bin/env python3
"""
Flask Dashboard for Spread Monitor

Provides web interface for viewing and analyzing spread data.

Usage:
    python app.py
    Access at http://localhost:5000
"""

import json
import os
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from flask import Flask, jsonify, render_template, request

from utils.data_utils import CSV_COLUMNS, get_csv_filename, load_csv_data
from utils.cost_calculator import (
    calculate_trading_costs,
    calculate_basket_costs,
    get_point_value,
    get_savings_info,
    get_basket_savings_info,
    get_currency_info
)

app = Flask(__name__)

# Optional URL prefix for reverse proxy (e.g., Tailscale Funnel path-based routing)
# Set URL_PREFIX=/spreads in environment to serve at /spreads
URL_PREFIX = os.environ.get('URL_PREFIX', '')
if URL_PREFIX:
    from werkzeug.middleware.dispatcher import DispatcherMiddleware
    from werkzeug.exceptions import NotFound
    app.wsgi_app = DispatcherMiddleware(NotFound(), {URL_PREFIX: app.wsgi_app})

# Load configuration
CONFIG_PATH = "config.json"


def load_config():
    """Load configuration from JSON file."""
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"data_directory": "./data", "flask_port": 5000}


config = load_config()
DATA_DIR = config.get("data_directory", "./data")

# Virtual brokers: use another broker's spread data but with different commission
# These only appear on the costs page, not in spread data collection
VIRTUAL_BROKERS = [
    {
        "name": "Vantage RAW Premium",
        "short_name": "VantagePremium",
        "source_broker": "VantageMarkets Raw",  # Use spread data from this broker
        "website": "vantagemarkets.com",  # Same website for logo
        "commission_per_lot": 2.00,  # A$1 per side = A$2 round trip
        "commission_free_symbols": [
            "XAU", "XAG",
            "NAS100", "US500", "US30", "US2000", "GER40", "UK100"
        ]
    }
]

# Index symbols - use spread (price difference) instead of spread_points for cost calculation
# because different brokers quote indices with different decimal precision
INDEX_SYMBOLS = ["NAS100", "US500", "US30", "US2000", "GER40", "UK100"]


# =============================================================================
# Page Routes
# =============================================================================

@app.route("/")
def index():
    """Live view page - shows current spreads."""
    return render_template("index.html")


@app.route("/history")
def history():
    """History page - shows spread over time."""
    return render_template("history.html")


@app.route("/stats")
def stats():
    """Statistics page - shows aggregated stats and box plot."""
    return render_template("stats.html")


@app.route("/sessions")
def sessions():
    """Session analysis page - shows heatmap and recommendations."""
    return render_template("sessions.html")


@app.route("/costs")
def costs():
    """Trading costs page - shows total cost comparison including commissions."""
    return render_template("costs.html")


# =============================================================================
# API Endpoints
# =============================================================================

@app.route("/api/config")
def api_config():
    """
    Get non-sensitive configuration values.

    Returns:
        JSON with collection interval, symbols, etc.
    """
    return jsonify({
        "success": True,
        "data": {
            "collection_interval_minutes": config.get("collection_interval_minutes", 5),
            "symbols": config.get("symbols", ["XAUUSD"])
        }
    })


@app.route("/api/brokers")
def api_brokers():
    """
    Get broker metadata (names and websites for logos).
    Does not expose sensitive data like passwords.
    Includes virtual brokers used only on costs page.

    Returns:
        JSON with broker name -> website mapping
    """
    try:
        brokers = {}
        for broker in config.get("brokers", []):
            website = broker.get("website", "")
            brokers[broker["name"]] = {
                "website": website,
                "logo_url": f"https://t3.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://{website}&size=128" if website else "",
                "short_name": broker.get("short_name", broker["name"])
            }

        # Add virtual brokers
        for vb in VIRTUAL_BROKERS:
            website = vb.get("website", "")
            brokers[vb["name"]] = {
                "website": website,
                "logo_url": f"https://t3.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://{website}&size=128" if website else "",
                "short_name": vb.get("short_name", vb["name"])
            }

        return jsonify({
            "success": True,
            "data": brokers
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/live")
def api_live():
    """
    Get current spread data (latest reading for each broker-symbol combination).

    Returns:
        JSON with latest spread per broker per symbol
    """
    try:
        # Get today's file
        csv_path = get_csv_filename(DATA_DIR)

        if not os.path.exists(csv_path):
            # Try yesterday if today's file doesn't exist yet
            yesterday = datetime.now(timezone.utc)
            yesterday = yesterday.replace(day=yesterday.day - 1)
            csv_path = get_csv_filename(DATA_DIR, yesterday)

        if not os.path.exists(csv_path):
            return jsonify({
                "success": True,
                "data": [],
                "timestamp": datetime.now(timezone.utc).isoformat()
            })

        df = pd.read_csv(csv_path)
        df["timestamp"] = pd.to_datetime(df["timestamp"])

        # Get latest row for each broker-symbol combination
        latest = df.sort_values("timestamp").groupby(["broker", "symbol"]).last().reset_index()

        data = latest.to_dict(orient="records")

        return jsonify({
            "success": True,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/history")
def api_history():
    """
    Get historical spread data.

    Query params:
        start: Start date (YYYY-MM-DD)
        end: End date (YYYY-MM-DD)
        symbol: Symbol to filter (optional)

    Returns:
        JSON with historical data
    """
    try:
        start_str = request.args.get("start")
        end_str = request.args.get("end")
        symbol = request.args.get("symbol")

        start_date = datetime.strptime(start_str, "%Y-%m-%d") if start_str else None
        end_date = datetime.strptime(end_str, "%Y-%m-%d") if end_str else None

        df = load_csv_data(DATA_DIR, start_date, end_date)

        if df.empty:
            return jsonify({
                "success": True,
                "data": []
            })

        # Filter by symbol if specified
        if symbol:
            df = df[df["symbol"] == symbol]

        # Convert timestamp to string for JSON
        df["timestamp"] = df["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")

        data = df.to_dict(orient="records")

        return jsonify({
            "success": True,
            "data": data
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/stats")
def api_stats():
    """
    Get aggregated statistics per broker.

    Query params:
        start: Start date (YYYY-MM-DD)
        end: End date (YYYY-MM-DD)
        symbol: Symbol to filter (optional)

    Returns:
        JSON with avg/min/max/std per broker
    """
    try:
        start_str = request.args.get("start")
        end_str = request.args.get("end")
        symbol = request.args.get("symbol")

        start_date = datetime.strptime(start_str, "%Y-%m-%d") if start_str else None
        end_date = datetime.strptime(end_str, "%Y-%m-%d") if end_str else None

        df = load_csv_data(DATA_DIR, start_date, end_date)

        if df.empty:
            return jsonify({
                "success": True,
                "data": []
            })

        # Filter by symbol if specified
        if symbol:
            df = df[df["symbol"] == symbol]

        # Calculate statistics per broker
        stats = df.groupby("broker")["spread_points"].agg([
            ("avg", "mean"),
            ("min", "min"),
            ("max", "max"),
            ("std", "std"),
            ("count", "count")
        ]).reset_index()

        # Handle NaN std (when only one data point)
        stats["std"] = stats["std"].fillna(0)

        data = stats.to_dict(orient="records")

        return jsonify({
            "success": True,
            "data": data
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/sessions")
def api_sessions():
    """
    Get session-based analysis data.

    Query params:
        start: Start date (YYYY-MM-DD)
        end: End date (YYYY-MM-DD)
        symbol: Symbol to filter (optional)

    Returns:
        JSON with avg spread per broker per session
    """
    try:
        start_str = request.args.get("start")
        end_str = request.args.get("end")
        symbol = request.args.get("symbol")

        start_date = datetime.strptime(start_str, "%Y-%m-%d") if start_str else None
        end_date = datetime.strptime(end_str, "%Y-%m-%d") if end_str else None

        df = load_csv_data(DATA_DIR, start_date, end_date)

        if df.empty:
            return jsonify({
                "success": True,
                "data": []
            })

        # Filter by symbol if specified
        if symbol:
            df = df[df["symbol"] == symbol]

        # Calculate statistics per broker per session
        session_stats = df.groupby(["session", "broker"])["spread_points"].agg([
            ("avg", "mean"),
            ("min", "min"),
            ("max", "max"),
            ("count", "count")
        ]).reset_index()

        data = session_stats.to_dict(orient="records")

        return jsonify({
            "success": True,
            "data": data
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/trading-costs")
def api_trading_costs():
    """
    Get trading costs comparison including spread and commission.

    Query params:
        start: Start date (YYYY-MM-DD)
        end: End date (YYYY-MM-DD)
        symbol: Single symbol to filter (default: XAUUSD) - for backward compatibility
        symbols: Comma-separated list of symbols for basket analysis
        lot_size: Lot size for calculation (default: 1.0)

    Returns:
        JSON with trading costs per broker
        - For single symbol: original response format
        - For multiple symbols: basket response with breakdown per symbol
    """
    try:
        start_str = request.args.get("start")
        end_str = request.args.get("end")
        lot_size = float(request.args.get("lot_size", 1.0))

        # Support both 'symbols' (comma-separated) and 'symbol' (single) params
        symbols_param = request.args.get("symbols", "")
        symbol_param = request.args.get("symbol", "")

        # Parse symbols list
        if symbols_param:
            symbols = [s.strip() for s in symbols_param.split(",") if s.strip()]
        elif symbol_param:
            symbols = [symbol_param]
        else:
            symbols = ["XAUUSD"]  # Default

        start_date = datetime.strptime(start_str, "%Y-%m-%d") if start_str else None
        end_date = datetime.strptime(end_str, "%Y-%m-%d") if end_str else None

        df = load_csv_data(DATA_DIR, start_date, end_date)

        # Get commission data from config (including commission-free symbols)
        broker_commissions = {}
        for broker in config.get("brokers", []):
            broker_commissions[broker["name"]] = {
                "commission_per_lot": broker.get("commission_per_lot", 0),
                "commission_free_symbols": broker.get("commission_free_symbols", [])
            }

        # Add virtual broker commissions
        for vb in VIRTUAL_BROKERS:
            broker_commissions[vb["name"]] = {
                "commission_per_lot": vb.get("commission_per_lot", 0),
                "commission_free_symbols": vb.get("commission_free_symbols", [])
            }

        currency = get_currency_info()

        # Single symbol - use original logic for backward compatibility
        if len(symbols) == 1:
            symbol = symbols[0]

            if df.empty:
                return jsonify({
                    "success": True,
                    "data": [],
                    "savings": None,
                    "lot_size": lot_size,
                    "symbol": symbol
                })

            # Filter by symbol
            df_symbol = df[df["symbol"] == symbol]

            # Calculate average spread per broker
            # For indices, use 'spread' (price difference) because brokers have different decimal precision
            # For other symbols, use 'spread_points' which is normalized
            spread_column = "spread" if symbol in INDEX_SYMBOLS else "spread_points"
            broker_stats = df_symbol.groupby("broker")[spread_column].agg([
                ("avg", "mean")
            ]).reset_index().to_dict(orient="records")

            # Add virtual brokers by cloning source broker's spread data
            for vb in VIRTUAL_BROKERS:
                source_stat = next(
                    (s for s in broker_stats if s["broker"] == vb["source_broker"]),
                    None
                )
                if source_stat:
                    broker_stats.append({
                        "broker": vb["name"],
                        "avg": source_stat["avg"]
                    })

            # Calculate trading costs
            costs = calculate_trading_costs(
                broker_stats=broker_stats,
                broker_commissions=broker_commissions,
                symbol=symbol,
                lot_size=lot_size
            )

            # Get savings information
            savings = get_savings_info(costs)

            return jsonify({
                "success": True,
                "data": costs,
                "savings": savings,
                "lot_size": lot_size,
                "symbol": symbol,
                "point_value": get_point_value(symbol),
                "currency": currency
            })

        # Multiple symbols - basket analysis
        else:
            if df.empty:
                return jsonify({
                    "success": True,
                    "data": [],
                    "savings": None,
                    "lot_size": lot_size,
                    "symbols": symbols,
                    "is_basket": True
                })

            # Calculate broker stats for each symbol
            symbol_broker_stats = {}
            for symbol in symbols:
                df_symbol = df[df["symbol"] == symbol]
                if not df_symbol.empty:
                    # For indices, use 'spread' (price difference) because brokers have different decimal precision
                    spread_column = "spread" if symbol in INDEX_SYMBOLS else "spread_points"
                    broker_stats = df_symbol.groupby("broker")[spread_column].agg([
                        ("avg", "mean")
                    ]).reset_index().to_dict(orient="records")

                    # Add virtual brokers by cloning source broker's spread data
                    for vb in VIRTUAL_BROKERS:
                        source_stat = next(
                            (s for s in broker_stats if s["broker"] == vb["source_broker"]),
                            None
                        )
                        if source_stat:
                            broker_stats.append({
                                "broker": vb["name"],
                                "avg": source_stat["avg"]
                            })

                    symbol_broker_stats[symbol] = broker_stats
                else:
                    symbol_broker_stats[symbol] = []

            # Calculate basket costs
            costs = calculate_basket_costs(
                symbols=symbols,
                symbol_broker_stats=symbol_broker_stats,
                broker_commissions=broker_commissions,
                lot_size=lot_size
            )

            # Get savings information
            savings = get_basket_savings_info(costs)

            return jsonify({
                "success": True,
                "data": costs,
                "savings": savings,
                "lot_size": lot_size,
                "symbols": symbols,
                "is_basket": True,
                "currency": currency
            })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/commissions")
def api_commissions():
    """
    Get commission data for all brokers.

    Returns:
        JSON with broker commission information
    """
    try:
        commissions = {}
        for broker in config.get("brokers", []):
            commissions[broker["name"]] = {
                "commission_per_lot": broker.get("commission_per_lot", 0),
                "commission_currency": broker.get("commission_currency", "USD")
            }

        return jsonify({
            "success": True,
            "data": commissions
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    port = config.get("flask_port", 5000)
    print(f"Starting Spread Monitor Dashboard on http://localhost:{port}")
    app.run(host='0.0.0.0', debug=True, port=port)
