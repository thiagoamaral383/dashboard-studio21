import re
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Set, Dict, Any
from dateutil.relativedelta import relativedelta

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
