import pandas as pd
import hashlib
import logging
import unicodedata
import re
from typing import List, Dict, Optional, Any
import numpy as np

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
    # Given the warning "falling back to dateutil", it implies some dates might be non-standard.
    # We try strict first, if that produces too many NaTs, we might need a backup.
    # However, for now, let's try to be explicit about the expected format.
    dt_series = pd.to_datetime(series, format='%d/%m/%Y', errors='coerce')
    
    # If all NaT (and input wasn't empty), maybe format was wrong? 
    # But usually this dataset is DD/MM/YYYY.
    # To be safe against the warning while allowing fallback:
    # We can use a different approach or just ignore the warning if we accept the diversity.
    # But the user specifically asked about the warning.
    # Alternative:
    # dt_series = pd.to_datetime(series, dayfirst=True, errors='coerce') 
    # The warning comes because efficient parsing failed.
    # Let's try to enforce the format as primary.
    
    # Return as date objects (object dtype), or keep as datetime64[ns]?
    # Motherduck/DuckDB handles datetime64[ns] well.
    # However, existing logic (and user preference for 'date' object in DF?)
    # usually .dt.date results in object dtype which is fine for upload but slower.
    # Let's keep it as datetime64[ns] if possible, or object if strictly needed.
    # The previous code returned `dt.date()`. Let's stick to that for compatibility.
    
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

def process_data(lista_caixa: List[pd.DataFrame], lista_competencia: List[pd.DataFrame]) -> pd.DataFrame:
    """
    Unifies Lists of Caixa and Competencia DataFrames (Report 0387).
    Refactored to apply robust typing before merge.
    """
    # 1. Concatenate Lists
    df_caixa_full = pd.concat(lista_caixa, ignore_index=True) if lista_caixa else pd.DataFrame()
    df_competencia_full = pd.concat(lista_competencia, ignore_index=True) if lista_competencia else pd.DataFrame()

    logger.info(f"Consolidando: Caixa={len(df_caixa_full)}, Competencia={len(df_competencia_full)}")

    df_total = pd.concat([df_competencia_full, df_caixa_full], ignore_index=True)
    
    if df_total.empty:
        logger.warning("DataFrame unificado vazio.")
        return df_total

    # Apply Cleaning (Vectorized)
    if 'Valor' in df_total.columns:
        df_total['Valor'] = clean_currency_vectorized(df_total['Valor'])
    
    for col in ['Competência', 'Pagamento', 'Cobrança']:
        if col in df_total.columns:
            df_total[col] = clean_date_vectorized(df_total[col])

    # Force Text Columns to String
    text_cols = ['Titulo', 'Título', 'Conta Bancária', 'Categoria', 'Fornecedor/Cliente', 'Centro de Custos', 'Observações']
    for col in text_cols:
        if col in df_total.columns:
            df_total[col] = df_total[col].astype(str).replace('nan', '').replace('None', '')

    # Normalize 'Título'
    if 'Título' not in df_total.columns and 'Titulo' in df_total.columns:
         df_total.rename(columns={'Titulo': 'Título'}, inplace=True)

    # Deduplication Strategy
    # Create flag has_payment based on 'Pagamento' (assuming NaT/None is falsey or check .notna())
    # Since clean_date_vectorized returns objects (date or NaT/None), notna() works.
    df_total['has_payment'] = df_total['Pagamento'].notna()
    
    # Sort: has_payment=True first
    df_total.sort_values(by=['has_payment'], ascending=False, inplace=True)
    
    # Generate ID logic
    # Vectorized ID generation is hard with custom logic, but we can do:
    # (Titulo + Competencia + Valor).apply(hash) 
    # Must ensure string conversion first.
    def generate_id_vectorized(df):
        s_titulo = df.get('Título', pd.Series([''] * len(df))).fillna('').astype(str).str.strip().str.lower()
        s_comp = df.get('Competência', pd.Series([''] * len(df))).astype(str)
        s_valor = df.get('Valor', pd.Series([''] * len(df))).astype(str)
        
        raw = s_titulo + s_comp + s_valor
        return raw.apply(lambda x: hashlib.md5(x.encode('utf-8')).hexdigest())

    df_total['id_transacao'] = generate_id_vectorized(df_total)

    initial_rows = len(df_total)
    df_total.drop_duplicates(subset=['Título', 'Competência', 'Valor'], keep='first', inplace=True)
    final_rows = len(df_total)
    
    logger.info(f"Deduplicação: {initial_rows} -> {final_rows} (Removidos: {initial_rows - final_rows})")

    df_total.drop(columns=['has_payment'], errors='ignore', inplace=True)
    
    return df_total

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
            # Special check: prevent cleaning if it looks like ID or something else? 
            # Assuming names are descriptive.
            df[col] = clean_currency_vectorized(df[col])
            
        # Date
        elif any(x in col for x in ['data', 'visita', 'nascimento', 'cadastro', 'competencia', 'pagamento', 'cobranca']):
             df[col] = clean_date_vectorized(df[col])
             
        # Numeric (Int/Float) - strict count/quantity
        elif any(x in col for x in ['qtd', 'numero', 'dias']):
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
    # Special Deduplication for Report 0229 (Profissionais)
    if report_id == "0229":
        # Look for 'id' column (it should be lowercase/clean now)
        id_col = 'id'
        if id_col in df.columns:
            initial_count = len(df)
            # Keep 'last' assuming the last extracted month might have the most recent status, 
            # or 'first' if we just want to ignore duplicates. 
            # User example: active in 2023-09 and 2023-10 -> same professional.
            # Usually we want the latest state? Or just unique ID.
            # Let's keep 'last' to be safe with updates.
            df.drop_duplicates(subset=[id_col], keep='last', inplace=True)
            final_count = len(df)
            logger.info(f"Deduplicação (0229 - ID): {initial_count} -> {final_count}")
        else:
            logger.warning("Relatório 0229 sem coluna 'id' para deduplicação.")
            
    logger.info(f"Dados genéricos processados ({report_id}). Rows: {len(df)}")
    return df

def transform_to_dataframe(raw_data: List[Dict], columns: List[str]) -> pd.DataFrame:
    """Converts raw list of dicts to DataFrame with specified columns."""
    if not raw_data:
        return pd.DataFrame(columns=columns)
    df = pd.DataFrame(raw_data, columns=columns)
    return df
