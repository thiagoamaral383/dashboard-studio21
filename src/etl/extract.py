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
from concurrent.futures import ThreadPoolExecutor, as_completed

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

MAX_WORKERS = 4  # Conservative worker count

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

    r_download = session.get(URL_BASE_RELATORIO, params=params_completos)
    
    if r_download.status_code == 429:
        raise Exception("Rate Limit (429)")
        
    r_download.raise_for_status()
    dados_json = r_download.json()
    return dados_json.get('aaData', [])

def process_month(month: datetime, session: requests.Session, config_list: List[Dict], report_type_filter: Optional[str] = None) -> Tuple[List[pd.DataFrame], List[pd.DataFrame]]:
    """
    Worker function to process a single month.
    Returns a tuple of (lista_caixa, lista_competencia) dataframes for that month.
    """
    month_str = month.strftime("%Y-%m")
    local_caixa = []
    local_competencia = []
    
    for report_config in config_list:
        subpasta = report_config.get("nome_subpasta", "")
        # Identify types
        is_caixa = "Caixa" in subpasta or "Caixa" in report_config.get("filename_suffix", "")
        is_competencia = "Competencia" in subpasta or "Competencia" in report_config.get("filename_suffix", "")
        
        # Filter check
        if report_type_filter == 'financial' and not (is_caixa or is_competencia):
            continue
        
        suffix = report_config.get("filename_suffix", "")
        report_id = report_config.get("id")

        # Filename Logic
        if report_id == "0007":
             datas = utils.get_period_dates(month)
             p1_str = datas['dt_p1'].strftime('%Y-%m')
             p2_str = datas['dt_p2'].strftime('%Y-%m')
             filename = f"{p1_str} a {p2_str}_{report_id}{suffix}.xlsx"
        else:
             filename = f"{month_str}_{report_id}{suffix}.xlsx"
        
        file_path = PASTA_RAIZ_RELATORIOS / subpasta / filename
        
        # 1. Smart Cache
        df = None
        if file_path.exists():
            try:
                # Keep using openpyxl for reading (default)
                df = pd.read_excel(file_path, dtype=str)
                # Runtime Injection from Function Argument (not file)
                df['data_competencia'] = month
            except Exception as e:
                logger.error(f"  Erro ao ler cache {filename}: {e}. Tentando baixar novamente.")
        
        # 2. Download
        if df is None:
            logger.info(f"  [DOWNLOAD] Baixando: {filename}...")
            
            # Retry Mechanism
            max_retries = 3
            backoff = 2
            raw_data = None
            
            for attempt in range(max_retries):
                try:
                    raw_data = fetch_data_from_api(session, report_config, month)
                    if raw_data is not None:
                        break # Success
                except Exception as e:
                    logger.warning(f"  Falha tentativa {attempt+1}/{max_retries} para {filename}: {e}")
                    if attempt < max_retries - 1:
                        time.sleep(backoff * (attempt + 1))
                    else:
                        logger.error(f"  Falha definitiva para {filename} após retries.")
            
            if raw_data:
                headers = report_config.get("headers", [])
                headers = report_config.get("headers", [])
                df = pd.DataFrame(raw_data, columns=headers)
                # Runtime Injection
                df['data_competencia'] = month
                
                # Save Local
                try:
                    load_local.save_to_excel(df, subpasta, filename) 
                except Exception as e:
                    logger.error(f"  Erro ao salvar {filename}: {e}")
                
                # Respect server is handled by limited workers + natural network latency, but we can add small sleep
                time.sleep(1)
                
            else:
                pass
        
        # 3. Aggregate
        if df is not None: # keep empty dfs possibly? Original code appended them.
            if is_caixa:
                local_caixa.append(df)
            elif is_competencia:
                local_competencia.append(df)
            else:
                local_caixa.append(df) # Generic fallback

    return local_caixa, local_competencia

def extract_financial_data(start_date_str: str = "2023-08-01") -> Tuple[List[pd.DataFrame], List[pd.DataFrame]]:
    """
    Main entry point for Financial Data Extraction (0387).
    Uses ThreadPoolExecutor for concurrency.
    """
    logger.info(f"Iniciando extração financeira a partir de {start_date_str} com MAX_WORKERS={MAX_WORKERS}...")
    
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
    today = datetime.now()
    months_to_process = get_month_range(start_date, today)

    config = load_reports_config()
    reports_0387 = [r for r in config if r.get("id") == "0387"]
    
    if not reports_0387:
        logger.error("Configuração do relatório 0387 não encontrada.")
        return [], []

    session = login()

    lista_caixa = []
    lista_competencia = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_month = {
            executor.submit(process_month, month, session, reports_0387, 'financial'): month 
            for month in months_to_process
        }
        
        for future in as_completed(future_to_month):
            month = future_to_month[future]
            month_str = month.strftime("%Y-%m")
            try:
                c_list, comp_list = future.result()
                if c_list:
                    lista_caixa.extend(c_list)
                if comp_list:
                    lista_competencia.extend(comp_list)
                # logger.info(f"Mês {month_str} concluído.")
            except Exception as exc:
                logger.error(f"Erro ao processar mês {month_str}: {exc}")

    return lista_caixa, lista_competencia

def extract_generic_report(report_config: Dict, start_date_str: str = "2023-08-01") -> List[pd.DataFrame]:
    """
    Extracts data for a generic report using Smart Cache and Full Refresh strategy.
    Uses ThreadPoolExecutor for concurrency.
    """
    report_id = report_config.get("id", "UNKNOWN")
    subpasta = report_config.get("nome_subpasta", "")
    
    logger.info(f"Iniciando extração genérica para {report_id} ({subpasta}) com MAX_WORKERS={MAX_WORKERS}...")
    
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
    today = datetime.now()
    months_to_process = get_month_range(start_date, today)
    
    session = login()
    
    dfs = []
    config_list = [report_config]
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_month = {
            executor.submit(process_month, month, session, config_list, 'generic'): month 
            for month in months_to_process
        }
        
        for future in as_completed(future_to_month):
            month = future_to_month[future]
            try:
                res_list, _ = future.result() 
                if res_list:
                    dfs.extend(res_list)
            except Exception as exc:
                logger.error(f"Erro ao processar mês {month}: {exc}")

    return dfs

def identify_months_to_download(relatorio: Dict, hoje: datetime, target_month_dt: datetime, start_date_dt: datetime) -> List[datetime]:
    # Legacy function for backward compatibility
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
        
    all_months = utils.get_month_list(start_date_dt, target_month_dt)
    months_to_download = []
    
    for month in all_months:
        if report_id == "0007":
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
