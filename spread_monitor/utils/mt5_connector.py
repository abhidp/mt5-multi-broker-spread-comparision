"""
MT5 connection handling utilities.

Handles connecting to MT5 terminals, fetching tick data, and calculating spreads.
"""

import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

import MetaTrader5 as mt5

logger = logging.getLogger(__name__)

# Global shutdown event for interrupting blocking operations
_shutdown_event = threading.Event()


def set_shutdown_flag():
    """Set the shutdown flag to interrupt blocking operations."""
    _shutdown_event.set()


def is_shutdown_requested():
    """Check if shutdown has been requested."""
    return _shutdown_event.is_set()


def interruptible_sleep(seconds: float, check_interval: float = 0.1) -> bool:
    """
    Sleep that can be interrupted by shutdown signal.

    Args:
        seconds: Total seconds to sleep
        check_interval: How often to check for shutdown (default 100ms)

    Returns:
        True if sleep completed normally, False if interrupted by shutdown
    """
    elapsed = 0.0
    while elapsed < seconds:
        if _shutdown_event.is_set():
            return False
        sleep_time = min(check_interval, seconds - elapsed)
        time.sleep(sleep_time)
        elapsed += sleep_time
    return True


@dataclass
class BrokerConfig:
    """Configuration for a single broker."""
    name: str
    server: str
    login: int
    password: str
    path: str
    symbol_suffix: str = ""
    symbol_suffix_overrides: Dict[str, str] = field(default_factory=dict)

    def get_symbol_suffix(self, symbol: str) -> str:
        """Get the suffix for a specific symbol, checking overrides first."""
        return self.symbol_suffix_overrides.get(symbol, self.symbol_suffix)


@dataclass
class SpreadData:
    """Spread data captured from a broker."""
    timestamp: datetime
    broker: str
    symbol: str
    bid: float
    ask: float
    spread: float
    spread_points: int


class MT5Connector:
    """Handles connections to MT5 terminal and data retrieval."""

    def __init__(self, retry_attempts: int = 3, retry_delay: int = 5):
        """
        Initialize the MT5 connector.

        Args:
            retry_attempts: Number of retry attempts on connection failure
            retry_delay: Delay in seconds between retries
        """
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay

    def connect(self, broker: BrokerConfig) -> bool:
        """
        Connect to MT5 terminal for a specific broker.

        Args:
            broker: BrokerConfig object with connection details

        Returns:
            True if connection successful, False otherwise
        """
        for attempt in range(1, self.retry_attempts + 1):
            # Check for shutdown request
            if is_shutdown_requested():
                logger.info(f"[{broker.name}] Shutdown requested, aborting connection")
                return False

            try:
                # Shutdown any existing connection first
                mt5.shutdown()

                # Initialize MT5 with broker-specific terminal
                if not mt5.initialize(
                    path=broker.path,
                    login=broker.login,
                    password=broker.password,
                    server=broker.server
                ):
                    error = mt5.last_error()
                    logger.warning(
                        f"[{broker.name}] Connection attempt {attempt}/{self.retry_attempts} "
                        f"failed: {error}"
                    )
                    if attempt < self.retry_attempts:
                        if not interruptible_sleep(self.retry_delay):
                            logger.info(f"[{broker.name}] Shutdown requested during retry wait")
                            return False
                    continue

                # Verify connection
                account_info = mt5.account_info()
                if account_info is None:
                    logger.warning(
                        f"[{broker.name}] Could not get account info on attempt "
                        f"{attempt}/{self.retry_attempts}"
                    )
                    if attempt < self.retry_attempts:
                        if not interruptible_sleep(self.retry_delay):
                            logger.info(f"[{broker.name}] Shutdown requested during retry wait")
                            return False
                    continue

                logger.info(
                    f"[{broker.name}] Connected successfully - "
                    f"Account: {account_info.login}, Server: {account_info.server}"
                )
                return True

            except Exception as e:
                logger.error(
                    f"[{broker.name}] Exception on attempt {attempt}/{self.retry_attempts}: {e}"
                )
                if attempt < self.retry_attempts:
                    if not interruptible_sleep(self.retry_delay):
                        logger.info(f"[{broker.name}] Shutdown requested during retry wait")
                        return False

        logger.error(f"[{broker.name}] Failed to connect after {self.retry_attempts} attempts")
        return False

    def disconnect(self) -> None:
        """Disconnect from MT5 terminal."""
        mt5.shutdown()

    def get_spread_data(
        self,
        broker: BrokerConfig,
        base_symbol: str
    ) -> Optional[SpreadData]:
        """
        Get current spread data for a symbol.

        Args:
            broker: BrokerConfig object (for broker name and symbol suffix)
            base_symbol: Base symbol name (e.g., 'XAUUSD'), suffix will be applied

        Returns:
            SpreadData object if successful, None otherwise
        """
        try:
            # Apply broker-specific symbol suffix
            broker_symbol = base_symbol + broker.get_symbol_suffix(base_symbol)

            # Get symbol info to check if it exists and get point value
            symbol_info = mt5.symbol_info(broker_symbol)
            if symbol_info is None:
                logger.error(f"[{broker.name}] Symbol {broker_symbol} not found")
                return None

            # Force symbol selection to refresh market data
            # First deselect, then reselect to clear any cached data
            mt5.symbol_select(broker_symbol, False)
            if not interruptible_sleep(0.1):
                return None
            if not mt5.symbol_select(broker_symbol, True):
                logger.error(f"[{broker.name}] Failed to select {broker_symbol}")
                return None

            # Wait for fresh tick data to arrive
            if not interruptible_sleep(0.5):
                return None

            # Get current tick using copy_ticks_from for fresh server data
            from datetime import timedelta
            ticks = mt5.copy_ticks_from(broker_symbol, datetime.now(timezone.utc), 1, mt5.COPY_TICKS_ALL)

            if ticks is None or len(ticks) == 0:
                # Fallback to symbol_info_tick
                tick = mt5.symbol_info_tick(broker_symbol)
                if tick is None:
                    logger.error(f"[{broker.name}] Could not get tick for {broker_symbol}")
                    return None
                bid = tick.bid
                ask = tick.ask
            else:
                # Use the latest tick from server
                latest_tick = ticks[-1]
                bid = latest_tick['bid']
                ask = latest_tick['ask']

            # Calculate spread with proper rounding based on symbol digits
            digits = symbol_info.digits
            point = symbol_info.point

            bid = round(bid, digits)
            ask = round(ask, digits)
            spread = round(ask - bid, digits)
            spread_points = int(round(spread / point)) if point > 0 else 0

            # Store base symbol in data (normalized across brokers)
            return SpreadData(
                timestamp=datetime.now(timezone.utc),
                broker=broker.name,
                symbol=base_symbol,
                bid=bid,
                ask=ask,
                spread=spread,
                spread_points=spread_points
            )

        except Exception as e:
            logger.error(f"[{broker.name}] Error getting spread for {base_symbol}: {e}")
            return None

    def collect_from_broker(
        self,
        broker: BrokerConfig,
        symbols: List[str]
    ) -> List[SpreadData]:
        """
        Connect to broker, collect spread data for all symbols, and disconnect.

        Args:
            broker: BrokerConfig object
            symbols: List of symbols to collect data for

        Returns:
            List of SpreadData objects (may be empty if connection failed)
        """
        results = []

        if not self.connect(broker):
            return results

        try:
            for symbol in symbols:
                # Check for shutdown before each symbol
                if is_shutdown_requested():
                    logger.info(f"[{broker.name}] Shutdown requested, stopping symbol collection")
                    break

                spread_data = self.get_spread_data(broker, symbol)
                if spread_data:
                    results.append(spread_data)
                    broker_symbol = symbol + broker.get_symbol_suffix(symbol)
                    logger.debug(
                        f"[{broker.name}] {broker_symbol}: Bid={spread_data.bid:.5f}, "
                        f"Ask={spread_data.ask:.5f}, Spread={spread_data.spread_points} pts"
                    )
        finally:
            self.disconnect()

        return results

    def collect_from_all_brokers(
        self,
        brokers: List[BrokerConfig],
        symbols: List[str]
    ) -> List[SpreadData]:
        """
        Collect spread data from all brokers sequentially.

        Args:
            brokers: List of BrokerConfig objects
            symbols: List of symbols to collect data for

        Returns:
            List of all SpreadData objects collected
        """
        all_results = []

        for broker in brokers:
            # Check for shutdown before starting each broker
            if is_shutdown_requested():
                logger.info("Shutdown requested, stopping collection")
                break

            logger.info(f"Collecting from {broker.name}...")
            results = self.collect_from_broker(broker, symbols)
            all_results.extend(results)

            if results:
                logger.info(f"[{broker.name}] Collected {len(results)} data points")
            else:
                logger.warning(f"[{broker.name}] No data collected")

        return all_results


def load_brokers_from_config(config: Dict) -> List[BrokerConfig]:
    """
    Load broker configurations from config dictionary.

    Args:
        config: Configuration dictionary with 'brokers' key

    Returns:
        List of BrokerConfig objects
    """
    brokers = []
    for broker_data in config.get("brokers", []):
        brokers.append(BrokerConfig(
            name=broker_data["name"],
            server=broker_data["server"],
            login=broker_data["login"],
            password=broker_data["password"],
            path=broker_data["path"],
            symbol_suffix=broker_data.get("symbol_suffix", ""),
            symbol_suffix_overrides=broker_data.get("symbol_suffix_overrides", {})
        ))
    return brokers
