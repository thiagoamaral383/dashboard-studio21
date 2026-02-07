import json
import logging
import os
import requests
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from dotenv import load_dotenv

from .utils import get_period_dates, get_month_list, find_all_downloaded_months

logger = logging.getLogger(__name__)

# Paths - Assuming this file is in src/etl/
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
    r_login = session.post(URL_LOGIN, data=LOGIN_PAYLOAD)
    r_login.raise_for_status()
    logger.info("Login realizado com SUCESSO.")
    return session

def identify_months_to_download(relatorio: Dict, hoje: datetime, target_month_dt: datetime, start_date_dt: datetime) -> List[datetime]:
    report_id = relatorio.get("id", "ID_DESCONHECIDO")
    subpasta = relatorio.get("nome_subpasta", "PASTA_DESCONHECIDA")
    report_type = relatorio.get("report_type", "padrao")
    suffix = relatorio.get("filename_suffix", "")
    
    subpasta_path = PASTA_RAIZ_RELATORIOS / subpasta
    
    if report_type == "sem_data":
        mes_ano_extracao = hoje.strftime('%Y-%m')
        nome_arquivo_str = f"{mes_ano_extracao}_{report_id}{suffix}.xlsx"
        caminho_completo = subpasta_path / nome_arquivo_str
        
        if caminho_completo.exists():
            logger.info(f"Snapshot de {mes_ano_extracao} já existe. Pulando.")
            return []
        else:
            return [hoje.replace(day=1)]
    
    else: # "padrao" ou "comparacao"
        all_required_months_list = get_month_list(start_date_dt, target_month_dt)
        all_required_months_set = set(all_required_months_list)
        
        all_downloaded_months_set = find_all_downloaded_months(subpasta_path, report_type)
        
        months_to_download_set = all_required_months_set - all_downloaded_months_set
        
        if not months_to_download_set:
            return []
        
        return sorted(list(months_to_download_set))

def fetch_data_for_month(session: requests.Session, relatorio: Dict, month_dt: datetime, hoje: datetime) -> Tuple[Optional[List[Dict]], str]:
    """
    Fetches data for a specific month/report configuration.
    Returns: (Data List, Filename to save)
    """
    report_id = relatorio.get("id", "ID_DESCONHECIDO")
    report_type = relatorio.get("report_type", "padrao")
    suffix = relatorio.get("filename_suffix", "")
    params_base = relatorio['params'].copy()
    
    datas = get_period_dates(month_dt)
    params_completos = params_base.copy()
    nome_arquivo_str = ""

    if report_type == "padrao":
        params_completos['inicio'] = datas['data_inicio_p2']
        params_completos['fim'] = datas['data_fim_p2']
        nome_arquivo_str = f"{datas['dt_p2'].strftime('%Y-%m')}_{report_id}{suffix}.xlsx"
    
    elif report_type == "comparacao":
        params_completos['inicio1'] = datas['data_inicio_p1']
        params_completos['fim1'] = datas['data_fim_p1']
        params_completos['inicio2'] = datas['data_inicio_p2']
        params_completos['fim2'] = datas['data_fim_p2']
        mes_ano_p1 = datas['dt_p1'].strftime('%Y-%m')
        mes_ano_p2 = datas['dt_p2'].strftime('%Y-%m')
        nome_arquivo_str = f"{mes_ano_p1} a {mes_ano_p2}_{report_id}{suffix}.xlsx"
    
    elif report_type == "sem_data":
        mes_ano_extracao = hoje.strftime('%Y-%m')
        nome_arquivo_str = f"{mes_ano_extracao}_{report_id}{suffix}.xlsx"

    logger.info(f"Baixando: {nome_arquivo_str}")

    try:
        r_download = session.get(URL_BASE_RELATORIO, params=params_completos)
        r_download.raise_for_status()
        dados_json = r_download.json()
        dados = dados_json.get('aaData', [])
        return dados, nome_arquivo_str
    except Exception as e:
        logger.error(f"Erro ao baixar dados: {e}")
        return None, nome_arquivo_str
