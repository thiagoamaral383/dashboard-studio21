import pandas as pd
import numpy as np
import unicodedata
import re
import logging
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)

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

    # Replace spaces and hyphens with _
    name_clean = re.sub(r'[\s-]+', '_', name_clean)

    # Remove excessive underscores and strip
    name_clean = re.sub(r'_+', '_', name_clean).strip('_')

    return name_clean

def clean_currency_vectorized(series: pd.Series) -> pd.Series:
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

def clean_date_vectorized(series: pd.Series) -> pd.Series:
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

def clean_currency(val: Any) -> Optional[float]:
    """Legacy individual function for single values (fallback)."""
    if pd.isna(val): return None
    try:
        series = pd.Series([val])
        res = clean_currency_vectorized(series)
        return float(res.iloc[0]) if not pd.isna(res.iloc[0]) else None
    except:
        return None

def clean_date(val: Any) -> Optional[Any]:
    """Legacy individual function for single values (fallback)."""
    if pd.isna(val): return None
    try:
        series = pd.Series([val])
        res = clean_date_vectorized(series)
        return res.iloc[0]
    except:
        return None

def transform_to_dataframe(raw_data: List[Dict], columns: List[str]) -> pd.DataFrame:
    """Converts raw list of dicts to DataFrame with specified columns."""
    if not raw_data:
        return pd.DataFrame(columns=columns)
    df = pd.DataFrame(raw_data, columns=columns)
    return df

def process_generic_data(df_list: List[pd.DataFrame], report_id: str = "") -> pd.DataFrame:
    """
    Standardizes generic report data.
    Concatenates, sanitizes columns, and applies type inference heuristics (Vectorized).
    """
    if not df_list:
        return pd.DataFrame()
    
    # 1. Concatenate
    df = pd.concat(df_list, ignore_index=True)
    
    if df.empty:
        return df

    # 2. Sanitize Column Names
    new_columns = [clean_column_name(c) for c in df.columns]
    
    # Deduplicate column names to prevent DataFrame retrieval on simple indexing
    seen = {}
    deduped_columns = []
    for col in new_columns:
        if col in seen:
            seen[col] += 1
            deduped_columns.append(f"{col}_{seen[col]}")
        else:
            seen[col] = 0
            deduped_columns.append(col)
            
    df.columns = deduped_columns

    # 3. Apply Heuristics
    for col in df.columns:
        # Currency/Float
        if any(x in col for x in ['valor', 'custo', 'liquido', 'comissao', 'total', 'taxa', 'faturado']):
            df[col] = clean_currency_vectorized(df[col])
            
        # Date
        elif any(x in col for x in ['data', 'visita', 'nascimento', 'cadastro', 'competencia', 'pagamento', 'cobranca']):
             df[col] = clean_date_vectorized(df[col])
             
        # Numeric (Int/Float) - strict count/quantity
        elif any(x in col for x in ['qtd', 'numero', 'dias']):
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
    # Special Deduplication for Report 0229 (Profissionais)
    if report_id == "0229":
        # Look for 'id' column (it should be lowercase/clean now)
        id_col = 'id'
        if id_col in df.columns:
            initial_count = len(df)
            df.drop_duplicates(subset=[id_col], keep='last', inplace=True)
            final_count = len(df)
            logger.info(f"Deduplicação (0229 - ID): {initial_count} -> {final_count}")
        else:
            logger.warning("Relatório 0229 sem coluna 'id' para deduplicação.")
            
    logger.info(f"Dados genéricos processados ({report_id}). Rows: {len(df)}")
    return df
