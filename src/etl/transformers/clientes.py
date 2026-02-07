import pandas as pd
import hashlib
import logging
from typing import List, Dict, Optional, Any


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

    # 2. Select Columns (Handle Optional Columns Gracefully)
    # Essential columns that MUST exist (or we fail/warn)
    if 'Cliente' not in df.columns:
        logger.warning(f"Dimensão Clientes (0002) sem coluna obrigatória 'Cliente'. Cols: {df.columns.tolist()}")
        return pd.DataFrame()

    # Definition of columns to keep and their target names
    # Using a mapping for easy renaming later
    # 'Source': 'Target'
    col_mapping = {
        'Cliente': 'cliente',
        'Celular': 'celular',
        'E-mail': 'email',
        'Data de Nascimento': 'data_nascimento',
        'Sexo': 'sexo'
    }

    # Ensure optional columns exist in df to avoid KeyErrors
    for source_col in col_mapping.keys():
        if source_col not in df.columns:
            df[source_col] = None  # Create missing column with None/NaN

    # Filter to only desired columns
    df = df[list(col_mapping.keys())].copy()

    # 3. Data Cleaning

    # --- CLIENTE (Crucial: UPPER, Strip, Remove Dots) ---
    df['Cliente'] = df['Cliente'].astype(str).str.strip().str.upper()
    # Remove trailing dots (e.g., "MARIA S." -> "MARIA S")
    df['Cliente'] = df['Cliente'].str.rstrip('.')
    # Replace empty/nan strings
    df['Cliente'] = df['Cliente'].replace(['', 'NAN', 'NONE'], 'NAO IDENTIFICADO')

    # --- EMAIL (Lower case) ---
    if 'E-mail' in df.columns:
        df['E-mail'] = df['E-mail'].astype(str).str.strip().str.lower()
        df['E-mail'] = df['E-mail'].replace(['', 'nan', 'none'], None)

    # --- CELULAR (Sanitization: Digits ONLY) ---
    if 'Celular' in df.columns:
        # Remove non-digits
        df['Celular'] = df['Celular'].astype(str).str.replace(r'\D', '', regex=True)
        # Handle invalid lengths (valid BR mobile is usually 11 digits, sometimes 10 or 8/9 legacy)
        # User Rule: "If < 8 digits, treat as None"
        df['Celular'] = df['Celular'].apply(lambda x: x if len(str(x)) >= 8 else None)

    # 4. Intelligent Deduplication (The "Richness" Logic)
    # We need to pick the "best" record for each unique Name.
    # Score: Celular (+10), Email (+5), Data de Nascimento (+1)
    
    def calculate_richness(row):
        score = 0
        if pd.notna(row.get('Celular')) and row.get('Celular') != '':
            score += 10
        if pd.notna(row.get('E-mail')) and row.get('E-mail') != '':
            score += 5
        if pd.notna(row.get('Data de Nascimento')) and row.get('Data de Nascimento') != '':
            score += 1
        return score

    df['richness_score'] = df.apply(calculate_richness, axis=1)

    # Preserve original index to use as tie-breaker (Latest = Better)
    df['original_order'] = df.index

    # Sort by Score (DESC) and then by Original Order (DESC) to keep the "newest" among the "best"
    # This ensures that if scores are tied, we take the one that appeared last (most recent entry)
    df = df.sort_values(by=['richness_score', 'original_order'], ascending=[False, False])
    
    df.drop_duplicates(subset=['Cliente'], keep='first', inplace=True)

    # 5. Generate ID (MD5 of Cliente)
    # Now that Cliente is standardized (UPPER), the ID will be consistent for "Maria" and "MARIA".
    df['id_cliente'] = df['Cliente'].apply(lambda x: hashlib.md5(x.encode('utf-8')).hexdigest())

    # 6. Apply Renaming
    df.rename(columns=col_mapping, inplace=True)

    # 7. Add Unknown Row
    unknown_cols = {
        'id_cliente': 'UNKNOWN',
        'cliente': 'NAO IDENTIFICADO',
        'celular': 'NAO INFORMADO',
        'email': 'NAO INFORMADO',
        'sexo': 'NAO INFORMADO',
        'data_nascimento': None
    }
    # Ensure all columns in final df are in unknown_row (or handle mismatch)
    
    df_unknown = pd.DataFrame([unknown_cols])
    
    # Concatenate
    df_final = pd.concat([df, df_unknown], ignore_index=True)

    # 8. Final Column Selection & Ordering
    final_pd_cols = ['id_cliente', 'cliente', 'email', 'celular', 'data_nascimento', 'sexo']
    # Ensure all exist (handling cases where optional cols were missing entirely)
    for c in final_pd_cols:
        if c not in df_final.columns:
            df_final[c] = None

    df_final = df_final[final_pd_cols]

    logger.info(f"Dimensão Clientes processada. Rows: {len(df_final)}")

    return df_final
