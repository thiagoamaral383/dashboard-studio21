import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Add src to python path to allow imports
PROJECT_ROOT = Path(__file__).parent
sys.path.append(str(PROJECT_ROOT / "src"))

from src.etl import extract, transform, load_local, load_cloud

# Constants
DEFAULT_START_DATE_STR = "2023-08"

def main():
    logger.info("--- Iniciando Pipeline de Dados Studio21 (Modernizado) ---")
    
    # 1. Configuração de Datas
    hoje = datetime.now()
    primeiro_dia_mes_atual = hoje.replace(day=1)
    target_month_dt = (primeiro_dia_mes_atual - timedelta(days=1)).replace(day=1) # P2 - Mês Anterior Fechado
    try:
        start_date_dt = datetime.strptime(DEFAULT_START_DATE_STR, "%Y-%m").replace(day=1)
    except ValueError:
        start_date_dt = datetime(2023, 8, 1)

    logger.info(f"Mês da extração: {hoje.strftime('%Y-%m')}")
    
    # =========================================================================
    # UNIFIED PIPELINE LOOP
    # =========================================================================
    reports_config = extract.load_reports_config()
    if not reports_config:
        logger.error("Nenhum relatório para processar.")
        return

    # Track processed IDs to avoid redundant processing for multi-part reports (like 0387)
    processed_ids = set()
    
    # We must iterate through unique IDs, but reports_config has duplicates for 0387.
    # Let's iterate config and check processed_ids.
    
    for report_conf in reports_config:
        report_id = report_conf.get("id", "UNKNOWN")
        
        if report_id in processed_ids:
            continue
        
        logger.info(f"\n>>> Processando ID: {report_id}")
        
        df_final = pd.DataFrame()
        table_name = ""
        
        # --- POLYMORPHIC EXTRACTION & TRANSFORMATION ---
        
        if report_id == "0387":
            # FINANCIAL REPORT (Special Logic)
            # 1. Extract (Returns lists)
            logger.info("   [Estratégia] Financeiro Específico (0387)")
            lista_caixa, lista_competencia = extract.extract_financial_data(start_date_str="2023-08-01")
            
            if lista_caixa or lista_competencia:
                # 2. Transform (Unify & Deduplicate)
                df_final = transform.transform_factory("0387", (lista_caixa, lista_competencia))
                table_name = "0387_financeiro"
            else:
                logger.warning("   Nenhum dado financeiro encontrado.")
                
        else:
            # GENERIC REPORT (Standard Logic)
            # 1. Extract (Generic Full Refresh)
            subpasta = report_conf.get("nome_subpasta", "UNKNOWN")
            logger.info(f"   [Estratégia] Genérico Full Refresh ({subpasta})")
            
            dfs = extract.extract_generic_report(report_conf, start_date_str="2023-08-01")
            
            if dfs:
                # 2. Transform (Generic Standardization)
                df_final = transform.transform_factory(report_id, dfs)
                table_name = subpasta
            else:
                logger.info("   Nenhum dado encontrado.")

        # --- UNIVERSAL CLOUD LOAD ---
        
        if not df_final.empty and table_name:
            try:
                # Table name sanitization happens inside upload_to_motherduck (prefix tbl_)
                # We simply pass the logical name.
                load_cloud.upload_to_motherduck(
                    df_final, 
                    table_name=table_name, 
                    if_exists='replace'
                )
            except Exception as e:
                logger.error(f"   FALHA Motherduck para {report_id}: {e}")
        
        # Mark as processed
        processed_ids.add(report_id)

    logger.info("\n--- Pipeline Finalizado ---")

if __name__ == "__main__":
    main()
