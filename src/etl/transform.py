import pandas as pd
import hashlib
import logging
import unicodedata
import re
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

def clean_currency(val: Any) -> Optional[float]:
    """
    Converts currency string to float.
    Handles 'R$ 1.200,50', '10,5%', '10.5'.
    Removes 'R$', '%', '.', replaces ',' with '.'.
    Treats empty strings/whitespace/NaN as None.
    """
    if pd.isna(val):
        return None
    
    val_str = str(val).strip()
    if not val_str:
        return None
    
    # If it's already a number, just return it
    if isinstance(val, (int, float)):
        return float(val)

    # Check for negative accounting format (parentheses)
    is_negative = False
    if '(' in val_str and ')' in val_str:
        is_negative = True
        val_str = val_str.replace('(', '').replace(')', '')
    elif '-' in val_str:
        # Standard negative
        pass

    # Remove 'R$' and '%' and whitespace
    val_str = val_str.replace('R$', '').replace('%', '').replace(' ', '')
    
    # Remove thousand separator (.) and replace decimal separator (,) with (.)
    val_str = val_str.replace('.', '').replace(',', '.')
    
    try:
        val_float = float(val_str)
        return -val_float if is_negative else val_float
    except ValueError:
        return None

def clean_date(val: Any) -> Optional[Any]:
    """
    Converts string 'DD/MM/YYYY' to datetime.date object.
    Treats empty strings/whitespace/NaN as None.
    """
    if pd.isna(val):
        return None
        
    val_str = str(val).strip()
    if not val_str:
        return None

    # If already datetime/timestamp
    if isinstance(val, (pd.Timestamp, pd.DatetimeIndex)):
        return val.date()
    
    try:
        # dayfirst=True for DD/MM/YYYY
        dt = pd.to_datetime(val, dayfirst=True)
        if pd.isna(dt):
            return None
        return dt.date()
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

    # 4. Concatenate (Unified)
    # Note: We are concatenating first as per original logic structure, 
    # but we will clean the result. 
    # Wait, the prompt said: "Antes de fazer o merge/dedupe, aplique clean_currency... e clean_date code..."
    # Doing it on the concatenated DF is equivalent to doing it on fragments, and easier.
    
    df_total = pd.concat([df_competencia_full, df_caixa_full], ignore_index=True)
    
    if df_total.empty:
        logger.warning("DataFrame unificado vazio.")
        return df_total

    # Apply Cleaning
    if 'Valor' in df_total.columns:
        df_total['Valor'] = df_total['Valor'].apply(clean_currency)
    
    for col in ['Competência', 'Pagamento', 'Cobrança']:
        if col in df_total.columns:
            df_total[col] = df_total[col].apply(clean_date)

    # Force Text Columns to String (safe fallback)
    text_cols = ['Titulo', 'Título', 'Conta Bancária', 'Categoria', 'Fornecedor/Cliente', 'Centro de Custos', 'Observações']
    for col in text_cols:
        if col in df_total.columns:
            # Replace nan with empty string for text columns? 
            # Or keep None? SQL usually prefers NULL.
            # Only convert explicit NaNs to empty string if needed for string operations.
            # Original code did: replace('nan', '').
            # Let's keep it safe.
            df_total[col] = df_total[col].astype(str).replace('nan', '').replace('None', '')

    # Normalize 'Título'
    if 'Título' not in df_total.columns and 'Titulo' in df_total.columns:
         df_total.rename(columns={'Titulo': 'Título'}, inplace=True)

    # Deduplication Strategy
    # Create flag has_payment based on 'Pagamento' (which is now date object or None)
    df_total['has_payment'] = df_total['Pagamento'].notna()
    
    # Sort: has_payment=True first
    df_total.sort_values(by=['has_payment'], ascending=False, inplace=True)
    
    # Generate ID logic
    # We need to ensure types are consistent for ID generation.
    def generate_id(row):
        titulo = str(row.get('Título', '')).strip().lower()
        competencia = str(row.get('Competência', ''))
        valor = str(row.get('Valor', ''))
        raw_string = f"{titulo}{competencia}{valor}"
        return hashlib.md5(raw_string.encode('utf-8')).hexdigest()

    df_total['id_transacao'] = df_total.apply(generate_id, axis=1)

    initial_rows = len(df_total)
    df_total.drop_duplicates(subset=['Título', 'Competência', 'Valor'], keep='first', inplace=True)
    final_rows = len(df_total)
    
    logger.info(f"Deduplicação: {initial_rows} -> {final_rows} (Removidos: {initial_rows - final_rows})")

    df_total.drop(columns=['has_payment'], errors='ignore', inplace=True)
    
    return df_total

def process_generic_data(df_list: List[pd.DataFrame], report_id: str = "") -> pd.DataFrame:
    """
    Standardizes generic report data.
    Concatenates, sanitizes columns, and applies type inference heuristics.
    """
    if not df_list:
        return pd.DataFrame()
    
    # 1. Concatenate
    df = pd.concat(df_list, ignore_index=True)
    
    if df.empty:
        return df

    # 2. Sanitize Column Names
    # Store old names if needed? No, we want clean names in DB.
    new_columns = [clean_column_name(c) for c in df.columns]
    df.columns = new_columns

    # 3. Apply Heuristics
    for col in df.columns:
        # Heuristics based on sanitized names
        
        # Currency/Float
        if any(x in col for x in ['valor', 'custo', 'liquido', 'comissao', 'total', 'taxa', 'faturado']):
            # Special case ID 0126: "taxa_de_ocupacao"
            # clean_currency handles '%' removal.
            df[col] = df[col].apply(clean_currency)
            
        # Date
        elif any(x in col for x in ['data', 'visita', 'nascimento', 'cadastro', 'competencia', 'pagamento', 'cobranca']):
             df[col] = df[col].apply(clean_date)
             
        # Numeric (Int/Float) - strict count/quantity
        elif any(x in col for x in ['qtd', 'numero', 'dias']):
            # Use pd.to_numeric with coercion
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # String fallback? 
        # Leave other columns as is (likely object/string)
        
    logger.info(f"Dados genéricos processados ({report_id}). Rows: {len(df)}")
    return df

def transform_to_dataframe(raw_data: List[Dict], columns: List[str]) -> pd.DataFrame:
    """Converts raw list of dicts to DataFrame with specified columns."""
    if not raw_data:
        return pd.DataFrame(columns=columns)
    df = pd.DataFrame(raw_data, columns=columns)
    return df
