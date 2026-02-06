import json
import logging
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Set, Dict, Any, Optional

import pandas as pd
import requests
from dateutil.relativedelta import relativedelta
from dotenv import load_dotenv

# --- CONFIGURATION & LOGGING ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Paths
SCRIPT_DIR = Path(__file__).parent
PASTA_RAIZ_RELATORIOS = SCRIPT_DIR.parent / "reports"
REPORTS_CONFIG_PATH = SCRIPT_DIR.parent / "config" / "reports.json"
ENV_PATH = SCRIPT_DIR.parent / "config" / ".env"

# Load Environment Variables
load_dotenv(ENV_PATH)

EMAIL = os.getenv("EMAIL")
SENHA = os.getenv("SENHA")
SALAO_ID = os.getenv("SALAO_ID", "91604")
SLUG = os.getenv("SLUG", "centro-e-r-nogales")

if not EMAIL or not SENHA:
    logger.warning("Credenciais (EMAIL/SENHA) não encontradas no arquivo .env. Verifique se o arquivo existe e está configurado.")

# URLs
URL_LOGIN = f"https://admin.avec.beauty/{SLUG}/admin"
URL_BASE_RELATORIO = "https://admin.avec.beauty/admin/relatorios/listar"

# Login Payload Base
LOGIN_PAYLOAD = {
    'email': EMAIL,
    'senha': SENHA,
    'salaoId': SALAO_ID,
    'slug': SLUG,
    'continue': 'outro',
    'logintimestamp': 'a3debc1b4b9ff358d2409ba6a98874cb'
}

# Dates Global Defaults
DEFAULT_START_DATE_STR = "2023-08"

# --- HELPER FUNCTIONS ---

def find_all_downloaded_months(subpasta_path: Path, report_type: str) -> Set[datetime]:
    """Verifica a pasta e retorna um SET de todas as datas (datetime) já baixadas."""
    if not subpasta_path.exists():
        return set()

    files = list(subpasta_path.glob('*.xlsx'))
    if not files:
        return set()

    # Regex para achar 'YYYY-MM'
    regex_padrao = re.compile(r'^(\d{4}-\d{2})_')
    regex_comp = re.compile(r'a (\d{4}-\d{2})_') # Pega a segunda data (P2)

    found_dates = set()
    for f in files:
        filename = f.name
        match = None
        if report_type == "comparacao":
            match = regex_comp.search(filename)
        else: # padrao
            match = regex_padrao.search(filename)
        
        if match:
            date_str = match.group(1)
            try:
                file_date = datetime.strptime(date_str, "%Y-%m").replace(day=1)
                found_dates.add(file_date)
            except ValueError:
                continue
    
    return found_dates

def get_month_list(start_month_dt: datetime, end_month_dt: datetime) -> List[datetime]:
    """Gera uma lista de meses (datetime) entre a data inicial e final, INCLUINDO ambas."""
    months = []
    current_month = start_month_dt
    while current_month <= end_month_dt:
        months.append(current_month)
        current_month += relativedelta(months=1)
    return months

def get_period_dates(base_month_dt: datetime) -> Dict[str, Any]:
    """Calcula as datas de início/fim P1 e P2 com base em um mês P2."""
    # P2 (Período Principal)
    inicio_p2 = base_month_dt.replace(day=1)
    fim_p2 = (inicio_p2 + relativedelta(months=1)) - timedelta(days=1)
    # P1 (Período de Comparação)
    inicio_p1 = inicio_p2 - relativedelta(months=1)
    fim_p1 = (inicio_p1 + relativedelta(months=1)) - timedelta(days=1)
    
    return {
        "data_inicio_p2": inicio_p2.strftime("%d/%m/%Y"), "data_fim_p2": fim_p2.strftime("%d/%m/%Y"),
        "data_inicio_p1": inicio_p1.strftime("%d/%m/%Y"), "data_fim_p1": fim_p1.strftime("%d/%m/%Y"),
        "dt_p1": inicio_p1, "dt_p2": inicio_p2
    }

def load_reports_config() -> List[Dict]:
    if not REPORTS_CONFIG_PATH.exists():
        logger.error(f"Arquivo de configuração de relatórios não encontrado em {REPORTS_CONFIG_PATH}")
        return []
    with open(REPORTS_CONFIG_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

# --- MAIN EXECUTION LOGIC ---

def process_report(s: requests.Session, relatorio: Dict, hoje: datetime, target_month_dt: datetime, start_date_dt: datetime):
    report_id = relatorio.get("id", "ID_DESCONHECIDO")
    subpasta = relatorio.get("nome_subpasta", "PASTA_DESCONHECIDA")
    report_type = relatorio.get("report_type", "padrao")
    suffix = relatorio.get("filename_suffix", "") 
    params_base = relatorio['params'].copy()
    colunas = relatorio.get("headers")
    subpasta_path = PASTA_RAIZ_RELATORIOS / subpasta
    
    print(f"\n--- Verificando Relatório: {report_id} ({subpasta}) ---")
    
    months_to_download = []
    
    if report_type == "sem_data":
        # Relatórios "sem_data" não fazem backfill. 
        mes_ano_extracao = hoje.strftime('%Y-%m')
        nome_arquivo_str = f"{mes_ano_extracao}_{report_id}{suffix}.xlsx"
        caminho_completo = subpasta_path / nome_arquivo_str
        
        if caminho_completo.exists():
            logger.info(f"Snapshot de {mes_ano_extracao} já existe. Pulando.")
            return
        else:
            logger.info(f"Baixando snapshot de {mes_ano_extracao}...")
            months_to_download.append(hoje.replace(day=1))
    
    else: # "padrao" ou "comparacao"
        all_required_months_list = get_month_list(start_date_dt, target_month_dt)
        all_required_months_set = set(all_required_months_list)
        
        all_downloaded_months_set = find_all_downloaded_months(subpasta_path, report_type)
        logger.debug(f"Meses já baixados: {[m.strftime('%Y-%m') for m in sorted(list(all_downloaded_months_set))]}")

        months_to_download_set = all_required_months_set - all_downloaded_months_set
        
        if not months_to_download_set:
            logger.info(f"Relatório já está 100% atualizado. Pulando.")
            return
        
        months_to_download = sorted(list(months_to_download_set))
        logger.info(f"Encontrados {len(months_to_download)} meses faltantes: {[m.strftime('%Y-%m') for m in months_to_download]}")

    # Loop de Download
    for month_dt in months_to_download:
        params_completos = params_base.copy()
        nome_arquivo_str = ""
        
        datas = get_period_dates(month_dt)
        
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
            r_download = s.get(URL_BASE_RELATORIO, params=params_completos)
            r_download.raise_for_status()
            dados_json = r_download.json()
            
            dados = dados_json.get('aaData', [])
            
            if not dados:
                logger.warning(f"Mês {month_dt.strftime('%Y-%m')} veio vazio (0 linhas). Pulando.")
                continue

            df = pd.DataFrame(dados, columns=colunas) 
            logger.info(f"JSON recebido e processado. {len(df)} linhas encontradas.")
            
            subpasta_path.mkdir(parents=True, exist_ok=True)
            caminho_completo_arquivo = subpasta_path / nome_arquivo_str
            
            df.to_excel(caminho_completo_arquivo, index=False, header=True)
            logger.info(f">>> SUCESSO! Salvo em: {caminho_completo_arquivo}")

        except Exception as e:
            logger.error(f"!!! ERRO ao baixar/processar {nome_arquivo_str}: {e}")
            if 'r_download' in locals():
                 logger.debug(f"Resposta do Servidor: {r_download.text[:200]}...")

def main():
    logger.info(f"--- Iniciando Robô de Extração Avec (v3.2 - Refatorado) ---")
    logger.info(f"Script rodando em: {SCRIPT_DIR}")
    logger.info(f"Relatórios serão salvos em: {PASTA_RAIZ_RELATORIOS}")

    # Configuração de Datas
    hoje = datetime.now()
    primeiro_dia_mes_atual = hoje.replace(day=1)
    target_month_dt = (primeiro_dia_mes_atual - timedelta(days=1)).replace(day=1) # P2 - Mês Anterior Fechado
    start_date_dt = datetime.strptime(DEFAULT_START_DATE_STR, "%Y-%m").replace(day=1)

    logger.info(f"Mês da extração: {hoje.strftime('%Y-%m')}")
    logger.info(f"Início padrão: {DEFAULT_START_DATE_STR}")
    logger.info(f"Mês alvo final (P2): {target_month_dt.strftime('%Y-%m')}")

    reports_config = load_reports_config()
    if not reports_config:
        return

    try:
        with requests.Session() as s:
            logger.info(f"Tentando login em {URL_LOGIN}...")
            r_login = s.post(URL_LOGIN, data=LOGIN_PAYLOAD)
            r_login.raise_for_status() 
            logger.info("Login realizado com SUCESSO. Iniciando downloads...")

            for relatorio in reports_config:
                process_report(s, relatorio, hoje, target_month_dt, start_date_dt)

    except Exception as e_geral:
        logger.critical(f"ERRO FATAL: {e_geral}")

if __name__ == "__main__":
    main()