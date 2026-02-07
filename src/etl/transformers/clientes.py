import pandas as pd
import hashlib
import logging
from typing import List, Dict, Optional, Any
from .generico import clean_column_name

logger = logging.getLogger(__name__)

def process_dim_clientes(df_list: List[pd.DataFrame]) -> pd.DataFrame:
    """
    Processes 'Clientes' dimension (Report 0002).
    Logic replicated from Power Query (M).
    
    Steps:
    1. Select ['Cliente', 'Celular', 'E-mail']
    2. Clean 'Cliente' (Trim, Title, Default 'Não Indentificado')
    3. Deduplicate on 'Cliente'
    4. Fill Nulls in Email/Celular with 'Não Informado'
    5. Generate MD5 ID based on 'Cliente'
    6. Add Unknown Row
    """
    if not df_list:
        return pd.DataFrame()

    # 1. Concatenate
    df = pd.concat(df_list, ignore_index=True)
    
    if df.empty:
        return df

    # 1. Select Columns
    # Normalize input columns to allow for some variation? No, strict per spec.
    # But let's handle potential casing issues in source if needed.
    # For now, stick to spec: 'Cliente', 'Celular', 'E-mail'
    
    desired_cols = ['Cliente', 'Celular', 'E-mail']
    available_cols = [c for c in desired_cols if c in df.columns]
    
    if 'Cliente' not in available_cols:
        logger.warning(f"Dimensão Clientes (0002) sem coluna obrigatória 'Cliente'. Cols: {df.columns.tolist()}")
        return pd.DataFrame() # Limit redundancy
        
    df = df[available_cols].copy()

    # 2. Data Cleaning
    
    # Cliente: Trim, Title, Handle Empty/Null
    df['Cliente'] = df['Cliente'].astype(str).str.strip()
    # Replace empty strings and 'nan'/'None' strings
    df['Cliente'] = df['Cliente'].replace(['', 'nan', 'None'], 'Não Indentificado')
    
    # Title casing:
    # Title() in pandas/python can be aggressive (e.g. D'agua -> D'Agua).
    # Power Query Text.Proper matches .str.title() roughly.
    df['Cliente'] = df['Cliente'].apply(lambda x: x.title() if x != 'Não Indentificado' else x)
    
    # 3. Deduplication
    df.drop_duplicates(subset=['Cliente'], inplace=True)
    
    # 4. Handle Nulls (Celular, E-mail)
    for col in ['Celular', 'E-mail']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().replace(['', 'nan', 'None'], 'Não Informado')
        else:
            df[col] = 'Não Informado'

    # 5. Generate ID (MD5 of Cliente)
    df['id_cliente'] = df['Cliente'].apply(lambda x: hashlib.md5(x.encode('utf-8')).hexdigest())
    
    # 7. Sanitize Column Names
    # Explicit mapping for known columns to ensure 'email' not 'e_mail'
    rename_map = {
        'Cliente': 'cliente',
        'Celular': 'celular',
        'E-mail': 'email'
    }
    df.rename(columns=rename_map, inplace=True)
    
    # 6. Add Unknown Row
    unknown_row = {
        'id_cliente': 'UNKNOWN',
        'cliente': 'Não Identificado',
        'celular': 'Não Informado',
        'email': 'Não Informado'
    }
    
    df_unknown = pd.DataFrame([unknown_row])
    df_final = pd.concat([df, df_unknown], ignore_index=True)
    
    # Reorder
    cols_order = ['id_cliente', 'cliente', 'celular', 'email']
    final_cols = [c for c in cols_order if c in df_final.columns]
    df_final = df_final[final_cols]
    
    logger.info(f"Dimensão Clientes processada. Rows: {len(df_final)}")
    
    return df_final
