"""
Session detection utilities for forex trading sessions.

UTC Times:
- Sydney:    21:00 - 06:00
- London:    07:00 - 16:00
- New York:  12:00 - 21:00
- Overlap:   12:00 - 16:00 (London/NY)
"""

from datetime import datetime
from typing import List


def get_trading_sessions(utc_time: datetime) -> List[str]:
    """
    Determine which trading sessions are active at a given UTC time.

    Args:
        utc_time: datetime object in UTC

    Returns:
        List of active session names
    """
    hour = utc_time.hour
    sessions = []

    # Sydney: 21:00 - 06:00 UTC (crosses midnight)
    if hour >= 21 or hour < 6:
        sessions.append("Sydney")

    # London: 07:00 - 16:00 UTC
    if 7 <= hour < 16:
        sessions.append("London")

    # New York: 12:00 - 21:00 UTC
    if 12 <= hour < 21:
        sessions.append("NewYork")

    return sessions


def get_session_tag(utc_time: datetime) -> str:
    """
    Get a single session tag for the given UTC time.
    Prioritizes Overlap, then specific sessions.

    Args:
        utc_time: datetime object in UTC

    Returns:
        Session tag string (Overlap/London/NewYork/Sydney/Closed)
    """
    sessions = get_trading_sessions(utc_time)

    # Check for London/NY overlap: 12:00 - 16:00 UTC
    if "London" in sessions and "NewYork" in sessions:
        return "Overlap"

    # Return single session or first one if multiple
    if sessions:
        return sessions[0]

    # No major session active (rare edge case)
    return "Closed"


def get_day_of_week(utc_time: datetime) -> str:
    """
    Get the day of week name for a given UTC time.

    Args:
        utc_time: datetime object in UTC

    Returns:
        Day name (Monday, Tuesday, etc.)
    """
    return utc_time.strftime("%A")


def is_market_open(utc_time: datetime) -> bool:
    """
    Check if forex market is likely open (Mon-Fri, excluding weekends).
    Note: Does not account for holidays.

    Args:
        utc_time: datetime object in UTC

    Returns:
        True if market is likely open
    """
    day = utc_time.weekday()
    hour = utc_time.hour

    # Market closed from Friday 21:00 UTC to Sunday 21:00 UTC
    if day == 5:  # Saturday - closed
        return False
    if day == 6 and hour < 21:  # Sunday before 21:00 - closed
        return False
    if day == 4 and hour >= 21:  # Friday after 21:00 - closed
        return False

    return True
