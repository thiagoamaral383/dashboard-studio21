import os
import duckdb
import pandas as pd
import logging
from dotenv import load_dotenv
from pathlib import Path

# Load Environment Variables for Token
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
ENV_PATH = PROJECT_ROOT / "config" / ".env"
load_dotenv(ENV_PATH)

logger = logging.getLogger(__name__)

def upload_to_motherduck(df: pd.DataFrame, table_name: str, if_exists: str = 'append'):
    """
    Uploads DataFrame to Motherduck.
    :param if_exists: 'append' (default) or 'replace'.
    """
    token = os.getenv("MOTHERDUCK_TOKEN")
    if not token:
        logger.warning("MOTHERDUCK_TOKEN não encontrado. Pulando upload para nuvem.")
        raise ValueError("MOTHERDUCK_TOKEN missing")

    try:
        # Sanitize table name
        table_name_sanitized = table_name.replace(" ", "_").replace("-", "_").replace("/", "_").lower()
        
        # Ensure it doesn't start with a digit
        if table_name_sanitized and table_name_sanitized[0].isdigit():
            table_name_sanitized = f"report_{table_name_sanitized}"
        
        # Connect to Motherduck
        con = duckdb.connect(f'md:?motherduck_token={token}')
        
        # Create/Replace table
        # We use register to make the DF available to SQL
        con.register('df_view', df)
        
        if if_exists == 'replace':
             con.execute(f"CREATE OR REPLACE TABLE {table_name_sanitized} AS SELECT * FROM df_view")
             logger.info(f"Tabela {table_name_sanitized} SUBSTITUÍDA com sucesso (ROWS: {len(df)}).")
        else:
            # Create schema if not exists
            con.execute(f"CREATE TABLE IF NOT EXISTS {table_name_sanitized} AS SELECT * FROM df_view LIMIT 0")
            # Insert data
            con.execute(f"INSERT INTO {table_name_sanitized} SELECT * FROM df_view")
            logger.info(f"Dados INSERIDOS com sucesso na tabela {table_name_sanitized} (ROWS: {len(df)}).")
        
    except Exception as e:
        logger.error(f"Erro ao fazer upload para Motherduck: {e}")
        # Re-raise to let the pipeline handle the 'try/except' logic for cloud failure
        raise e
