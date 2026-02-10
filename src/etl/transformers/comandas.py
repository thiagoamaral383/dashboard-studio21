import pandas as pd
import hashlib
import logging
from typing import List, Dict, Optional, Any
from src.etl.cleaning import clean_column_name, clean_currency, clean_date

logger = logging.getLogger(__name__)

def process_comandas(df_list: List[pd.DataFrame]) -> pd.DataFrame:
    """
    Processes 'Fato Comandas' (Report 0186).
    
    Logic:
    1.  Concatenate & Clean Columns.
    2.  Clean Text (UPPER, Strip) for Hash consistency with Dimensions.
    3.  Convert Types (Date, Float, Int).
    4.  Generate MD5 FKs for Cliente, Profissional (UPPER).
    5.  Generate MD5 FK for Servico (Granular: Item, no aggregation).
    6.  Generate MD5 PK for Comanda (Num + Data).
    7.  Select Final Columns.
    """
    if not df_list:
        return pd.DataFrame()

    # 1. Concatenate
    df = pd.concat(df_list, ignore_index=True)
    
    if df.empty:
        return df

    # FIX: Pre-cleaning Rename to avoid collision
    rename_map = {
        'Comissão (%)': 'comissao_pct',
        'Comissao (%)': 'comissao_pct'
    }
    df = df.rename(columns=rename_map)

    # 2. Sanitize Column Names
    # Expecting: 'data', 'comanda', 'profissional', 'cliente', 'item', 'tipo', 'categoria', 
    # 'valor', 'desconto', 'qtd', 'custo', 'comissão', 'líquido', 'grupo'
    new_columns = [clean_column_name(c) for c in df.columns]
    df.columns = new_columns

    # 3. Text Cleaning (Critical for Hash Consistency: UPPER + TRIM)
    # Target columns for ID generation: 'profissional', 'cliente', 'servico' (derived from item)
    
    # --- PROFISSIONAL ---
    if 'profissional' in df.columns:
        df['profissional'] = df['profissional'].astype(str).str.strip().str.upper()
        df['profissional'] = df['profissional'].replace(['', 'NAN', 'NONE'], 'NÃO IDENTIFICADO')
    else:
        df['profissional'] = 'NÃO IDENTIFICADO'

    # --- CLIENTE ---
    if 'cliente' in df.columns:
        df['cliente'] = df['cliente'].astype(str).str.strip().str.upper()
        df['cliente'] = df['cliente'].str.rstrip('.') # Remove dots
        df['cliente'] = df['cliente'].replace(['', 'NAN', 'NONE'], 'NAO IDENTIFICADO')
    else:
        df['cliente'] = 'NAO IDENTIFICADO'

    # --- SERVICO (ITEM) ---
    # User Request: "Granularidade: Manter uma linha por serviço (não concatenar)"
    # We will use 'item' (or 'servico' if renamed) as the service name.
    # We need a display version (Title Case) and an ID version (UPPER MD5).
    
    service_col = 'item' if 'item' in df.columns else 'servico'
    if service_col not in df.columns:
        # Fallback if neither exists
        df['servico'] = 'SERVIÇO DESCONHECIDO'
        df['id_servico_source'] = 'SERVIÇO DESCONHECIDO'
    else:
        # Normalized Source for ID (UPPER)
        df['id_servico_source'] = df[service_col].astype(str).str.strip().str.upper()
        df['id_servico_source'] = df['id_servico_source'].replace(['', 'NAN', 'NONE'], 'SERVICO DESCONHECIDO')
        
        # Display Name (Title Case)
        df['servico'] = df[service_col].astype(str).str.strip().str.title()
        df['servico'] = df['servico'].replace(['', 'Nan', 'None'], 'Servico Desconhecido')

    # --- GRUPO SERVICO (CATEGORIA) ---
    if 'categoria' in df.columns:
        df['grupo_servico'] = df['categoria'].astype(str).str.strip().str.title()
        df['grupo_servico'] = df['grupo_servico'].replace(['', 'Nan', 'None'], 'Geral')
    else:
        df['grupo_servico'] = 'Geral'

    # 4. Type Conversion
    
    # Dates
    if 'data' in df.columns:
        df['data'] = clean_date(df['data'])
        df['data_dt'] = pd.to_datetime(df['data'], errors='coerce')
    else:
        df['data_dt'] = pd.NaT

    # Floats (Currency)
    float_cols = ['valor', 'desconto', 'custo', 'comissao', 'liquido']
    for col in float_cols:
        if col in df.columns:
            df[col] = clean_currency(df[col])
            df[col] = df[col].fillna(0.0)
        else:
            df[col] = 0.0

    # Integers
    int_cols = ['qtd', 'comanda']
    for col in int_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
        else:
            df[col] = 0

    # 5. Generate Keys (MD5)
    
    def generate_hash(val: str) -> str:
        return hashlib.md5(val.encode('utf-8')).hexdigest()

    # ID Cliente
    df['id_cliente'] = df['cliente'].apply(generate_hash)

    # ID Profissional
    df['id_profissional'] = df['profissional'].apply(generate_hash)

    # ID Servico
    df['id_servico'] = df['id_servico_source'].apply(generate_hash)

    # 6. ID Comanda (Unique Ticket ID)
    # Logic: md5(str(Numero) + str(Data))
    # Ensure date component is consistent (YYYY-MM-DD or similar standard)
    
    # Format date as YYYY-MM-DD string
    date_str = df['data_dt'].dt.strftime('%Y-%m-%d').fillna('1900-01-01')
    comanda_str = df['comanda'].astype(str)
    
    # Combined string for hashing
    df['comanda_key'] = comanda_str + date_str
    df['id_comanda'] = df['comanda_key'].apply(generate_hash)

    # 7. Final Select
    desired_cols = [
        'data', 'id_comanda', 'comanda', 'id_profissional', 'profissional', 'id_cliente', 'cliente', 
        'id_servico', 'servico', 'grupo_servico', 
        'valor', 'desconto', 'qtd', 'custo', 'comissao', 'liquido'
    ]
    
    # Check for missing and fill with appropriate defaults if they weren't created above
    for col in desired_cols:
        if col not in df.columns:
            if col in float_cols or col in int_cols:
                df[col] = 0
            else:
                df[col] = None
            
    df_final = df[desired_cols].copy()
    
    logger.info(f"Fato Comandas (0186) processada. Rows: {len(df_final)}")
    return df_final
