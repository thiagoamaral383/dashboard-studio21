import pandas as pd
import logging
from typing import List, Any
import datetime
from src.etl.cleaning import clean_column_name

logger = logging.getLogger(__name__)

def parse_time_to_decimal(val: Any) -> float:
    """
    Converts strictly formatted 'HH:MM' string, python time, or datetime object 
    to decimal hours (float).
    
    Examples:
    - "01:30" -> 1.5
    - datetime.time(1, 30) -> 1.5
    - datetime.datetime(2023, 1, 1, 1, 30) -> 1.5
    - 1.5 -> 1.5 (if already float)
    - "Invalid" -> 0.0
    - None -> 0.0
    """
    if pd.isna(val) or val == '':
        return 0.0
    
    try:
        # 1. If already numeric (float/int)
        if isinstance(val, (float, int)):
            return float(val)

        # 2. If datetime.time
        if isinstance(val, datetime.time):
            return val.hour + (val.minute / 60.0)

        # 3. If datetime.datetime
        if isinstance(val, datetime.datetime):
            return val.hour + (val.minute / 60.0)

        # 4. If string
        val_str = str(val).strip()
        if not val_str:
            return 0.0
            
        # Handle 'HH:MM:SS' or 'HH:MM'
        parts = val_str.split(':')
        if len(parts) >= 2:
            hours = float(parts[0])
            minutes = float(parts[1])
            return hours + (minutes / 60.0)
        
        # Determine if it's just a number string "1.5"
        try:
             return float(val_str)
        except:
             pass
             
    except Exception as e:
        # logger.debug(f"Falha ao converter tempo '{val}': {e}")
        pass

    return 0.0

def process_ocupacao(df_list: List[pd.DataFrame]) -> pd.DataFrame:
    """
    Processes 'Ocupação' report (ID 0126).
    Focus: Extract 'Horas Agendadas' as decimal hours for productivity validation.
    
    Steps:
    1. Check for data existence
    2. Sanitize column names
    3. Ensure 'data_competencia' exists
    4. Convert 'total_agendado' (HH:MM) to decimal
    5. Clean 'profissional' name (title case, strip)
    6. Return specific subset of columns
    """
    if not df_list:
        return pd.DataFrame()

    # 1. Concatenate
    df = pd.concat(df_list, ignore_index=True)
    if df.empty:
        return df

    # 2. Sanitize Column Names
    # We use temporary generic cleaning to ensure consistency before access
    # But usually we want to rename map specifically if we know source.
    # However, 'generico' approach is safer for diverse inputs.
    clean_cols = {c: clean_column_name(c) for c in df.columns}
    df.rename(columns=clean_cols, inplace=True)

    # 3. Date Validation (Runtime Injection check)
    if 'data_competencia' not in df.columns:
        logger.warning("Relatório 0126 (Ocupação) sem 'data_competencia'. Verifique extract.py.")
        # Fallback? Maybe today? Or fail?
        # Let's drop rows without it or set to NaT, but we want to fail loudly for data integrity?
        # User requested warning.
        return pd.DataFrame() 

    # 4. Time Conversion
    # Target column: 'total_agendado' (from source 'Total Agendado')
    target_col = 'total_agendado'
    if target_col not in df.columns:
        logger.warning(f"Relatório 0126 sem coluna '{target_col}'. Cols: {df.columns.tolist()}")
        # Maybe 'horas_agendadas'? Try some variations if strict legacy name changed.
        # But per spec: "total_agendado" likely from "Total Agendado".
        return pd.DataFrame()

    # Vectorized Apply (Parsing is complex for vectorization without pure string ops, map is fine)
    df['horas_agendadas_decimal'] = df[target_col].apply(parse_time_to_decimal)

    # 5. Clean Professional
    # Target: 'profissional'
    if 'profissional' in df.columns:
        df['profissional'] = df['profissional'].astype(str).str.strip().str.title().replace(['Nan', 'None', ''], 'Desconhecido')
    else:
        logger.warning("Relatório 0126 sem coluna 'profissional'.")
        df['profissional'] = 'Desconhecido'

    # Filter Rows with 0 hours?
    # Spec says "filtrando apenas métricas confiáveis". 
    # Usually we keep 0s for explicitly "Free" days? 
    # The requirement says "focus on extracting Horas Agendadas".
    # We'll keep all rows for now, aggregation happens later.

    # 3. Select Final Columns
    final_cols = ['data_competencia', 'profissional', 'horas_agendadas_decimal']
    
    # Ensure strict schema
    df_final = df[final_cols].copy()
    
    logger.info(f"Ocupação (0126) processada. Rows: {len(df_final)}")
    return df_final
