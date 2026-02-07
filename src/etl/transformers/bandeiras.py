import pandas as pd
import logging
from typing import List
from src.etl.cleaning import clean_column_name, clean_currency, clean_date

logger = logging.getLogger(__name__)

def process_bandeiras(df_list: List[pd.DataFrame]) -> pd.DataFrame:
    """
    Process Report 0188 - BandeirasCartao.
    
    Transforms raw data into a clean ledger of Acquirer Fees (Taxas de Maquininha).
    Calculates Net Revenue (Valor Líquido) from Gross Revenue (Valor Faturado).
    
    Args:
        df_list: List of raw DataFrames loaded from Excel/CSV.
        
    Returns:
        pd.DataFrame: Standardized DataFrame with columns:
            ['data_competencia', 'bandeira', 'valor_faturado', 'valor_liquido']
    """
    if not df_list:
        logger.warning("Bandeiras: Lista de DataFrames vazia.")
        return pd.DataFrame(columns=['data_competencia', 'bandeira', 'valor_faturado', 'valor_liquido'])

    # 1. Concatenate
    df = pd.concat(df_list, ignore_index=True)
    
    if df.empty:
        return pd.DataFrame(columns=['data_competencia', 'bandeira', 'valor_faturado', 'valor_liquido'])

    # 2. Sanitize Column Names
    # Expecting: 'Bandeira', 'Valor Faturado', 'Valor' (Liquido), 'Data' (Competencia)
    df.columns = [clean_column_name(c) for c in df.columns]
    
    # 3. Rename Columns to Standard Schema
    rename_map = {
        'valor': 'valor_liquido',
        # 'valor_faturado' usually comes as 'valor_faturado' after cleaning 'Valor Faturado'
        # 'bandeira' comes as 'bandeira'
        # 'data_competencia' might come as 'data' or 'competencia' depending on extract.py injection
        # but User said "A coluna de data já deve vir injetada do extract.py como data_competencia"
    }
    df.rename(columns=rename_map, inplace=True)
    
    # Ensure all required columns exist
    required_cols = ['data_competencia', 'bandeira', 'valor_faturado', 'valor_liquido']
    for col in required_cols:
        if col not in df.columns:
            logger.warning(f"Bandeiras: Coluna esperada '{col}' não encontrada. Criando com nulos.")
            df[col] = None

    # 4. Data Cleaning & Type Conversion
    
    # A. Bandeira (Title Case, Default "NÃO IDENTIFICADO")
    df['bandeira'] = df['bandeira'].fillna("NÃO IDENTIFICADO").astype(str).str.strip().str.title()
    
    # B. Values (Currency -> Float) - CRITICAL: Apply cleaning to both Gross and Net
    # Handle text formats like "R$ 1.200,50"
    df['valor_faturado'] = clean_currency(df['valor_faturado'])
    df['valor_liquido'] = clean_currency(df['valor_liquido'])
    
    # Fill numeric nulls with 0.0
    df['valor_faturado'] = df['valor_faturado'].fillna(0.0)
    df['valor_liquido'] = df['valor_liquido'].fillna(0.0)
    
    # C. Dates
    df['data_competencia'] = clean_date(df['data_competencia'])

    # 5. Final Selection
    df_out = df[required_cols].copy()
    
    logger.info(f"Bandeiras 0188 processado: {len(df_out)} registros.")
    
    return df_out
