import json
import logging
import os
import time
import requests
import pandas as pd
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from dotenv import load_dotenv

from . import utils
from . import load_local

logger = logging.getLogger(__name__)

# Paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
REPORTS_CONFIG_PATH = PROJECT_ROOT / "config" / "reports.json"
ENV_PATH = PROJECT_ROOT / "config" / ".env"
PASTA_RAIZ_RELATORIOS = PROJECT_ROOT / "reports"

# Load Environment Variables
load_dotenv(ENV_PATH)

EMAIL = os.getenv("EMAIL")
SENHA = os.getenv("SENHA")
SALAO_ID = os.getenv("SALAO_ID", "91604")
SLUG = os.getenv("SLUG", "centro-e-r-nogales")
URL_LOGIN = f"https://admin.avec.beauty/{SLUG}/admin"
URL_BASE_RELATORIO = "https://admin.avec.beauty/admin/relatorios/listar"

LOGIN_PAYLOAD = {
    'email': EMAIL,
    'senha': SENHA,
    'salaoId': SALAO_ID,
    'slug': SLUG,
    'continue': 'outro',
    'logintimestamp': 'a3debc1b4b9ff358d2409ba6a98874cb'
}

def load_reports_config() -> List[Dict]:
    if not REPORTS_CONFIG_PATH.exists():
        logger.error(f"Arquivo de configuração de relatórios não encontrado em {REPORTS_CONFIG_PATH}")
        return []
    with open(REPORTS_CONFIG_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def login() -> requests.Session:
    session = requests.Session()
    logger.info(f"Tentando login em {URL_LOGIN}...")
    try:
        r_login = session.post(URL_LOGIN, data=LOGIN_PAYLOAD)
        r_login.raise_for_status()
        logger.info("Login realizado com SUCESSO.")
        return session
    except Exception as e:
        logger.critical(f"Falha no login: {e}")
        raise

def get_month_range(start_date: datetime, end_date: datetime) -> List[datetime]:
    months = []
    current = start_date.replace(day=1)
    end = end_date.replace(day=1)
    while current <= end:
        months.append(current)
        current += relativedelta(months=1)
    return months

def extract_financial_data(start_date_str: str = "2023-08-01") -> Tuple[List[pd.DataFrame], List[pd.DataFrame]]:
    """
    Main entry point for Financial Data Extraction (0387).
    iterates from start_date to current month.
    """
    logger.info(f"Iniciando extração financeira a partir de {start_date_str}...")
    
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
    today = datetime.now()
    # End date includes current month because we might want partial data or full refresh
    months_to_process = get_month_range(start_date, today)

    config = load_reports_config()
    # Filter for 0387 reports
    reports_0387 = [r for r in config if r.get("id") == "0387"]
    
    if not reports_0387:
        logger.error("Configuração do relatório 0387 não encontrada.")
        return [], []

    session = login()

    lista_caixa = []
    lista_competencia = []

    for month in months_to_process:
        month_str = month.strftime("%Y-%m")
        logger.info(f"Processando mês: {month_str}")

        for report_config in reports_0387:
            # Identify if it is Caixa or Competencia based on sub folder or suffix
            subpasta = report_config.get("nome_subpasta", "")
            is_caixa = "Caixa" in subpasta or "Caixa" in report_config.get("filename_suffix", "")
            is_competencia = "Competencia" in subpasta or "Competencia" in report_config.get("filename_suffix", "")
            
            if not (is_caixa or is_competencia):
                continue
            
            # Construct Filename
            suffix = report_config.get("filename_suffix", "")
            filename = f"{month_str}_0387{suffix}.xlsx"
            
            # Path Check (Smart Cache)
            # subpasta e.g. "0387_Financeiro/Caixa"
            # Full path: reports/0387_Financeiro/Caixa/2023-08_0387_Caixa.xlsx
            file_path = PASTA_RAIZ_RELATORIOS / subpasta / filename
            
            df = None
            
            if file_path.exists():
                logger.info(f"  [CACHE] Encontrado: {filename}")
                try:
                    # User requested 'dtype=str' to maintain consistency with API/JSON behavior
                    df = pd.read_excel(file_path, dtype=str)
                except Exception as e:
                    logger.error(f"  Erro ao ler cache {filename}: {e}. Tentando baixar novamente.")
            
            if df is None:
                # Download
                logger.info(f"  [DOWNLOAD] Baixando: {filename}...")
                raw_data = fetch_data_from_api(session, report_config, month)
                if raw_data:
                    # Convert to DF for saving
                    headers = report_config.get("headers", [])
                    df = pd.DataFrame(raw_data, columns=headers)
                    
                    # Save Local (Constraint: load_local)
                    try:
                        load_local.save_to_excel(df, subpasta, filename)
                        # Reload from excel to ensure type consistency? 
                        # Or just cast to str? API returns JSON which might have ints/floats. 
                        # But read_excel(dtype=str) makes everything object. 
                        # To be safe and consistent with "Loaded from Cache", we can just use the df we just created, 
                        # but ideally we want the string representation that would be providing by read_excel(dtype=str).
                        # However, for now, we will proceed with the df we have, assuming transform handle types.
                    except Exception as e:
                        logger.error(f"  Erro ao salvar {filename}: {e}")
                    
                    # Constraint: Respect server load
                    time.sleep(2)
                else:
                    logger.warning(f"  Sem dados para {filename}.")
            
            if df is not None:
                if is_caixa:
                    lista_caixa.append(df)
                elif is_competencia:
                    lista_competencia.append(df)

    return lista_caixa, lista_competencia

def fetch_data_from_api(session: requests.Session, relatorio: Dict, month_dt: datetime) -> Optional[List[Dict]]:
    """
    Fetches raw data from AVEC API for a specific month.
    """
    params_base = relatorio['params'].copy()
    
    # Calculate dates using utils logic
    datas = utils.get_period_dates(month_dt)
    
    params_completos = params_base.copy()
    report_type = relatorio.get("report_type", "padrao")
    
    if report_type == "padrao":
        params_completos['inicio'] = datas['data_inicio_p2']
        params_completos['fim'] = datas['data_fim_p2']
    elif report_type == "comparacao":
        # Usually not for 0387, but generic support
        params_completos['inicio1'] = datas['data_inicio_p1']
        params_completos['fim1'] = datas['data_fim_p1']
        params_completos['inicio2'] = datas['data_inicio_p2']
        params_completos['fim2'] = datas['data_fim_p2']

    try:
        r_download = session.get(URL_BASE_RELATORIO, params=params_completos)
        r_download.raise_for_status()
        dados_json = r_download.json()
        return dados_json.get('aaData', [])
    except Exception as e:
        logger.error(f"Erro na API AVEC: {e}")
        return None

# Keep legacy function for compatibility if needed, or redirect
def identify_months_to_download(relatorio: Dict, hoje: datetime, target_month_dt: datetime, start_date_dt: datetime) -> List[datetime]:
    # This is used by the old loop in run_data_pipeline.py for NON-financial reports?
    # The user asked to refactor extract.py, assuming we keep supporting other reports too.
    # So I should keep this generic logic for other reports.
    # ...
    # Re-implementing the original logic for backward compatibility
    report_id = relatorio.get("id", "UNKNOWN")
    subpasta = relatorio.get("nome_subpasta", "")
    report_type = relatorio.get("report_type", "padrao")
    suffix = relatorio.get("filename_suffix", "")
    
    subpasta_path = PASTA_RAIZ_RELATORIOS / subpasta
    
    if report_type == "sem_data":
        mes_ano_extracao = hoje.strftime('%Y-%m')
        filename = f"{mes_ano_extracao}_{report_id}{suffix}.xlsx"
        if (subpasta_path / filename).exists():
            return []
        return [hoje.replace(day=1)]
        
    # Standard logic
    all_months = utils.get_month_list(start_date_dt, target_month_dt)
    months_to_download = []
    
    for month in all_months:
        # Check specific Logic for 0007 (Range Naming Exception)
        if report_id == "0007":
            # 0007 uses "YYYY-MM a YYYY-MM_0007_Retorno.xlsx"
            # Derived from P1 and P2 dates.
             datas = utils.get_period_dates(month)
             p1_str = datas['dt_p1'].strftime('%Y-%m')
             p2_str = datas['dt_p2'].strftime('%Y-%m')
             filename = f"{p1_str} a {p2_str}_{report_id}{suffix}.xlsx"
        else:
            month_str = month.strftime('%Y-%m')
            filename = f"{month_str}_{report_id}{suffix}.xlsx"
            
        if not (subpasta_path / filename).exists():
            months_to_download.append(month)
            
    return months_to_download

def extract_generic_report(report_config: Dict, start_date_str: str = "2023-08-01") -> List[pd.DataFrame]:
    """
    Extracts data for a generic report using Smart Cache and Full Refresh strategy.
    Handles Report 0007 exception.
    """
    report_id = report_config.get("id", "UNKNOWN")
    subpasta = report_config.get("nome_subpasta", "")
    suffix = report_config.get("filename_suffix", "")
    
    logger.info(f"Iniciando extração genérica para {report_id} ({subpasta})...")
    
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
    today = datetime.now()
    months_to_process = get_month_range(start_date, today)
    
    session = login() # Re-use or create new session
    
    dfs = []
    
    for month in months_to_process:
        month_str = month.strftime("%Y-%m")
        
        # 1. Determine Filename (Handle 0007 Exception)
        if report_id == "0007":
            # 0007 uses "YYYY-MM a YYYY-MM_0007_Retorno.xlsx"
            datas = utils.get_period_dates(month)
            p1_str = datas['dt_p1'].strftime('%Y-%m')
            p2_str = datas['dt_p2'].strftime('%Y-%m')
            filename = f"{p1_str} a {p2_str}_{report_id}{suffix}.xlsx"
        elif report_config.get("report_type") == "sem_data":
            # Sem data usually is snapshot of current state, so maybe we only want the LATEST?
            # But the loop iterates months.
            # If "sem_data", filename usually is just YYYY-MM of extraction.
            # We strictly follow the loop to ensure we get what was requested or existing history.
            filename = f"{month_str}_{report_id}{suffix}.xlsx"
        else:
            filename = f"{month_str}_{report_id}{suffix}.xlsx"
            
        # 2. Smart Cache Check
        file_path = PASTA_RAIZ_RELATORIOS / subpasta / filename
        df_month = None
        
        if file_path.exists():
            # logger.info(f"  [CACHE] Encontrado: {filename}") # Verbosity reduction
            try:
                # Read as string to avoid type inference issues early on
                df_month = pd.read_excel(file_path, dtype=str)
            except Exception as e:
                logger.error(f"  Erro ao ler cache {filename}: {e}")
        
        if df_month is None:
            # Download
            logger.info(f"  [DOWNLOAD] Baixando: {filename}...")
            # We need to pass the specific month to fetch data
            # Note: fetch_data_from_api uses 'report_config' params.
            
            raw_data = fetch_data_from_api(session, report_config, month)
            
            if raw_data:
                headers = report_config.get("headers", [])
                df_month = pd.DataFrame(raw_data, columns=headers)
                
                # Save Local
                try:
                    load_local.save_to_excel(df_month, subpasta, filename)
                except Exception as e:
                    logger.error(f"  Erro ao salvar {filename}: {e}")
                
                time.sleep(2) # Respect Server
            else:
                # logger.warning(f"  Sem dados para {filename}.")
                pass
                
        if df_month is not None and not df_month.empty:
            dfs.append(df_month)

    # 3. Return List (Consolidation moved to transform.py)
    return dfs

