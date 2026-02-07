import pandas as pd
import hashlib
import logging
from typing import List
from src.etl.cleaning import clean_column_name

logger = logging.getLogger(__name__)

def clean_text_field(series: pd.Series) -> pd.Series:
    """Normalizes text fields: UPPER CASE, Strip, handle nulls."""
    return series.fillna('NÃO INFORMADO').astype(str).str.strip().str.upper()

def clean_cpf(series: pd.Series) -> pd.Series:
    """
    Cleans CPF:
    1. Force to string to preserve leading zeros.
    2. Remove punctuation (., -).
    3. Handle nulls/empty strings -> 'Não Informado'.
    """
    # Force string, handle NaNs first
    s = series.fillna('').astype(str).str.strip()
    
    # Remove punctuation
    s = s.str.replace(r'[.-]', '', regex=True)
    
    # Replace empty or 'nan' string with default
    s = s.replace(['', 'nan', 'None'], 'NÃO INFORMADO')
    
    return s

def generate_id(nome: str) -> str:
    """Generates MD5 hash from the normalized name."""
    if not nome or nome == 'NÃO INFORMADO':
        return 'UNKNOWN'
    return hashlib.md5(nome.encode('utf-8')).hexdigest()

def process_profissionais(df_list: List[pd.DataFrame]) -> pd.DataFrame:
    """
    Processes Report 0229 - Profissionais.
    Arguments:
        df_list: List containing a single DataFrame (report_type="sem_data").
    Returns:
        pd.DataFrame: Cleaned and transformed Professionals dimension.
    """
    if not df_list or df_list[0].empty:
        logger.warning("Relatório 0229 (Profissionais) vazio ou inválido.")
        return pd.DataFrame(columns=['id_profissional', 'nome', 'apelido', 'cargo', 'cpf', 'especialidade', 'data_cadastro'])
        
    # 1. Extract single DataFrame
    df = df_list[0].copy()
    
    # 2. Sanitize Column Names
    df.columns = [clean_column_name(c) for c in df.columns]
    
    # 3. Rename essential columns if needed (mapping heuristic)
    # Depending on raw data, these might be named differently. Assuming standard input.
    # Common mappings: 'Profissional' -> 'nome', 'CPF' -> 'cpf', etc.
    # If the raw report already has specific headers, clean_column_name handles it.
    # We expect: 'nome', 'apelido', 'cargo', 'cpf', 'especialidade'
    
    # 4. Data Cleaning & Type Enforcement
    if 'nome' not in df.columns:
         logger.error("Coluna 'nome' não encontrada no relatório 0229.")
         return pd.DataFrame() # Fail gracefully or raise
         
    # Clean Text Fields
    df['nome'] = clean_text_field(df['nome'])
    
    # Preventative Deduplication on Name (before ID generation)
    initial_rows = len(df)
    df.drop_duplicates(subset=['nome'], inplace=True)
    deduped_rows = len(df)
    if initial_rows != deduped_rows:
        logger.info(f"Profissionais: Deduplicado {initial_rows - deduped_rows} registros duplicados pelo nome.")

    # Apply other cleaning
    for col in ['apelido', 'cargo', 'especialidade']:
        if col in df.columns:
            df[col] = clean_text_field(df[col])
        else:
            df[col] = 'Não Informado'
            
    # Clean CPF specifically
    if 'cpf' in df.columns:
        df['cpf'] = clean_cpf(df['cpf'])
    else:
        df['cpf'] = 'Não Informado'
        
    # Data Cadastro - simple clean if exists
    if 'data_cadastro' in df.columns:
        df['data_cadastro'] = pd.to_datetime(df['data_cadastro'], errors='coerce')
    else:
        df['data_cadastro'] = pd.NaT

    # 5. ID Generation (MD5 of Name)
    # This aligns with the fact table logic for seamless joining
    df['id_profissional'] = df['nome'].apply(generate_id)
    
    # 6. Add UNKNOWN Row (Simulated)
    unknown_row = {
        'id_profissional': 'UNKNOWN',
        'nome': 'NÃO IDENTIFICADO',
        'apelido': 'N/I',
        'cargo': 'NÃO INFORMADO',
        'cpf': 'NÃO INFORMADO',
        'especialidade': 'NÃO INFORMADO',
        'data_cadastro': pd.NaT
    }
    df_unknown = pd.DataFrame([unknown_row])
    
    # 7. Select Final Columns
    final_cols = ['id_profissional', 'nome', 'apelido', 'cargo', 'cpf', 'especialidade', 'data_cadastro']
    
    # Filter only available columns (in case some are missing from source, but we handled them above)
    transformed_df = pd.concat([df_unknown, df[final_cols]], ignore_index=True)
    
    logger.info(f"Profissionais processados: {len(transformed_df)} registros.")
    
    return transformed_df
