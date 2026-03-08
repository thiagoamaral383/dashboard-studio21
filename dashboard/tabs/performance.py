"""
Performance (Comercial) Tab - Business Performance Analytics
"""

import streamlit as st
import pandas as pd
from utils.formatters import format_currency, calculate_previous_period, calculate_same_period_last_year
from utils.database import query_data
from components.charts import (
    render_professional_ranking,
    render_service_pareto,
    render_category_mix,
    render_dow_performance
)


def get_sales_data(start_date, end_date):
    """Query sales data for a specific period."""
    query = f"""
        SELECT
            data,
            id_comanda,
            valor
        FROM fct_vendas
        WHERE data BETWEEN '{start_date}' AND '{end_date}'
            AND valor > 0
    """
    return query_data(query)


def calculate_kpis(df):
    """Calculate main KPIs from sales dataframe."""
    if df.empty:
        return {
            "faturamento": 0.0,
            "faturamento_medio_diario": 0.0,
            "atendimentos": 0,
            "ticket_medio": 0.0,
            "itens_por_cesta": 0.0
        }
    
    faturamento_total = df['valor'].sum()
    num_dias_vendas = df['data'].nunique()
    faturamento_medio_diario = faturamento_total / num_dias_vendas if num_dias_vendas > 0 else 0.0
    num_atendimentos = df['id_comanda'].nunique()
    ticket_medio = faturamento_total / num_atendimentos if num_atendimentos > 0 else 0.0
    total_itens = len(df)
    itens_por_cesta = total_itens / num_atendimentos if num_atendimentos > 0 else 0.0
    
    return {
        "faturamento": faturamento_total,
        "faturamento_medio_diario": faturamento_medio_diario,
        "atendimentos": num_atendimentos,
        "ticket_medio": ticket_medio,
        "itens_por_cesta": itens_por_cesta
    }


def render():
    """Render the Performance (Commercial) tab content."""
    st.markdown("### Indicadores de Performance Comercial")
    st.markdown("")
    
    # Get date range from session state
    start_date = st.session_state.start_date
    end_date = st.session_state.end_date
    
    # Calculate comparison periods
    prev_start, prev_end = calculate_previous_period(start_date, end_date)
    yoy_start, yoy_end = calculate_same_period_last_year(start_date, end_date)
    
    # Query current period data (Full for charts/cleaning)
    query_full = f"""
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
    df_vendas = query_data(query_full)
    
    # Check if we have data
    if df_vendas.empty:
        st.info("Não há dados de vendas no período selecionado.")
        return
    
    # Query comparison data (Lightweight)
    df_prev = get_sales_data(prev_start, prev_end)
    df_yoy = get_sales_data(yoy_start, yoy_end)
    
    # Calculate KPIs for all periods
    kpis_atual = calculate_kpis(df_vendas)
    kpis_prev = calculate_kpis(df_prev)
    kpis_yoy = calculate_kpis(df_yoy)
    
    # Limpeza Visual: Title Case em colunas de texto
    cols_to_title = ['profissional', 'servico', 'categoria_servico']
    for col in cols_to_title:
        if col in df_vendas.columns:
            df_vendas[col] = df_vendas[col].astype(str).str.title()
    
    # Helper to format delta percentage string
    def format_delta_str(val_atual, val_prev, val_yoy):
        pct_mom = ((val_atual - val_prev) / val_prev * 100) if val_prev > 0 else 0
        pct_yoy = ((val_atual - val_yoy) / val_yoy * 100) if val_yoy > 0 else None
        
        mom_str = f"{pct_mom:+.1f}%".replace('.', ',')
        if pct_yoy is None:
            return f"{mom_str} (Mês)"
        yoy_str = f"{pct_yoy:+.1f}%".replace('.', ',')
        return f"{yoy_str} (Ano) | {mom_str} (Mês)"

    # =========================================================================
    # KPI CARDS (Row 1)
    # =========================================================================
    
    cols_kpi = st.columns(4)
    
    with cols_kpi[0]:
        st.metric(
            label="Fat. Médio Diário",
            value=format_currency(kpis_atual["faturamento_medio_diario"]),
            delta=format_delta_str(kpis_atual["faturamento_medio_diario"], kpis_prev["faturamento_medio_diario"], kpis_yoy["faturamento_medio_diario"]),
            delta_color="normal",
            help="Faturamento médio por dia com vendas\n\nCálculo: Faturamento Total / Quantidade de Dias com Vendas"
        )
    
    with cols_kpi[1]:
        st.metric(
            label="Atendimentos",
            value=f"{kpis_atual['atendimentos']:,}".replace(',', '.'),
            delta=format_delta_str(kpis_atual["atendimentos"], kpis_prev["atendimentos"], kpis_yoy["atendimentos"]),
            delta_color="normal",
            help="Número de atendimentos únicos (comandas) no período"
        )
    
    with cols_kpi[2]:
        st.metric(
            label="Ticket Médio",
            value=format_currency(kpis_atual["ticket_medio"]),
            delta=format_delta_str(kpis_atual["ticket_medio"], kpis_prev["ticket_medio"], kpis_yoy["ticket_medio"]),
            delta_color="normal",
            help="Faturamento médio por atendimento\n\nCálculo: Faturamento Total / Atendimentos"
        )
    
    with cols_kpi[3]:
        st.metric(
            label="Itens por Cesta",
            value=f"{kpis_atual['itens_por_cesta']:.1f}".replace('.', ','),
            delta=format_delta_str(kpis_atual["itens_por_cesta"], kpis_prev["itens_por_cesta"], kpis_yoy["itens_por_cesta"]),
            delta_color="normal",
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
