import pandas as pd
from src.etl.cleaning import clean_column_name, clean_date

def process_retorno(df_list):
    """
    Processa o relatório 0007 (Retorno).
    
    Colunas esperadas: ["Cliente", "E-mail", "Telefone", "Celular", "Sexo", "Última Visita"]
    """
    if not df_list:
        return pd.DataFrame()

    df = pd.concat(df_list, ignore_index=True)

    # 1. Sanitizar nomes das colunas
    df.columns = [clean_column_name(c) for c in df.columns]
    
    # Padronização específica
    if 'e_mail' in df.columns:
        df.rename(columns={'e_mail': 'email'}, inplace=True)

    # 2. Converter datas
    if 'ultima_visita' in df.columns:
        df['ultima_visita'] = clean_date(df['ultima_visita'])

    # 3. Limpeza de strings
    if 'cliente' in df.columns:
        df['cliente'] = df['cliente'].astype(str).str.title().str.strip()
    
    if 'email' in df.columns:
        df['email'] = df['email'].astype(str).str.lower().str.strip()
        # Tratamento básico para nulos/vazios
        df.loc[df['email'].isin(['nan', 'none', '']), 'email'] = None

    if 'sexo' in df.columns:
        df['sexo'] = df['sexo'].astype(str).str.upper().str.strip()
        df.loc[df['sexo'].isin(['NAN', 'NONE', '']), 'sexo'] = None

    # Tratamento de nulos/NaNs gerais para evitar problemas futuros
    # (Opcional, mas boa prática manter consistência)
    
    return df
