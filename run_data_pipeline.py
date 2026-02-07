import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

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
    logger.info("--- Iniciando Pipeline de Dados Studio21 (Modularizado) ---")
    
    # 1. Configuração de Datas
    hoje = datetime.now()
    primeiro_dia_mes_atual = hoje.replace(day=1)
    target_month_dt = (primeiro_dia_mes_atual - timedelta(days=1)).replace(day=1) # P2 - Mês Anterior Fechado
    try:
        start_date_dt = datetime.strptime(DEFAULT_START_DATE_STR, "%Y-%m").replace(day=1)
    except ValueError:
        logger.error(f"Data inicial inválida: {DEFAULT_START_DATE_STR}. Usando fallback.")
        start_date_dt = datetime(2023, 8, 1)

    logger.info(f"Mês da extração: {hoje.strftime('%Y-%m')}")
    logger.info(f"Mês alvo final (P2): {target_month_dt.strftime('%Y-%m')}")

    # 2. Carregar Configuração
    reports_config = extract.load_reports_config()
    if not reports_config:
        logger.error("Nenhum relatório para processar.")
        return

    # 3. Login
    try:
        session = extract.login()
    except Exception as e:
        logger.critical(f"Falha no login: {e}")
        return

    # 4. Processar cada relatório
    for relatorio in reports_config:
        report_id = relatorio.get("id", "UNKNOWN")
        subpasta = relatorio.get("nome_subpasta", "UNKNOWN")
        logger.info(f"\n--- Processando Relatório: {report_id} ({subpasta}) ---")

        months_to_process = extract.identify_months_to_download(
            relatorio, hoje, target_month_dt, start_date_dt
        )

        if not months_to_process:
            logger.info("Relatório atualizado. Nada a processar.")
            continue

        logger.info(f"Meses a processar: {[m.strftime('%Y-%m') for m in months_to_process]}")

        for month_dt in months_to_process:
            # EXTRACT
            raw_data, filename = extract.fetch_data_for_month(session, relatorio, month_dt, hoje)
            
            if not raw_data:
                logger.warning(f"Sem dados para {filename}. Pulando.")
                continue

            # TRANSFORM
            colunas = relatorio.get("headers")
            df = transform.transform_to_dataframe(raw_data, colunas)
            logger.info(f"Dados transformados. Rows: {len(df)}")

            # LOAD LOCAL (CRITICAL)
            try:
                load_local.save_to_excel(df, subpasta, filename)
            except Exception as e:
                logger.error(f"FALHA CRÍTICA ao salvar Excel local {filename}: {e}")
                continue

            # LOAD CLOUD (Resilient)
            try:
                if report_id == "0387":
                    # Special Logic for Financeiro (0387)
                    # We need to unify Competencia and Caixa history + new data
                    # The new data is already saved to disk in LOAD LOCAL step.
                    # So we just reload everything from disk to ensure consistency.
                    
                    logger.info("Executando unificação financeira para 0387...")
                    
                    # Define paths (Hardcoded based on knowledge of reports.json structure)
                    path_competencia = extract.PASTA_RAIZ_RELATORIOS / "0387_Financeiro/Competencia"
                    path_caixa = extract.PASTA_RAIZ_RELATORIOS / "0387_Financeiro/Caixa"
                    
                    df_comp = transform.load_excel_history(path_competencia, file_filter="*Competencia*.xlsx")
                    df_caixa = transform.load_excel_history(path_caixa, file_filter="*Caixa*.xlsx")
                    
                    logger.info(f"Histórico carregado: Comp={len(df_comp)}, Caixa={len(df_caixa)}")
                    
                    df_unified = transform.process_financial_data(df_comp, df_caixa)
                    logger.info(f"Dados financeiros unificados. Rows Finais: {len(df_unified)}")
                    
                    load_cloud.upload_to_motherduck(df_unified, table_name="0387_Financeiro", if_exists='replace')
                    
                else:
                    # Standard Logic
                    # Table name strategy: Use the folder name (subpasta)
                    load_cloud.upload_to_motherduck(df, table_name=subpasta, if_exists='append')
                    
            except Exception as e:
                logger.error(f"FALHA ao subir para Motherduck: {e}. O Excel local foi salvo.")
                # Não interrompe o fluxo (Constraint atendida)

    logger.info("\n--- Pipeline Finalizado ---")

if __name__ == "__main__":
    main()
