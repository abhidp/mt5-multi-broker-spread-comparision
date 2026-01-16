"""
Data processing and storage utilities.

Handles CSV file operations with daily rotation.
"""

import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List

import pandas as pd

from .mt5_connector import SpreadData
from .session_utils import get_day_of_week, get_session_tag

logger = logging.getLogger(__name__)

# CSV column order
CSV_COLUMNS = [
    "timestamp",
    "broker",
    "symbol",
    "bid",
    "ask",
    "spread",
    "spread_points",
    "session",
    "day_of_week"
]


def get_csv_filename(data_dir: str, date: datetime = None) -> str:
    """
    Get the CSV filename for a given date.

    Args:
        data_dir: Directory to store CSV files
        date: Date for the filename (defaults to current UTC date)

    Returns:
        Full path to the CSV file
    """
    if date is None:
        date = datetime.now(timezone.utc)

    date_str = date.strftime("%Y-%m-%d")
    filename = f"spread_data_{date_str}.csv"
    return os.path.join(data_dir, filename)


def ensure_directory(path: str) -> None:
    """
    Ensure a directory exists, creating it if necessary.

    Args:
        path: Directory path to create
    """
    Path(path).mkdir(parents=True, exist_ok=True)


def spread_data_to_dict(spread_data: SpreadData) -> dict:
    """
    Convert SpreadData object to dictionary with session info.

    Args:
        spread_data: SpreadData object

    Returns:
        Dictionary with all fields including session info
    """
    return {
        "timestamp": spread_data.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        "broker": spread_data.broker,
        "symbol": spread_data.symbol,
        "bid": spread_data.bid,
        "ask": spread_data.ask,
        "spread": spread_data.spread,
        "spread_points": spread_data.spread_points,
        "session": get_session_tag(spread_data.timestamp),
        "day_of_week": get_day_of_week(spread_data.timestamp)
    }


def save_to_csv(
    spread_data_list: List[SpreadData],
    data_dir: str
) -> str:
    """
    Save spread data to CSV file with daily rotation.

    Args:
        spread_data_list: List of SpreadData objects to save
        data_dir: Directory to store CSV files

    Returns:
        Path to the CSV file written
    """
    if not spread_data_list:
        logger.warning("No data to save")
        return ""

    # Ensure data directory exists
    ensure_directory(data_dir)

    # Get filename based on current date
    csv_path = get_csv_filename(data_dir)

    # Convert spread data to list of dicts
    records = [spread_data_to_dict(sd) for sd in spread_data_list]

    # Create DataFrame
    df = pd.DataFrame(records, columns=CSV_COLUMNS)

    # Check if file exists and has content to determine if we need headers
    write_header = True
    if os.path.exists(csv_path) and os.path.getsize(csv_path) > 0:
        write_header = False

    # Append to CSV (create if doesn't exist)
    df.to_csv(
        csv_path,
        mode='a',
        header=write_header,
        index=False
    )

    logger.info(f"Saved {len(records)} records to {csv_path}")
    return csv_path


def load_csv_data(
    data_dir: str,
    start_date: datetime = None,
    end_date: datetime = None
) -> pd.DataFrame:
    """
    Load CSV data from the data directory.

    Args:
        data_dir: Directory containing CSV files
        start_date: Start date to load (optional)
        end_date: End date to load (optional)

    Returns:
        DataFrame with all loaded data
    """
    data_path = Path(data_dir)
    if not data_path.exists():
        logger.warning(f"Data directory does not exist: {data_dir}")
        return pd.DataFrame(columns=CSV_COLUMNS)

    # Get all CSV files
    csv_files = sorted(data_path.glob("spread_data_*.csv"))

    if not csv_files:
        logger.warning(f"No CSV files found in {data_dir}")
        return pd.DataFrame(columns=CSV_COLUMNS)

    # Filter by date range if provided
    filtered_files = []
    for csv_file in csv_files:
        # Extract date from filename
        try:
            file_date_str = csv_file.stem.replace("spread_data_", "")
            file_date = datetime.strptime(file_date_str, "%Y-%m-%d")

            if start_date and file_date.date() < start_date.date():
                continue
            if end_date and file_date.date() > end_date.date():
                continue

            filtered_files.append(csv_file)
        except ValueError:
            logger.warning(f"Could not parse date from filename: {csv_file}")
            continue

    if not filtered_files:
        logger.warning("No CSV files match the date range")
        return pd.DataFrame(columns=CSV_COLUMNS)

    # Load and concatenate all files
    dfs = []
    for csv_file in filtered_files:
        try:
            df = pd.read_csv(csv_file)
            dfs.append(df)
            logger.debug(f"Loaded {len(df)} records from {csv_file}")
        except Exception as e:
            logger.error(f"Error loading {csv_file}: {e}")

    if not dfs:
        return pd.DataFrame(columns=CSV_COLUMNS)

    combined_df = pd.concat(dfs, ignore_index=True)

    # Parse timestamp column
    combined_df["timestamp"] = pd.to_datetime(combined_df["timestamp"])

    return combined_df


def get_latest_data(data_dir: str) -> pd.DataFrame:
    """
    Get the most recent spread data for each broker.

    Args:
        data_dir: Directory containing CSV files

    Returns:
        DataFrame with latest data per broker
    """
    # Get today's file
    csv_path = get_csv_filename(data_dir)

    if not os.path.exists(csv_path):
        logger.warning(f"Today's CSV file does not exist: {csv_path}")
        return pd.DataFrame(columns=CSV_COLUMNS)

    try:
        df = pd.read_csv(csv_path)
        df["timestamp"] = pd.to_datetime(df["timestamp"])

        # Get latest row for each broker/symbol combination
        latest = df.sort_values("timestamp").groupby(["broker", "symbol"]).last().reset_index()
        return latest
    except Exception as e:
        logger.error(f"Error loading latest data: {e}")
        return pd.DataFrame(columns=CSV_COLUMNS)
