import pandas as pd
import numpy as np
import unicodedata
import re
from typing import List, Dict, Optional, Any

def clean_column_name(name: str) -> str:
    """
    Sanitizes column names: removes accents, special chars, spaces to underscores, lowercase.
    Example: "Total Consumido" -> "total_consumido"
    """
    if not isinstance(name, str):
        return str(name)

    # Normalize unicode to ASCII (remove accents)
    nfkd_form = unicodedata.normalize('NFKD', name)
    name_ascii = "".join([c for c in nfkd_form if not unicodedata.combining(c)])

    # Lowercase
    name_clean = name_ascii.lower()

    # Remove special characters like %, ., (, )
    # We keep alphanumeric and underscores.
    name_clean = re.sub(r'[().%]', '', name_clean)

    # Replace spaces, slashes and hyphens with _
    name_clean = re.sub(r'[\s/-]+', '_', name_clean)

    # Remove excessive underscores and strip
    name_clean = re.sub(r'_+', '_', name_clean).strip('_')

    return name_clean

def clean_currency(series: pd.Series) -> pd.Series:
    """
    Vectorized currency cleaning.
    Handles 'R$ 1.200,50', '10,5%', '10.5'.
    
    CRITICAL ORDER:
    1. Remove 'R$', '%', ' ' (whitespace)
    2. Handle negative parentheses: '(100)' -> '-100'
    3. Remove THOUSANDS separator (.) -> '1.200,50' becomes '1200,50'
    4. Replace DECIMAL separator (,) with (.) -> '1200,50' becomes '1200.50'
    5. Convert to float
    """
    if series.empty:
        return series
        
    s = series.astype(str).str.strip()
    
    # Handle negatives in parentheses (Accounting format)
    # Mark where they are
    mask_neg = s.str.startswith('(') & s.str.endswith(')')
    
    # Remove chars
    s = s.str.replace(r'[R$%\s()]', '', regex=True)
    
    # Remove thousand separator (.) BEFORE decimal
    s = s.str.replace('.', '', regex=False)
    
    # Replace decimal separator (,) with (.)
    s = s.str.replace(',', '.', regex=False)
    
    # Convert to numeric
    vals = pd.to_numeric(s, errors='coerce')
    
    # Apply negatives
    vals = np.where(mask_neg, -vals, vals)
    
    return pd.Series(vals, index=series.index)

def clean_date(series: pd.Series) -> pd.Series:
    """
    Vectorized date cleaning.
    Expects DD/MM/YYYY or similar.
    Returns datetime.date objects (or NaT).
    """
    if series.empty:
        return series
        
    # Coerce to datetime with explicit format to suppress warnings and improve speed
    # If standard format fails, we could try fallback, but 'coerce' will just return NaT.
    dt_series = pd.to_datetime(series, format='%d/%m/%Y', errors='coerce')
    
    return dt_series.dt.date
