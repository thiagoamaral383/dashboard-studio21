import requests
import pandas as pd
import os
from datetime import datetime, timedelta
from pathlib import Path
import re # Para ler nomes de arquivos
from dateutil.relativedelta import relativedelta # Para cálculos de mês

# --- 2. CONFIGURAÇÃO DE PASTAS ---
SCRIPT_DIR = Path(__file__).parent 
PASTA_RAIZ_RELATORIOS = SCRIPT_DIR.parent / "Relatórios"

print(f"Script iniciado em: {SCRIPT_DIR}")
print(f"Pasta de relatórios encontrada em: {PASTA_RAIZ_RELATORIOS}")

# --- 3. CONFIGURAÇÃO DE LOGIN ---
URL_LOGIN = "https://admin.avec.beauty/centro-e-r-nogales/admin" 
payload = {
    'email': 'isa.par@hotmail.com', 
    'senha': 'Salao123@',    # <-- Sua senha
    'salaoId': '91604',
    'slug': 'centro-e-r-nogales',
    'continue': 'outro',
    'logintimestamp': 'a3debc1b4b9ff358d2409ba6a98874cb' 
}

# --- 4. CONFIGURAÇÃO DE DATAS GLOBAIS ---
hoje = datetime.now()
primeiro_dia_mes_atual = hoje.replace(day=1)
# P2 - Mês Anterior Fechado (Nosso "Mês Alvo" final)
TARGET_MONTH_DT = primeiro_dia_mes_atual - timedelta(days=1)
TARGET_MONTH_DT = TARGET_MONTH_DT.replace(day=1) # Ex: 01/10/2025
# Data mais antiga para buscar
DEFAULT_START_DATE_STR = "2023-08" # Baseado nos seus arquivos
DEFAULT_START_DATE_DT = datetime.strptime(DEFAULT_START_DATE_STR, "%Y-%m").replace(day=1)

print(f"Mês da extração: {hoje.strftime('%Y-%m')}")
print(f"Data de início padrão: {DEFAULT_START_DATE_STR}")
print(f"Mês alvo final (P2): {TARGET_MONTH_DT.strftime('%Y-%m')}")

# --- 5. O Cérebro: O que baixar e Onde salvar (Sua lista final) ---
URL_BASE_RELATORIO = "https://admin.avec.beauty/admin/relatorios/listar"
RELATORIOS_PARA_BAIXAR = [
    {
        "id": "0002", "nome_subpasta": "0002_Clientes", "report_type": "padrao", "filename_suffix": "",
        "params": { 'relatorio': '0002', 'salao': '91604', 'como_conheceu': 'ALL' },
        "headers": ["Cliente", "Celular", "E-mail", "Última Visita", "Total Consumido", "Profissionais", "Número de Visitas"]
    },
    {
        "id": "0007", "nome_subpasta": "0007_Retorno", "report_type": "comparacao", "filename_suffix": "",
        "params": { 'relatorio': '0007', 'salao': '91604' },
        "headers": ["Cliente", "E-mail", "Telefone", "Celular", "Sexo", "Última Visita"]
    },
    {
        "id": "0126", "nome_subpasta": "0126_Ocupacao", "report_type": "padrao", "filename_suffix": "",
        "params": { 'relatorio': '0126', 'salao': '91604', 'minutos': '60' },
        "headers": ["Profissional", "Cargo", "Carga Diária", "Dias Úteis", "Total Disponível", "Total Agendado", "Taxa de Ocupação (%)"]
    },
    {
        "id": "0186", "nome_subpasta": "0186_Comandas", "report_type": "padrao", "filename_suffix": "",
        "params": { 'relatorio': '0186', 'salao': '91604' },
        "headers": ["Data", "Comanda", "Item", "Tipo", "Categoria", "Profissional", "Assistente 1", "Assistente 2", "Comissão (%)", "Cliente", "Email", "Telefone", "Celular", "Valor", "Desconto", "Qtd.", "Custo", "Comissão", "Líquido", "UA"]
    },
    {
        "id": "0188", "nome_subpasta": "0188_BandeirasCartao", "report_type": "padrao", "filename_suffix": "",
        "params": { 'relatorio': '0188', 'salao': '91604' },
        "headers": ["Bandeira", "Valor faturado", "Valor"]
    },
    {
        "id": "0229", "nome_subpasta": "0229_Profissionais", "report_type": "sem_data", "filename_suffix": "",
        "params": { 'relatorio': '0229', 'salao': '91604' },
        "headers": ["ID", "Nome", "Cargo", "CPF", "Apelido", "Especialidade", "Contratação", "Grupo de acesso", "Data Cadastro"]
    },
    {
        "id": "0387", "nome_subpasta": "0387_Financeiro/Competencia", "report_type": "padrao", "filename_suffix": "_Competencia",
        "params": { 'relatorio': '0387', 'salao': '91604', 'tipo': 'competencia' },
        "headers": ["Competência", "Pagamento", "Cobrança", "Título", "Conta Bancária", "Categoria", "Fornecedor/Cliente", "Centro de Custos", "Valor", "Observações"]
    },
    {
        "id": "0387", "nome_subpasta": "0387_Financeiro/Caixa", "report_type": "padrao", "filename_suffix": "_Caixa", 
        "params": { 'relatorio': '0387', 'salao': '91604', 'tipo': 'pagamento' },
        "headers": ["Competência", "Pagamento", "Cobrança", "Título", "Conta Bancária", "Categoria", "Fornecedor/Cliente", "Centro de Custos", "Valor", "Observações"]
    },
]

# --- 6. NOVAS FUNÇÕES DE LÓGICA (v3.1) ---

def find_all_downloaded_months(subpasta_path, report_type):
    """Verifica a pasta e retorna um SET de todas as datas (datetime) já baixadas."""
    if not subpasta_path.exists():
        return set() # Retorna um set vazio

    files = list(subpasta_path.glob('*.xlsx'))
    if not files:
        return set() # Retorna um set vazio

    # Regex para achar 'YYYY-MM'
    regex_padrao = re.compile(r'^(\d{4}-\d{2})_')
    regex_comp = re.compile(r'a (\d{4}-\d{2})_') # Pega a segunda data (P2)

    found_dates = set() # Usamos um SET para evitar duplicatas
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
                found_dates.add(file_date) # Adiciona ao SET
            except ValueError:
                continue # Ignora arquivos com nome fora do padrão
    
    return found_dates # Retorna o SET completo

def get_month_list(start_month_dt, end_month_dt):
    """Gera uma lista de meses (datetime) entre a data inicial e final, INCLUINDO ambas."""
    months = []
    current_month = start_month_dt
    while current_month <= end_month_dt:
        months.append(current_month)
        current_month += relativedelta(months=1)
    return months

def get_period_dates(base_month_dt):
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

# --- 7. EXECUÇÃO PRINCIPAL (v3.1) ---
print(f"\n--- Iniciando Robô de Extração Avec (v3.1 - Caçador de Gaps) ---")
try:
    with requests.Session() as s:
        # --- ETAPA A: LOGIN ---
        print(f"Tentando login em {URL_LOGIN}...")
        r_login = s.post(URL_LOGIN, data=payload)
        r_login.raise_for_status() 
        print("Login realizado com SUCESSO. Iniciando downloads...")

        # --- ETAPA B: LOOP DE DOWNLOADS ---
        for relatorio in RELATORIOS_PARA_BAIXAR:
            report_id = relatorio.get("id", "ID_DESCONHECIDO")
            subpasta = relatorio.get("nome_subpasta", "PASTA_DESCONHECIDA")
            report_type = relatorio.get("report_type", "padrao")
            suffix = relatorio.get("filename_suffix", "") 
            params_base = relatorio['params'].copy()
            colunas = relatorio.get("headers")
            subpasta_path = PASTA_RAIZ_RELATORIOS / subpasta
            
            print(f"\n--- Verificando Relatório: {report_id} ({subpasta}) ---")
            
            # --- LÓGICA DE BACKFILL (v3.1) ---
            months_to_download = []
            
            if report_type == "sem_data":
                # Relatórios "sem_data" não fazem backfill. 
                mes_ano_extracao = hoje.strftime('%Y-%m')
                nome_arquivo_str = f"{mes_ano_extracao}_{report_id}{suffix}.xlsx"
                caminho_completo = subpasta_path / nome_arquivo_str
                
                if caminho_completo.exists():
                    print(f"Snapshot de {mes_ano_extracao} já existe. Pulando.")
                    continue
                else:
                    print(f"Baixando snapshot de {mes_ano_extracao}...")
                    months_to_download.append(hoje.replace(day=1)) # Adiciona "hoje" à lista
            
            else: # "padrao" ou "comparacao"
                # 1. Gerar lista de TODOS os meses que DEVERÍAMOS ter
                all_required_months_list = get_month_list(DEFAULT_START_DATE_DT, TARGET_MONTH_DT)
                all_required_months_set = set(all_required_months_list)
                
                # 2. Achar todos os meses que JÁ TEMOS
                all_downloaded_months_set = find_all_downloaded_months(subpasta_path, report_type)
                print(f"Meses já baixados: {[m.strftime('%Y-%m') for m in sorted(list(all_downloaded_months_set))]}")

                # 3. Calcular os meses faltantes (diferença de sets)
                months_to_download_set = all_required_months_set - all_downloaded_months_set
                
                if not months_to_download_set:
                    print(f"Relatório já está 100% atualizado (de {DEFAULT_START_DATE_STR} até {TARGET_MONTH_DT.strftime('%Y-%m')}). Pulando.")
                    continue
                
                # Converte para lista e ordena para baixar em ordem cronológica
                months_to_download = sorted(list(months_to_download_set))
                print(f"Encontrados {len(months_to_download)} meses faltantes: {[m.strftime('%Y-%m') for m in months_to_download]}")

            # --- LOOP INTERNO: Baixa cada mês faltante ---
            for month_dt in months_to_download:
                
                params_completos = params_base.copy()
                nome_arquivo_str = ""
                
                # Calcula as datas e nomes de arquivo para ESTE mês
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
                    # Não adiciona datas aos params
                    mes_ano_extracao = hoje.strftime('%Y-%m')
                    nome_arquivo_str = f"{mes_ano_extracao}_{report_id}{suffix}.xlsx"
                
                print(f"\nBaixando: {nome_arquivo_str}")

                try:
                    # 1. FAZ A REQUISIÇÃO GET
                    r_download = s.get(URL_BASE_RELATORIO, params=params_completos)
                    r_download.raise_for_status()
                    dados_json = r_download.json()
                    
                    # 2. EXTRAI OS DADOS E CABEÇALHOS
                    dados = dados_json['aaData']
                    
                    if not dados:
                        print(f"Mês {month_dt.strftime('%Y-%m')} veio vazio (0 linhas). Pulando.")
                        continue # Pula para o próximo mês

                    # 3. CONVERTE PARA PANDAS
                    df = pd.DataFrame(dados, columns=colunas) 
                    print(f"JSON recebido e processado. {len(df)} linhas encontradas.")
                    
                    # 4. PREPARA O CAMINHO DE SAÍDA
                    subpasta_path.mkdir(parents=True, exist_ok=True)
                    caminho_completo_arquivo = subpasta_path / nome_arquivo_str
                    
                    # 5. SALVA A TABELA COMO ARQUIVO EXCEL
                    df.to_excel(caminho_completo_arquivo, index=False, header=True)
                    print(f">>> SUCESSO! Salvo em: {caminho_completo_arquivo}")

                except Exception as e:
                    print(f"!!! ERRO ao baixar/processar {nome_arquivo_str}: {e}")
                    if 'r_download' in locals():
                        print(f"Resposta do Servidor: {r_download.text[:200]}...")

except Exception as e_geral:
    print(f"\n!!! ERRO FATAL: {e_geral}")