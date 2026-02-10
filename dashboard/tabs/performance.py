"""
Performance (Comercial) Tab - Business Performance Analytics
"""

import streamlit as st
import pandas as pd
from utils.formatters import format_currency
from utils.database import query_data
from components.charts import (
    render_professional_ranking,
    render_service_pareto,
    render_category_mix,
    render_dow_performance
)


def render():
    """Render the Performance (Commercial) tab content."""
    st.markdown("### Indicadores de Performance Comercial")
    st.markdown("")
    
    # Get date range from session state
    start_date = st.session_state.start_date
    end_date = st.session_state.end_date
    
    # Query sales data from fct_vendas
    query = f"""
        SELECT
            data,
            id_comanda,
            comanda,
            profissional,
            servico,
            grupo_servico,
            categoria_servico,
            valor
        FROM fct_vendas
        WHERE data BETWEEN '{start_date}' AND '{end_date}'
            AND valor > 0
    """
    
    df_vendas = query_data(query)
    
    # Check if we have data
    if df_vendas.empty:
        st.info("Não há dados de vendas no período selecionado.")
        return
    
    # Limpeza Visual: Title Case em colunas de texto
    cols_to_title = ['profissional', 'servico', 'categoria_servico']
    for col in cols_to_title:
        if col in df_vendas.columns:
            df_vendas[col] = df_vendas[col].astype(str).str.title()
    
    # =========================================================================
    # KPI CALCULATIONS
    # =========================================================================
    
    # 1. Faturamento Total (Bruto)
    faturamento_total = df_vendas['valor'].sum()
    
    # 2. Fat. Médio Diário - Faturamento Total / Dias com Vendas
    num_dias_vendas = df_vendas['data'].nunique()
    faturamento_medio_diario = faturamento_total / num_dias_vendas if num_dias_vendas > 0 else 0.0
    
    # 3. Atendimentos (#) - Número de comandas únicas
    num_atendimentos = df_vendas['id_comanda'].nunique()
    
    # 4. Ticket Médio (R$) - Faturamento Total / Atendimentos
    ticket_medio = faturamento_total / num_atendimentos if num_atendimentos > 0 else 0
    
    # 5. Itens por Cesta - Total de linhas (serviços) / Atendimentos
    total_itens = len(df_vendas)
    itens_por_cesta = total_itens / num_atendimentos if num_atendimentos > 0 else 0
    
    # =========================================================================
    # KPI CARDS (Row 1)
    # =========================================================================
    
    cols_kpi = st.columns(4)
    
    with cols_kpi[0]:
        st.metric(
            label="Fat. Médio Diário",
            value=format_currency(faturamento_medio_diario),
            help="Faturamento médio por dia com vendas\n\nCálculo: Faturamento Total / Quantidade de Dias com Vendas"
        )
    
    with cols_kpi[1]:
        st.metric(
            label="Atendimentos",
            value=f"{num_atendimentos:,}".replace(',', '.'),
            help="Número de atendimentos únicos (comandas) no período"
        )
    
    with cols_kpi[2]:
        st.metric(
            label="Ticket Médio",
            value=format_currency(ticket_medio),
            help="Faturamento médio por atendimento\n\nCálculo: Faturamento Total / Atendimentos"
        )
    
    with cols_kpi[3]:
        st.metric(
            label="Itens por Cesta",
            value=f"{itens_por_cesta:.1f}".replace('.', ','),
            help="Média de serviços realizados por visita. Ex: Pé + Mão conta como 1 item se for um pacote, ou 2 se lançados separados.\n\nCálculo: Total de Itens / Atendimentos"
        )
    
    st.markdown("---")
    
    # =========================================================================
    # CHARTS SECTION
    # =========================================================================
    
    # Row 2: Professional Ranking (Left) + Category Mix (Right)
    col_row2 = st.columns([2, 1])
    
    with col_row2[0]:
        st.markdown("### Ranking de Profissionais")
        render_professional_ranking(df_vendas)
    
    with col_row2[1]:
        st.markdown("### Mix de Categorias")
        render_category_mix(df_vendas)
    
    st.markdown("")
    
    # Row 3: Top 10 Services (Left) + Day of Week Performance (Right)
    col_row3 = st.columns([2, 1])
    
    with col_row3[0]:
        st.markdown("### Top 10 Serviços")
        render_service_pareto(df_vendas)
    
    with col_row3[1]:
        st.markdown("### Performance por Dia da Semana")
        render_dow_performance(df_vendas)
