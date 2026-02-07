import pandas as pd
import hashlib
import logging
from typing import List, Dict, Optional, Any, Tuple
from .generico import clean_currency_vectorized, clean_date_vectorized

logger = logging.getLogger(__name__)

def process_financeiro(data: Tuple[List[pd.DataFrame], List[pd.DataFrame]]) -> pd.DataFrame:
    """
    Unifies Lists of Caixa and Competencia DataFrames (Report 0387).
    Refactored to apply robust typing before merge.
    
    Args:
        data: Tuple containing (lista_caixa, lista_competencia)
    """
    lista_caixa, lista_competencia = data
    
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
    # Create flag has_payment based on 'Pagamento'
    df_total['has_payment'] = df_total['Pagamento'].notna()
    
    # Sort: has_payment=True first
    df_total.sort_values(by=['has_payment'], ascending=False, inplace=True)
    
    # Generate ID logic
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
