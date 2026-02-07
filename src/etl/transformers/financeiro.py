import pandas as pd
import hashlib
import logging
from typing import List, Dict, Optional, Any, Tuple
from src.etl.cleaning import clean_currency, clean_date

logger = logging.getLogger(__name__)

def process_financeiro(data: Tuple[List[pd.DataFrame], List[pd.DataFrame]]) -> pd.DataFrame:
    """
    Unified transformer for Report 0387 (Financeiro).
    
    Processes a tuple of two lists:
    1. Lista Caixa (Cash Basis)
    2. Lista Competência (Accrual Basis)
    
    Steps:
    - Pre-process each independent stream (Standardize column names).
    - Concatenate (Stack).
    - Apply robust cleaning (Values, Dates, Text).
    - Generate Dimension Keys (MD5 Hashes).
    - Return final 'Fato Financeiro' with native dtypes.
    """
    lista_caixa, lista_competencia = data

    # =========================================================================
    # 1. PRE-PROCESS & CONCATENATE STREAMS
    # =========================================================================
    
    # --- Helper to define standardize mapping ---
    # Target Schema for internal processing before final selection
    # We map source columns to these standardized names
    # Note: 'Valor' in source might be 'Valor Pago', 'Valor', etc.
    # checking source patterns from previous analysis:
    # 'Pagamento', 'Competência', 'Valor', 'Título', 'Conta Bancária', 'Categoria', 'Fornecedor/Cliente', 'Centro de Custos', 'Observações'

    def standardize_stream(df_list: List[pd.DataFrame], stream_type: str) -> pd.DataFrame:
        if not df_list:
            return pd.DataFrame()
        
        df = pd.concat(df_list, ignore_index=True)
        
        if df.empty:
            return df

        # Standardize Names immediately to avoid mismatch during concat
        # Using a mapping strategy. Keys = Source (potential), Value = Target
        
        rename_map = {
            # Dates
            'Pagamento': 'data_movimento',
            'Competência': 'data_movimento',
            'Data': 'data_movimento',
            
            # Values
            'Valor': 'valor',
            'Valor Pago': 'valor',
            'Valor Previsto': 'valor',
            
            # Dimensions
            'Título': 'titulo',
            'Titulo': 'titulo',
            'Categoria': 'categoria',
            'Conta Bancária': 'conta_bancaria',
            'Conta Bancaria': 'conta_bancaria',
            'Fornecedor/Cliente': 'fornecedor_cliente',
            'Centro de Custos': 'centro_de_custos',
            'Observações': 'observacoes',
            'Observacoes': 'observacoes'
        }
        
        df.rename(columns=rename_map, inplace=True)
        
        # Enforce 'tipo' column
        df['tipo'] = stream_type
        
        # Ensure 'observacoes' exists if missing (common in some sources)
        if 'observacoes' not in df.columns:
            df['observacoes'] = "Não Informado"

        return df

    # Process Streams
    df_caixa = standardize_stream(lista_caixa, 'Caixa')
    df_competencia = standardize_stream(lista_competencia, 'Competencia')
    
    # Concatenate Unified
    # This ensures columns align perfectly because we renamed them above.
    df_final = pd.concat([df_caixa, df_competencia], ignore_index=True)
    
    if df_final.empty:
        logger.warning("Fato Financeiro: Sem dados para processar (Inputs vazios).")
        return pd.DataFrame(columns=['data_movimento', 'valor', 'tipo'])

    logger.info(f"Fato Financeiro Unificada: {len(df_final)} linhas (Caixa={len(df_caixa)}, Competencia={len(df_competencia)})")

    # =========================================================================
    # 2. DATA CLEANING & ENRICHMENT
    # =========================================================================

    # --- A. Dates ---
    if 'data_movimento' in df_final.columns:
        df_final['data_movimento'] = clean_date(df_final['data_movimento'])
    
    # --- B. Values (Currency) ---
    if 'valor' in df_final.columns:
        # clean_currency handles '(100.00)' as -100.00
        df_final['valor'] = clean_currency(df_final['valor'])
        # Fill NaN values with 0.0 to allow math ops (safe assumption for financial ledger? or drop?)
        # Usually better to keep NaN if it's really unknown, but for sums, 0 is safer. 
        # Requirement said "Clean" not "Fill", but for finance, 0.0 is better than NaN for aggregation.
        df_final['valor'] = df_final['valor'].fillna(0.0)

    # --- C. Text Normalization ---
    text_cols = ['categoria', 'fornecedor_cliente', 'centro_de_custos', 'conta_bancaria', 'observacoes', 'titulo']
    
    for col in text_cols:
        if col not in df_final.columns:
            df_final[col] = "Não Informado"
        
        # Convert to string, cleanup nan
        df_final[col] = df_final[col].fillna("Não Informado").astype(str)
        # Remove whitespace
        df_final[col] = df_final[col].str.strip()
        
    # Specific Cases
    # Categoria: UPPER CASE
    df_final['categoria'] = df_final['categoria'].str.upper()
    
    # Fornecedor/Cliente/Centro/Conta: Title Case
    for col in ['fornecedor_cliente', 'centro_de_custos', 'conta_bancaria', 'titulo']:
        df_final[col] = df_final[col].str.title()
        
    # Handle empty strings that might have resulted from stripping (e.g. "   " -> "")
    # Replace "" with "Não Informado" again to be safe
    for col in text_cols:
        mask_empty = df_final[col] == ""
        df_final.loc[mask_empty, col] = "Não Informado"

    # =========================================================================
    # 3. GENERATE KEYS (Foreign Keys & Primary Keys)
    # =========================================================================

    # Helper for MD5
    def generate_hash_vectorized(series: pd.Series) -> pd.Series:
        # Ensure string, strip, upper for consistency in Keys
        s_clean = series.astype(str).str.strip().str.upper()
        return s_clean.apply(lambda x: hashlib.md5(x.encode('utf-8')).hexdigest())

    # ID Categoria
    df_final['id_categoria'] = generate_hash_vectorized(df_final['categoria'])
    
    # ID Entidade (Fornecedor/Cliente)
    df_final['id_entidade'] = generate_hash_vectorized(df_final['fornecedor_cliente'])

    # =========================================================================
    # 4. FINAL SELECTION
    # =========================================================================
    
    final_cols = [
        'data_movimento',
        'tipo',
        'id_categoria',
        'id_entidade',
        'categoria',
        'fornecedor_cliente',
        'valor',
        'conta_bancaria',
        'centro_de_custos',
        'observacoes',
        'titulo'
    ]
    
    # Select only existing columns from the list
    existing_cols = [c for c in final_cols if c in df_final.columns]
    
    df_out = df_final[existing_cols].copy()
    
    # Final Type Cast
    df_out['valor'] = df_out['valor'].astype('float64')
    # data_movimento is object (date) or NaT, pandas handles well as object for export, 
    # but let's ensure it's not string if possible. clean_date_vectorized returns objects (datetime.date).
    
    return df_out
