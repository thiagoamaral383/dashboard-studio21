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
    2.  Clean Text (Trim, Title) for Hash consistency with Dimensions.
    3.  Convert Types (Date, Float, Int).
    4.  Generate FKs (MD5) for Cliente, Profissional, Servico.
    5.  Generate PK (Surrogate Key) -> "{comanda}-{ano}-{mes_zero_padded}".
    6.  Select Final Columns.
    """
    if not df_list:
        return pd.DataFrame()

    # 1. Concatenate
    df = pd.concat(df_list, ignore_index=True)
    
    if df.empty:
        return df

    # 2. Sanitize Column Names
    # Expecting: 'Data', 'Comanda', 'Profissional', 'Cliente', 'Item', 'Tipo', 'Categoria', 
    # 'Valor', 'Desconto', 'Qtd', 'Custo', 'Comissão', 'Líquido'
    new_columns = [clean_column_name(c) for c in df.columns]
    df.columns = new_columns

    # 3. Text Cleaning (Critical for Hash Consistency)
    # Target columns: 'profissional', 'cliente', 'item', 'tipo', 'categoria'
    text_cols = ['profissional', 'cliente', 'item', 'tipo', 'categoria']
    
    for col in text_cols:
        if col in df.columns:
            # Ensure string, strip whitespace
            df[col] = df[col].astype(str).str.strip()
            
            # Handle Empty/NaN -> "Não Identificado" (or empty string for optional components?)
            # User requirement: "Se lá usamos 'Maria Silva', aqui não pode ser 'MARIA SILVA'"
            # User requirement: replicate 'clientes.py' logic: Title Case.
            
            # Replace common null representations with a placeholder if needed, 
            # BUT for hashing we might want a specific standard.
            # In clientes.py: 
            #   df['Cliente'] = df['Cliente'].replace(['', 'nan', 'None'], 'Não Indentificado')
            #   df['Cliente'] = df['Cliente'].apply(lambda x: x.title() ...)
            
            # We'll apply this to 'profissional' and 'cliente' specifically.
            if col in ['profissional', 'cliente']:
                df[col] = df[col].replace(['', 'nan', 'None'], 'Não Identificado')
                df[col] = df[col].apply(lambda x: x.title() if x != 'Não Identificado' else x)
            else:
                # For Service components (item, tipo, categoria)
                # User request: "Preencha nulos com string vazia '' ou 'N/A' ... antes de concatenar"
                # using empty string to ensure clean concatenation
                df[col] = df[col].replace(['', 'nan', 'None'], '')
                df[col] = df[col].apply(lambda x: x.title())

    # 4. Type Conversion
    
    # Dates
    if 'data' in df.columns:
        df['data'] = clean_date(df['data'])
        # Ensure we have datetime objects for year/month extraction (clean_date_vectorized returns objects/dates)
        # We need to coerce to actual datetime for .dt accessors if they aren't already
        df['data_dt'] = pd.to_datetime(df['data'], errors='coerce')
    
    # Floats (Currency)
    float_cols = ['valor', 'desconto', 'custo', 'comissao', 'liquido']
    for col in float_cols:
        if col in df.columns:
            df[col] = clean_currency(df[col])
            # Handle nulls -> 0.0
            df[col] = df[col].fillna(0.0)

    # Integers
    int_cols = ['qtd', 'comanda']
    for col in int_cols:
        if col in df.columns:
            # Clean generic text first? clean_currency handles numeric string cleaning well.
            # But let's just use pd.to_numeric with coerce
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

    # 5. Generate Keys (MD5)
    
    def generate_hash(val: str) -> str:
        return hashlib.md5(val.encode('utf-8')).hexdigest()

    # ID Cliente
    if 'cliente' in df.columns:
        df['id_cliente'] = df['cliente'].apply(generate_hash)
    else:
        df['id_cliente'] = generate_hash('Não Identificado')

    # ID Profissional
    if 'profissional' in df.columns:
        df['id_profissional'] = df['profissional'].apply(generate_hash)
    else:
        df['id_profissional'] = generate_hash('Não Identificado')

    # ID Servico (Item + Tipo + Categoria)
    # User requirement: "Hash da concatenação item + tipo + categoria"
    # User requirement: "Preencha nulos com string vazia... antes de concatenar"
    # We already filled with 'Não Identificado' above. Let's use that.
    # We need to ensure we don't have NaNs here at all.
    
    servico_components = []
    for c in ['item', 'tipo', 'categoria']:
        if c in df.columns:
            servico_components.append(df[c])
        else:
            # If column missing, treat as empty/unknown
            servico_components.append(pd.Series(['Não Identificado'] * len(df)))
            
    # Vectorized Concatenation
    # We can zip them or just adds.
    # s1 + s2 + s3
    
    # Let's ensure they are all strings
    s_item = servico_components[0].astype(str)
    s_tipo = servico_components[1].astype(str)
    s_cat = servico_components[2].astype(str)
    
    # Concat
    # Separator? Usually good practice, but not specified. "item + tipo + categoria" implies direct concat?
    # "Concatenação 'item + tipo + categoria' (limpos)."
    # If I use a separator, I risk diverging from a potential 'Serviços' dimension logic if it exists.
    # Assuming direct concatenation or space separated?
    # Spec says "item + tipo + categoria". I will stick to direct concatenation to be safe,
    # OR better, standard `|` separator to avoid collisions (e.g. "A" + "BC" vs "AB" + "C").
    # Given the instructions "item + tipo + categoria", I will assume DIRECT CONCATENATION unless dimension logic implies otherwise.
    # However, for safety in many projects we use a separator.
    # Let's assume DIRECT for now based on strict reading, but I'll add a comment.
    # Actually, looking at the user prompt: "id_servico: Hash MD5 da concatenação item + tipo + categoria (limpos)."
    # I will use DIRECT concatenation to follow instructions literally.
    
    df['servico_concat'] = s_item + s_tipo + s_cat
    df['id_servico'] = df['servico_concat'].apply(generate_hash)

    # 6. Surrogate Key (id_comanda_unica)
    # "{comanda}-{ano}-{mes}"
    # User requirement: "Mês com dois dígitos!" -> %02d
    
    if 'data_dt' in df.columns and 'comanda' in df.columns:
        # We need year and month
        y = df['data_dt'].dt.year.fillna(0).astype(int).astype(str)
        m = df['data_dt'].dt.month.fillna(0).astype(int).astype(str).str.zfill(2) # Zero padding
        
        c = df['comanda'].astype(int).astype(str)
        
        df['id_comanda_unica'] = c + '-' + y + '-' + m
    else:
        df['id_comanda_unica'] = range(len(df)) # Fallback/Error
        df['id_comanda_unica'] = df['id_comanda_unica'].astype(str)

    # 7. Final Select
    desired_cols = [
        'data', 'id_comanda_unica', 'id_profissional', 'id_cliente', 'id_servico', 
        'valor', 'desconto', 'qtd', 'custo', 'comissao', 'liquido'
    ]
    
    # Check for missing
    for col in desired_cols:
        if col not in df.columns:
            df[col] = 0 if col in float_cols or col in int_cols else None
            
    df_final = df[desired_cols].copy()
    
    logger.info(f"Fato Comandas (0186) processada. Rows: {len(df_final)}")
    return df_final
