"""
Formatting utility module for Studio21 Dashboard.
Provides consistent formatting for currency, percentages, and compact numbers.
"""

from typing import Optional, Union, Tuple
from datetime import date, timedelta


# ============================================================================
# DATE UTILITIES
# ============================================================================

def calculate_previous_period(start_date: date, end_date: date) -> Tuple[date, date]:
    """
    Calculate the previous period with the same duration (PoP).
    
    For example, if the current period is 30 days (Jan 1 - Jan 30),
    the previous period will be the 30 days immediately before (Dec 2 - Dec 31).
    
    Args:
        start_date: Start date of the current period
        end_date: End date of the current period
        
    Returns:
        Tuple of (previous_start_date, previous_end_date)
    """
    # Calculate the duration of the current period
    duration_days = (end_date - start_date).days
    
    # Previous period ends one day before the current start
    previous_end = start_date - timedelta(days=1)
    
    # Previous period starts duration_days before the previous end
    previous_start = previous_end - timedelta(days=duration_days)
    
    return (previous_start, previous_end)


def calculate_same_period_last_year(start_date: date, end_date: date) -> Tuple[date, date]:
    """
    Calculate the same period in the previous year (YoY).
    Uses 365 days for fiscal alignment as per business rules.
    
    Args:
        start_date: Start date of the current period
        end_date: End date of the current period
        
    Returns:
        Tuple of (yoy_start_date, yoy_end_date)
    """
    # Simply subtract 365 days from both start and end dates
    yoy_start = start_date - timedelta(days=365)
    yoy_end = end_date - timedelta(days=365)
    
    return (yoy_start, yoy_end)


# ============================================================================
# FORMATTING UTILITIES
# ============================================================================

def format_currency(value: Union[float, int], show_sign: bool = False) -> str:
    """
    Format a number as Brazilian Real currency.
    
    Args:
        value: Numeric value to format
        show_sign: If True, include '+' for positive values
        
    Returns:
        Formatted currency string (e.g., "R$ 12.345,67")
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "R$ 0,00"
    
    # Handle negative values
    is_negative = value < 0
    abs_value = abs(value)
    
    # Format with thousands separator and 2 decimals
    formatted = f"{abs_value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    
    # Add currency symbol and sign
    if is_negative:
        return f"R$ -{formatted}"
    elif show_sign and value > 0:
        return f"R$ +{formatted}"
    else:
        return f"R$ {formatted}"


def format_percentage(value: Union[float, int], decimals: int = 1, show_sign: bool = False) -> str:
    """
    Format a number as a percentage.
    
    Args:
        value: Numeric value to format (e.g., 0.125 for 12.5%)
        decimals: Number of decimal places
        show_sign: If True, include '+' for positive values
        
    Returns:
        Formatted percentage string (e.g., "12,5%")
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "0,0%"
    
    # Convert to percentage (multiply by 100)
    percentage = value * 100
    
    # Handle negative values
    is_negative = percentage < 0
    abs_percentage = abs(percentage)
    
    # Format with specified decimals
    formatted = f"{abs_percentage:.{decimals}f}".replace(".", ",")
    
    # Add sign
    if is_negative:
        return f"-{formatted}%"
    elif show_sign and percentage > 0:
        return f"+{formatted}%"
    else:
        return f"{formatted}%"


def format_compact(value: Union[float, int]) -> str:
    """
    Format large numbers in compact notation (K, M, B).
    
    Args:
        value: Numeric value to format
        
    Returns:
        Compact formatted string (e.g., "12,3K", "1,5M")
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "0"
    
    abs_value = abs(value)
    sign = "-" if value < 0 else ""
    
    if abs_value >= 1_000_000_000:
        formatted = f"{abs_value / 1_000_000_000:.1f}".replace(".", ",")
        return f"{sign}{formatted}B"
    elif abs_value >= 1_000_000:
        formatted = f"{abs_value / 1_000_000:.1f}".replace(".", ",")
        return f"{sign}{formatted}M"
    elif abs_value >= 1_000:
        formatted = f"{abs_value / 1_000:.1f}".replace(".", ",")
        return f"{sign}{formatted}K"
    else:
        return f"{sign}{abs_value:.0f}"


def format_delta(
    value: Union[float, int],
    is_percentage: bool = False,
    is_currency: bool = True,
    show_sign: bool = True
) -> tuple[str, str]:
    """
    Format a delta value with appropriate coloring.
    Used for Period-over-Period (PoP) and Year-over-Year (YoY) comparisons.
    
    Args:
        value: Delta value to format
        is_percentage: If True, format as percentage
        is_currency: If True, format as currency (when is_percentage is False)
        show_sign: If True, include '+' for positive values
        
    Returns:
        Tuple of (formatted_string, color)
        color is one of: "normal", "inverse", "off"
        - "normal": green for positive, red for negative
        - "inverse": red for positive, green for negative (for costs/expenses)
        - "off": gray (no color indication)
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ("0", "off")
    
    # Determine color based on sign
    if value > 0:
        color = "normal"  # Green for positive by default
    elif value < 0:
        color = "inverse"  # Red for negative by default
    else:
        color = "off"  # Gray for zero
    
    # Format the value
    if is_percentage:
        formatted = format_percentage(value, decimals=1, show_sign=show_sign)
    elif is_currency:
        formatted = format_currency(value, show_sign=show_sign)
    else:
        # Format as plain number
        formatted = f"{value:+,.0f}" if show_sign else f"{value:,.0f}"
        formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
    
    return (formatted, color)


def format_number(value: Union[float, int], decimals: int = 0) -> str:
    """
    Format a number with thousands separator (Brazilian standard).
    
    Args:
        value: Numeric value to format
        decimals: Number of decimal places
        
    Returns:
        Formatted number string (e.g., "12.345,67")
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "0"
    
    formatted = f"{value:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return formatted


# Import pandas for isna checks
import pandas as pd
