import pandas as pd
import hashlib
import logging
from typing import List, Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

def load_excel_history(folder_path: Path, file_filter: str = "*") -> pd.DataFrame:
    """
    Loads and concatenates all Excel files from a directory that match the filter.
    Security: Only allows files matching specific patterns to avoid loops.
    """
    if not folder_path.exists():
        logger.warning(f"Path not found: {folder_path}")
        return pd.DataFrame()

    all_files = list(folder_path.glob(file_filter))
    
    # Security Filter: Enforce "Caixa" or "Competência" in filename if filter is generic
    # The user explicitly asked to filter for these to avoid reading 'Controle Studio21.xlsx' or temps.
    valid_files = []
    for f in all_files:
        name_lower = f.name.lower()
        if "caixa" in name_lower or "competência" in name_lower or "competencia" in name_lower:
             valid_files.append(f)
        else:
            logger.debug(f"Skipping file {f.name} (does not match safe patterns)")
            
    if not valid_files:
        logger.info(f"No valid history files found in {folder_path}")
        return pd.DataFrame()

    df_list = []
    for f in valid_files:
        try:
            df = pd.read_excel(f)
            df_list.append(df)
        except Exception as e:
            logger.error(f"Error reading {f}: {e}")

    if not df_list:
        return pd.DataFrame()
        
    return pd.concat(df_list, ignore_index=True)

def _clean_currency(val):
    """Converts '1.200,50' string to 1200.50 float."""
    if isinstance(val, (int, float)):
        return float(val)
    if pd.isna(val) or val == '':
        return 0.0
    
    val_str = str(val).strip()
    # Remove thousand separator (.) and replace decimal separator (,)
    val_str = val_str.replace('.', '').replace(',', '.')
    try:
        return float(val_str)
    except ValueError:
        return 0.0

def process_financial_data(df_competencia: pd.DataFrame, df_caixa: pd.DataFrame) -> pd.DataFrame:
    """
    Unifies Competencia and Caixa reports, deduplicates, and generates a surrogate key.
    """
    # 1. Standardization
    # Convert Currency
    if 'Valor' in df_competencia.columns:
        df_competencia['Valor'] = df_competencia['Valor'].apply(_clean_currency)
    if 'Valor' in df_caixa.columns:
        df_caixa['Valor'] = df_caixa['Valor'].apply(_clean_currency)

    # Convert Dates
    # Using dayfirst=True as requested for DD/MM/YYYY
    for df in [df_competencia, df_caixa]:
        if 'Competência' in df.columns:
            df['Competência'] = pd.to_datetime(df['Competência'], dayfirst=True, errors='coerce')
        if 'Pagamento' in df.columns:
            df['Pagamento'] = pd.to_datetime(df['Pagamento'], dayfirst=True, errors='coerce')

    # Force Text Columns to String (Fix for DuckDB Schema Inference)
    text_cols = ['Titulo', 'Título', 'Conta Bancária', 'Categoria', 'Fornecedor/Cliente', 'Centro de Custos', 'Observações']
    for df in [df_competencia, df_caixa]:
        for col in text_cols:
            if col in df.columns:
                df[col] = df[col].astype(str)

    # 2. Merge
    df_total = pd.concat([df_competencia, df_caixa], ignore_index=True)

    # 3. Deduplication Strategy (Priority to 'Pagamento')
    # Create flag has_payment
    df_total['has_payment'] = df_total['Pagamento'].notna()
    
    # Sort: has_payment=True first
    df_total.sort_values(by=['has_payment'], ascending=False, inplace=True)
    
    # Drop duplicates based on Composite Key (Título, Competência, Valor)
    # Keeping 'first' which is the one with payment (if exists)
    df_total.drop_duplicates(subset=['Título', 'Competência', 'Valor'], keep='first', inplace=True)

    # 4. ID Creation (Surrogate Key)
    def generate_id(row):
        # Normalize fields: Lowercase, Strip
        titulo = str(row['Título']).strip().lower() if pd.notna(row['Título']) else ""
        competencia = str(row['Competência']) if pd.notna(row['Competência']) else ""
        valor = str(row['Valor']) # Float already normalized
        
        raw_string = f"{titulo}{competencia}{valor}"
        return hashlib.md5(raw_string.encode('utf-8')).hexdigest()

    df_total['id_transacao'] = df_total.apply(generate_id, axis=1)

    # 5. Final Cleanup
    df_total.drop(columns=['has_payment'], errors='ignore', inplace=True)
    
    return df_total

def transform_to_dataframe(raw_data: List[Dict], columns: List[str]) -> pd.DataFrame:
    """Converts raw list of dicts to DataFrame with specified columns."""
    if not raw_data:
        return pd.DataFrame(columns=columns)
    
    df = pd.DataFrame(raw_data, columns=columns)
    return df
