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

def upload_to_motherduck(df: pd.DataFrame, table_name: str, if_exists: str = 'replace'):
    """
    Uploads DataFrame to Motherduck.
    :param table_name: Target table name (e.g. 'financeiro_movimentacoes')
    :param if_exists: 'replace' (default) or 'append'.
    """
    token = os.getenv("MOTHERDUCK_TOKEN")
    if not token:
        logger.warning("MOTHERDUCK_TOKEN não encontrado no .env. Pulando upload para Motherduck.")
        return 

    try:
        # Sanitize table name
        table_name_sanitized = table_name.strip().replace(" ", "_").replace("-", "_").replace("/", "_").lower()
        
        # Ensure it doesn't start with a digit (DuckDB/SQL requirement)
        # We prefix EVERY table with 'tbl_' for consistency and safety.
        # e.g. "0002_Clientes" -> "tbl_0002_clientes"
        # e.g. "financeiro_movimentacoes" -> "tbl_financeiro_movimentacoes" (optional, but good for consistency)
        
        # If it already starts with tbl_, don't add it again.
        if not table_name_sanitized.startswith("tbl_"):
             table_name_sanitized = f"tbl_{table_name_sanitized}"
        
        logger.info(f"Conectando ao Motherduck (tabela: {table_name_sanitized})...")
        
        # Connect to Motherduck (Default)
        # We connect to 'md:' first to ensure we can create the database if it doesn't exist.
        con = duckdb.connect('md:')
        
        # Create and Switch to Database
        con.sql("CREATE DATABASE IF NOT EXISTS studio21")
        con.sql("USE studio21")
        
        # Register the DataFrame as a virtual table
        con.register('df_view', df)
        
        if if_exists == 'replace':
             con.sql(f"CREATE OR REPLACE TABLE {table_name_sanitized} AS SELECT * FROM df_view")
             logger.info(f"Tabela {table_name_sanitized} SUBSTITUÍDA com sucesso em studio21 (ROWS: {len(df)}).")
        else:
            # Create schema if not exists
            con.sql(f"CREATE TABLE IF NOT EXISTS {table_name_sanitized} AS SELECT * FROM df_view LIMIT 0")
            # Insert data
            con.sql(f"INSERT INTO {table_name_sanitized} SELECT * FROM df_view")
            logger.info(f"Dados INSERIDOS com sucesso na tabela {table_name_sanitized} em studio21 (ROWS: {len(df)}).")
            
    except Exception as e:
        logger.error(f"Erro ao fazer upload para Motherduck: {e}")
        raise e
