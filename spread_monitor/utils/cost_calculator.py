"""
Trading Cost Calculator Utility

Calculates total trading costs including spread and commission costs.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional


# Point values for common symbols (per standard lot) in AUD
# These represent the value of 1 point movement in AUD for AUD base currency accounts
# Assumes approximate AUDUSD rate of 0.63-0.65
POINT_VALUES_AUD = {
    # Forex pairs (pip values)
    "XAUUSD": 1.55,      # Gold: ~A$1.55 per point per lot (USD 1.00 / 0.645)
    "EURUSD": 15.50,     # EUR/USD: ~A$15.50 per pip per lot
    "GBPUSD": 15.50,     # GBP/USD: ~A$15.50 per pip per lot
    "USDJPY": 10.40,     # USD/JPY: ~A$10.40 per pip (varies with rate)
    "AUDUSD": 15.50,     # AUD/USD: ~A$15.50 per pip per lot
    "USDCAD": 11.60,     # USD/CAD: ~A$11.60 per pip (varies with rate)
    "USDCHF": 17.05,     # USD/CHF: ~A$17.05 per pip (varies with rate)
    "NZDUSD": 15.50,     # NZD/USD: ~A$15.50 per pip per lot
    # Index CFDs (point values - typically $1 USD per point per contract)
    "NAS100": 1.55,      # NASDAQ 100: ~A$1.55 per point
    "US500": 1.55,       # S&P 500: ~A$1.55 per point
    "US30": 1.55,        # Dow Jones 30: ~A$1.55 per point
    "US2000": 1.55,      # Russell 2000: ~A$1.55 per point
    "GER40": 1.75,       # German DAX 40: ~A$1.75 per point (EUR based)
    "UK100": 2.00,       # UK FTSE 100: ~A$2.00 per point (GBP based)
}

# Default point value for unknown symbols (in AUD)
DEFAULT_POINT_VALUE_AUD = 15.50

# Currency symbol for display
CURRENCY_SYMBOL = "A$"
CURRENCY_CODE = "AUD"


@dataclass
class TradingCost:
    """Represents the trading cost breakdown for a broker."""
    broker: str
    avg_spread_points: float
    spread_cost: float
    commission: float
    total_cost: float
    point_value: float
    lot_size: float
    commission_per_lot: float


def get_point_value(symbol: str) -> float:
    """
    Get the point value for a symbol in AUD.

    Args:
        symbol: Trading symbol (e.g., "XAUUSD")

    Returns:
        Point value in AUD per standard lot
    """
    # Remove any suffix and normalize
    base_symbol = symbol.upper().replace(".", "").replace("+", "")

    # Try exact match first
    if base_symbol in POINT_VALUES_AUD:
        return POINT_VALUES_AUD[base_symbol]

    # Try without common suffixes
    for key in POINT_VALUES_AUD:
        if base_symbol.startswith(key) or key.startswith(base_symbol):
            return POINT_VALUES_AUD[key]

    return DEFAULT_POINT_VALUE_AUD


def get_currency_info() -> Dict[str, str]:
    """
    Get currency display information.

    Returns:
        Dictionary with currency symbol and code
    """
    return {
        "symbol": CURRENCY_SYMBOL,
        "code": CURRENCY_CODE
    }


def calculate_spread_cost(
    spread_points: float,
    lot_size: float,
    point_value: float
) -> float:
    """
    Calculate the cost of the spread.

    Args:
        spread_points: Spread in points
        lot_size: Trade size in lots
        point_value: Value of 1 point per standard lot

    Returns:
        Spread cost in AUD
    """
    return spread_points * point_value * lot_size


def calculate_commission_cost(
    commission_per_lot: float,
    lot_size: float
) -> float:
    """
    Calculate the commission cost.

    Args:
        commission_per_lot: Commission per standard lot (round trip) in AUD
        lot_size: Trade size in lots

    Returns:
        Commission cost in AUD
    """
    return commission_per_lot * lot_size


def calculate_total_cost(
    spread_points: float,
    commission_per_lot: float,
    lot_size: float,
    point_value: float
) -> TradingCost:
    """
    Calculate total trading cost for a single broker.

    Args:
        spread_points: Average spread in points
        commission_per_lot: Commission per lot (round trip)
        lot_size: Trade size in lots
        point_value: Value of 1 point per standard lot

    Returns:
        Dictionary with cost breakdown
    """
    spread_cost = calculate_spread_cost(spread_points, lot_size, point_value)
    commission_cost = calculate_commission_cost(commission_per_lot, lot_size)
    total = spread_cost + commission_cost

    return {
        "spread_cost": round(spread_cost, 2),
        "commission": round(commission_cost, 2),
        "total_cost": round(total, 2)
    }


def is_commission_free(symbol: str, commission_free_symbols: List[str]) -> bool:
    """
    Check if a symbol is commission-free based on the broker's exempt list.

    Args:
        symbol: Trading symbol (e.g., "XAUUSD")
        commission_free_symbols: List of symbol prefixes/names that are commission-free

    Returns:
        True if the symbol is commission-free, False otherwise
    """
    if not commission_free_symbols:
        return False

    # Normalize symbol (remove suffixes like .a, .r, +, x, etc.)
    base_symbol = symbol.upper().split('.')[0].rstrip('+').rstrip('x')

    for exempt in commission_free_symbols:
        exempt_upper = exempt.upper()
        # Check if symbol starts with the exempt prefix or matches exactly
        if base_symbol.startswith(exempt_upper) or base_symbol == exempt_upper:
            return True

    return False


def calculate_trading_costs(
    broker_stats: List[Dict],
    broker_commissions: Dict[str, Dict],
    symbol: str,
    lot_size: float = 1.0
) -> List[Dict]:
    """
    Calculate trading costs for all brokers.

    Args:
        broker_stats: List of dicts with broker stats (must include 'broker' and 'avg')
        broker_commissions: Dict mapping broker name to commission info:
            - commission_per_lot: float
            - commission_free_symbols: List[str] (optional)
        symbol: Trading symbol
        lot_size: Trade size in lots

    Returns:
        List of TradingCost dictionaries
    """
    point_value = get_point_value(symbol)
    results = []

    for stat in broker_stats:
        broker_name = stat.get("broker", "Unknown")
        avg_spread = stat.get("avg", 0)

        # Get commission info for this broker
        commission_info = broker_commissions.get(broker_name, {})

        # Handle both old format (float) and new format (dict)
        if isinstance(commission_info, dict):
            base_commission = commission_info.get("commission_per_lot", 0)
            commission_free_list = commission_info.get("commission_free_symbols", [])
        else:
            # Backwards compatibility with old format
            base_commission = commission_info
            commission_free_list = []

        # Check if this symbol is commission-free for this broker
        if is_commission_free(symbol, commission_free_list):
            commission_per_lot = 0
        else:
            commission_per_lot = base_commission

        costs = calculate_total_cost(
            spread_points=avg_spread,
            commission_per_lot=commission_per_lot,
            lot_size=lot_size,
            point_value=point_value
        )

        results.append({
            "broker": broker_name,
            "avg_spread_points": round(avg_spread, 2),
            "spread_cost": costs["spread_cost"],
            "commission": costs["commission"],
            "total_cost": costs["total_cost"],
            "point_value": point_value,
            "lot_size": lot_size,
            "commission_per_lot": commission_per_lot
        })

    # Sort by total cost
    results.sort(key=lambda x: x["total_cost"])

    return results


def get_savings_info(costs: List[Dict]) -> Optional[Dict]:
    """
    Calculate potential savings information.

    Args:
        costs: List of trading cost dictionaries (sorted by total_cost)

    Returns:
        Dictionary with savings information or None if insufficient data
    """
    if len(costs) < 2:
        return None

    best = costs[0]
    worst = costs[-1]

    savings_per_lot = round(worst["total_cost"] - best["total_cost"], 2)
    savings_percent = round((savings_per_lot / worst["total_cost"]) * 100, 1) if worst["total_cost"] > 0 else 0

    return {
        "best_broker": best["broker"],
        "worst_broker": worst["broker"],
        "best_cost": best["total_cost"],
        "worst_cost": worst["total_cost"],
        "savings_per_lot": savings_per_lot,
        "savings_percent": savings_percent
    }


def calculate_basket_costs(
    symbols: List[str],
    symbol_broker_stats: Dict[str, List[Dict]],
    broker_commissions: Dict[str, Dict],
    lot_size: float = 1.0
) -> List[Dict]:
    """
    Calculate trading costs across a basket of symbols for all brokers.

    Args:
        symbols: List of symbols in the basket
        symbol_broker_stats: Dict mapping symbol -> list of broker stats
            Each broker stat must include 'broker' and 'avg' keys
        broker_commissions: Dict mapping broker name to commission info:
            - commission_per_lot: float
            - commission_free_symbols: List[str] (optional)
        lot_size: Trade size in lots (same for all symbols)

    Returns:
        List of dicts with aggregated costs per broker, sorted by total_cost
    """
    # Collect all unique brokers from the data
    all_brokers = set()
    for symbol in symbols:
        for stat in symbol_broker_stats.get(symbol, []):
            all_brokers.add(stat.get("broker"))

    results = []

    for broker_name in all_brokers:
        breakdown = []
        total_spread_cost = 0.0
        total_commission = 0.0
        symbols_with_data = 0

        for symbol in symbols:
            # Find this broker's stats for this symbol
            broker_stat = None
            for stat in symbol_broker_stats.get(symbol, []):
                if stat.get("broker") == broker_name:
                    broker_stat = stat
                    break

            if broker_stat is None:
                # Broker has no data for this symbol - skip it
                continue

            symbols_with_data += 1
            avg_spread = broker_stat.get("avg", 0)
            point_value = get_point_value(symbol)

            # Get commission info for this broker
            commission_info = broker_commissions.get(broker_name, {})
            if isinstance(commission_info, dict):
                base_commission = commission_info.get("commission_per_lot", 0)
                commission_free_list = commission_info.get("commission_free_symbols", [])
            else:
                base_commission = commission_info
                commission_free_list = []

            # Check if this symbol is commission-free for this broker
            if is_commission_free(symbol, commission_free_list):
                commission_per_lot = 0
            else:
                commission_per_lot = base_commission

            # Calculate costs for this symbol
            spread_cost = calculate_spread_cost(avg_spread, lot_size, point_value)
            commission_cost = calculate_commission_cost(commission_per_lot, lot_size)
            symbol_total = spread_cost + commission_cost

            breakdown.append({
                "symbol": symbol,
                "avg_spread_points": round(avg_spread, 2),
                "spread_cost": round(spread_cost, 2),
                "commission": round(commission_cost, 2),
                "total": round(symbol_total, 2),
                "point_value": point_value
            })

            total_spread_cost += spread_cost
            total_commission += commission_cost

        # Only include broker if they have data for at least one symbol
        if symbols_with_data > 0:
            results.append({
                "broker": broker_name,
                "symbol_count": symbols_with_data,
                "total_spread_cost": round(total_spread_cost, 2),
                "total_commission": round(total_commission, 2),
                "total_cost": round(total_spread_cost + total_commission, 2),
                "breakdown": breakdown
            })

    # Sort by total cost
    results.sort(key=lambda x: x["total_cost"])

    return results


def get_basket_savings_info(costs: List[Dict]) -> Optional[Dict]:
    """
    Calculate potential savings information for basket costs.

    Args:
        costs: List of basket trading cost dictionaries (sorted by total_cost)

    Returns:
        Dictionary with savings information or None if insufficient data
    """
    if len(costs) < 2:
        return None

    best = costs[0]
    worst = costs[-1]

    savings_per_trade = round(worst["total_cost"] - best["total_cost"], 2)
    savings_percent = round((savings_per_trade / worst["total_cost"]) * 100, 1) if worst["total_cost"] > 0 else 0

    return {
        "best_broker": best["broker"],
        "worst_broker": worst["broker"],
        "best_cost": best["total_cost"],
        "worst_cost": worst["total_cost"],
        "savings_per_trade": savings_per_trade,
        "savings_percent": savings_percent
    }
