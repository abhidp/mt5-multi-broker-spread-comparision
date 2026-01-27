"""
Generate mock spread data for testing the history chart weekend handling.
Creates CSV files spanning multiple weeks with realistic spread data.

Usage:
    python generate_test_data.py
    python generate_test_data.py --weeks 4
"""

import argparse
import csv
import os
import random
from datetime import datetime, timedelta, timezone

# Reuse project utilities
from utils.data_utils import CSV_COLUMNS, get_csv_filename
from utils.session_utils import get_session_tag

BROKERS = [
    "Pepperstone Razor",
    "FusionMarkets Zero",
    "ICMarkets Raw",
]

SYMBOLS = ["XAUUSD", "EURUSD", "NAS100"]

# Typical spread ranges per symbol (in points)
SPREAD_RANGES = {
    "XAUUSD": (8, 25),
    "EURUSD": (0, 4),
    "GBPUSD": (0, 5),
    "USDJPY": (0, 4),
    "AUDUSD": (0, 4),
    "NAS100": (60, 150),
    "US500": (20, 50),
}

# Point values per symbol
POINT_VALUES = {
    "XAUUSD": 0.01,
    "EURUSD": 0.00001,
    "GBPUSD": 0.00001,
    "USDJPY": 0.001,
    "AUDUSD": 0.00001,
    "NAS100": 0.01,
    "US500": 0.01,
}

# Base prices
BASE_PRICES = {
    "XAUUSD": 5080.0,
    "EURUSD": 1.18900,
    "GBPUSD": 1.37000,
    "USDJPY": 153.650,
    "AUDUSD": 0.69350,
    "NAS100": 25740.0,
    "US500": 6953.0,
}


def is_weekend(dt):
    """Check if datetime falls on weekend (Fri 21:00 UTC to Sun 21:00 UTC)."""
    weekday = dt.weekday()
    hour = dt.hour

    if weekday == 4 and hour >= 21:  # Friday after 21:00
        return True
    if weekday == 5:  # Saturday
        return True
    if weekday == 6 and hour < 21:  # Sunday before 21:00
        return True
    return False


def generate_data(weeks=4, interval_minutes=30, data_dir="./data"):
    """Generate mock spread data."""
    os.makedirs(data_dir, exist_ok=True)

    end_time = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    start_time = end_time - timedelta(weeks=weeks)

    current_time = start_time
    rows_by_date = {}

    while current_time <= end_time:
        if not is_weekend(current_time):
            date_str = current_time.strftime("%Y-%m-%d")
            if date_str not in rows_by_date:
                rows_by_date[date_str] = []

            session = get_session_tag(current_time)
            day_name = current_time.strftime("%A")

            for broker in BROKERS:
                for symbol in SYMBOLS:
                    min_spread, max_spread = SPREAD_RANGES[symbol]
                    spread_points = random.randint(min_spread, max_spread)
                    point = POINT_VALUES[symbol]
                    spread = round(spread_points * point, 5)

                    base = BASE_PRICES[symbol]
                    # Add some random price drift
                    price_drift = random.uniform(-base * 0.005, base * 0.005)
                    bid = round(base + price_drift, 5)
                    ask = round(bid + spread, 5)

                    rows_by_date[date_str].append([
                        current_time.strftime("%Y-%m-%d %H:%M:%S"),
                        broker,
                        symbol,
                        bid,
                        ask,
                        spread,
                        spread_points,
                        session,
                        day_name,
                    ])

        current_time += timedelta(minutes=interval_minutes)

    # Write to CSV files (one per day)
    total_rows = 0
    for date_str, rows in sorted(rows_by_date.items()):
        filepath = os.path.join(data_dir, f"spread_data_{date_str}.csv")
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(CSV_COLUMNS)
            writer.writerows(rows)
        total_rows += len(rows)
        print(f"  {filepath}: {len(rows)} rows")

    print(f"\nGenerated {total_rows} total rows across {len(rows_by_date)} days ({weeks} weeks)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate test spread data")
    parser.add_argument("--weeks", type=int, default=4, help="Number of weeks of data to generate")
    parser.add_argument("--interval", type=int, default=5, help="Collection interval in minutes")
    parser.add_argument("--data-dir", type=str, default="./data_test", help="Output directory")
    args = parser.parse_args()

    print(f"Generating {args.weeks} weeks of test data (every {args.interval} min)...")
    print(f"Output directory: {args.data_dir}\n")
    generate_data(weeks=args.weeks, interval_minutes=args.interval, data_dir=args.data_dir)
    print(f"\nTo use this data, update config.json: \"data_directory\": \"{args.data_dir}\"")
    print("Or temporarily change DATA_DIR in app.py")
