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
from utils.cost_calculator import calculate_trading_costs, get_point_value, get_savings_info, get_currency_info

app = Flask(__name__)

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
    Get current spread data (latest reading for each broker).

    Returns:
        JSON with latest spread per broker
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

        # Get latest row for each broker
        latest = df.sort_values("timestamp").groupby("broker").last().reset_index()

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
        symbol: Symbol to filter (default: XAUUSD)
        lot_size: Lot size for calculation (default: 1.0)

    Returns:
        JSON with trading costs per broker
    """
    try:
        start_str = request.args.get("start")
        end_str = request.args.get("end")
        symbol = request.args.get("symbol", "XAUUSD")
        lot_size = float(request.args.get("lot_size", 1.0))

        start_date = datetime.strptime(start_str, "%Y-%m-%d") if start_str else None
        end_date = datetime.strptime(end_str, "%Y-%m-%d") if end_str else None

        df = load_csv_data(DATA_DIR, start_date, end_date)

        if df.empty:
            return jsonify({
                "success": True,
                "data": [],
                "savings": None,
                "lot_size": lot_size,
                "symbol": symbol
            })

        # Filter by symbol if specified
        if symbol:
            df = df[df["symbol"] == symbol]

        # Calculate average spread per broker
        broker_stats = df.groupby("broker")["spread_points"].agg([
            ("avg", "mean")
        ]).reset_index().to_dict(orient="records")

        # Get commission data from config (including commission-free symbols)
        broker_commissions = {}
        for broker in config.get("brokers", []):
            broker_commissions[broker["name"]] = {
                "commission_per_lot": broker.get("commission_per_lot", 0),
                "commission_free_symbols": broker.get("commission_free_symbols", [])
            }

        # Calculate trading costs
        costs = calculate_trading_costs(
            broker_stats=broker_stats,
            broker_commissions=broker_commissions,
            symbol=symbol,
            lot_size=lot_size
        )

        # Get savings information
        savings = get_savings_info(costs)

        currency = get_currency_info()
        return jsonify({
            "success": True,
            "data": costs,
            "savings": savings,
            "lot_size": lot_size,
            "symbol": symbol,
            "point_value": get_point_value(symbol),
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
