#!/usr/bin/env python3
"""
Spread Data Collector

Collects spread data from multiple MT5 brokers at configurable intervals
and saves to CSV files with daily rotation.

Usage:
    python collector.py
    python collector.py --once  # Run once without scheduling
"""

import argparse
import json
import logging
import os
import signal
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

from utils.data_utils import save_to_csv
from utils.mt5_connector import MT5Connector, load_brokers_from_config, set_shutdown_flag
from utils.session_utils import is_market_open

# Global scheduler and shutdown event for signal handling
scheduler = None
shutdown_event = threading.Event()


def setup_logging(log_dir: str, level: int = logging.INFO) -> None:
    """
    Set up logging configuration.

    Args:
        log_dir: Directory to store log files
        level: Logging level
    """
    # Ensure log directory exists
    Path(log_dir).mkdir(parents=True, exist_ok=True)

    # Create formatters
    file_formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%H:%M:%S"
    )

    # File handler - error.log
    error_log_path = os.path.join(log_dir, "error.log")
    file_handler = logging.FileHandler(error_log_path, encoding="utf-8")
    file_handler.setLevel(logging.WARNING)
    file_handler.setFormatter(file_formatter)

    # File handler - collector.log (all messages)
    collector_log_path = os.path.join(log_dir, "collector.log")
    collector_handler = logging.FileHandler(collector_log_path, encoding="utf-8")
    collector_handler.setLevel(logging.DEBUG)
    collector_handler.setFormatter(file_formatter)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(console_formatter)

    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(collector_handler)
    root_logger.addHandler(console_handler)


def load_config(config_path: str = "config.json") -> dict:
    """
    Load configuration from JSON file.

    Args:
        config_path: Path to config.json file

    Returns:
        Configuration dictionary
    """
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def collect_spreads(config: dict) -> None:
    """
    Main collection function - collects spreads from all brokers.

    Args:
        config: Configuration dictionary
    """
    logger = logging.getLogger(__name__)
    utc_now = datetime.now(timezone.utc)

    logger.info("=" * 60)
    logger.info(f"Starting collection at {utc_now.strftime('%Y-%m-%d %H:%M:%S')} UTC")

    # Check if market is open
    if not is_market_open(utc_now):
        logger.info("Market is closed, skipping collection")
        return

    # Load broker configurations
    brokers = load_brokers_from_config(config)
    if not brokers:
        logger.error("No brokers configured")
        return

    symbols = config.get("symbols", ["XAUUSD"])
    data_dir = config.get("data_directory", "./data")
    retry_attempts = config.get("retry_attempts", 3)
    retry_delay = config.get("retry_delay_seconds", 5)

    logger.info(f"Collecting {symbols} from {len(brokers)} brokers")

    # Create connector and collect data
    connector = MT5Connector(
        retry_attempts=retry_attempts,
        retry_delay=retry_delay
    )

    spread_data = connector.collect_from_all_brokers(brokers, symbols)

    if spread_data:
        # Save to CSV
        csv_path = save_to_csv(spread_data, data_dir)
        logger.info(f"Collection complete: {len(spread_data)} records saved")

        # Log summary
        for sd in spread_data:
            logger.info(
                f"  {sd.broker} | {sd.symbol} | "
                f"Spread: {sd.spread_points} pts ({sd.spread:.5f})"
            )
    else:
        logger.warning("No data collected from any broker")

    logger.info("=" * 60)


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    logger = logging.getLogger(__name__)
    logger.info("Shutdown signal received, stopping collector...")

    # Set shutdown flag to interrupt blocking operations
    global shutdown_event
    shutdown_event.set()
    set_shutdown_flag()

    global scheduler
    if scheduler:
        scheduler.shutdown(wait=False)

    sys.exit(0)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Collect spread data from MT5 brokers"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run collection once without scheduling"
    )
    parser.add_argument(
        "--config",
        default="config.json",
        help="Path to configuration file (default: config.json)"
    )
    args = parser.parse_args()

    # Load configuration
    try:
        config = load_config(args.config)
    except FileNotFoundError:
        print(f"Error: Configuration file not found: {args.config}")
        print("Please create config.json with your broker credentials.")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in configuration file: {e}")
        sys.exit(1)

    # Setup logging
    log_dir = config.get("log_directory", "./logs")
    setup_logging(log_dir)

    logger = logging.getLogger(__name__)
    logger.info("Spread Monitor Collector starting...")
    logger.info(f"Configuration loaded from {args.config}")

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    if args.once:
        # Run once and exit
        logger.info("Running single collection...")
        collect_spreads(config)
        logger.info("Single collection complete")
    else:
        # Run with scheduler
        global scheduler
        interval_minutes = config.get("collection_interval_minutes", 5)

        logger.info(f"Starting scheduler with {interval_minutes} minute interval")

        scheduler = BlockingScheduler()

        # Add job
        scheduler.add_job(
            collect_spreads,
            IntervalTrigger(minutes=interval_minutes),
            args=[config],
            id="spread_collector",
            name="Spread Data Collection",
            max_instances=1,
            coalesce=True
        )

        # Run immediately on start
        logger.info("Running initial collection...")
        collect_spreads(config)

        try:
            logger.info("Scheduler started. Press Ctrl+C to stop.")
            scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            logger.info("Scheduler stopped")


if __name__ == "__main__":
    main()
