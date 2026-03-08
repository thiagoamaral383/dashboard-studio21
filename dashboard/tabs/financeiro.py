"""
Financeiro Tab - Financial KPIs and Analysis
"""

import streamlit as st
import pandas as pd
from datetime import date
from utils.formatters import format_currency, calculate_previous_period, calculate_same_period_last_year
from utils.database import query_data
from components.kpi_cards import render_kpi_grid
from components.charts import render_financial_evolution, render_top_expenses


def calculate_metric(df, grupo_metrica_list):
    """
    Calculate sum of valores for specified grupo_metrica values.
    
    Args:
        df: DataFrame with query results
        grupo_metrica_list: List of grupo_metrica values to filter
        
    Returns:
        Sum of valor column, or 0 if no data
    """
    if df.empty:
        return 0.0
    
    # Filter by grupo_metrica
    if isinstance(grupo_metrica_list, list):
        filtered = df[df['grupo_metrica'].isin(grupo_metrica_list)]
    else:
        filtered = df[df['grupo_metrica'] == grupo_metrica_list]
    
    # Sum the valor column
    return filtered['valor'].sum() if not filtered.empty else 0.0


def render():
    """Render the Financeiro (Financial) tab content."""
    st.markdown("### Indicadores Financeiros")
    st.markdown("")
    
    # Get date range from session state
    start_date = st.session_state.start_date
    end_date = st.session_state.end_date
    
    # Calculate previous period (PoP)
    prev_start, prev_end = calculate_previous_period(start_date, end_date)
    
    # Calculate same period last year (YoY)
    yoy_start, yoy_end = calculate_same_period_last_year(start_date, end_date)
    
    # Query current period data (Detailed for Audit and Charts)
    current_query = f"""
        SELECT 
            data,
            grupo_metrica,
            categoria_detalhada as categoria,
            descricao,
            valor
        FROM rep_financeiro_competencia
        WHERE data BETWEEN '{start_date}' AND '{end_date}'
        ORDER BY data DESC
    """
    
    # Query previous period data (Aggregated for KPIs)
    previous_query = f"""
        SELECT 
            grupo_metrica,
            SUM(valor) as valor
        FROM rep_financeiro_competencia
        WHERE data BETWEEN '{prev_start}' AND '{prev_end}'
        GROUP BY grupo_metrica
    """
    
    # Query YoY data (Aggregated for KPIs)
    yoy_query = f"""
        SELECT 
            grupo_metrica,
            SUM(valor) as valor
        FROM rep_financeiro_competencia
        WHERE data BETWEEN '{yoy_start}' AND '{yoy_end}'
        GROUP BY grupo_metrica
    """
    
    # Execute queries
    df_current = query_data(current_query)
    df_previous = query_data(previous_query)
    df_yoy = query_data(yoy_query)
    
    # Calculate metrics for current period
    # Note: df_current is detailed, so calculate_metric works fine (it sums 'valor')
    receita_bruta_atual = calculate_metric(df_current, 'Receita Bruta')
    comissao_atual = calculate_metric(df_current, 'Comissões')
    taxas_atual = calculate_metric(df_current, 'Despesas Financeiras')
    despesas_atual = calculate_metric(df_current, ['Despesas Operacionais', 'Despesas Financeiras', 'Resultado Financeiro'])
    lucro_liquido_atual = df_current['valor'].sum() if not df_current.empty else 0.0
    
    # Calculate metrics for previous period (PoP)
    receita_bruta_anterior = calculate_metric(df_previous, 'Receita Bruta')
    comissao_anterior = calculate_metric(df_previous, 'Comissões')
    taxas_anterior = calculate_metric(df_previous, 'Despesas Financeiras')
    despesas_anterior = calculate_metric(df_previous, ['Despesas Operacionais', 'Despesas Financeiras', 'Resultado Financeiro'])
    lucro_liquido_anterior = df_previous['valor'].sum() if not df_previous.empty else 0.0
    
    # Calculate metrics for YoY
    receita_bruta_yoy = calculate_metric(df_yoy, 'Receita Bruta')
    comissao_yoy = calculate_metric(df_yoy, 'Comissões')
    taxas_yoy = calculate_metric(df_yoy, 'Despesas Financeiras')
    despesas_yoy = calculate_metric(df_yoy, ['Despesas Operacionais', 'Despesas Financeiras', 'Resultado Financeiro'])
    lucro_liquido_yoy = df_yoy['valor'].sum() if not df_yoy.empty else 0.0
    
    # Calculate Ratios (Efficiency Metrics) - Current
    ratio_margem_atual = (lucro_liquido_atual / receita_bruta_atual * 100) if receita_bruta_atual > 0 else 0.0
    ratio_comissao_atual = (abs(comissao_atual) / receita_bruta_atual * 100) if receita_bruta_atual > 0 else 0.0
    ratio_taxas_atual = (abs(taxas_atual) / receita_bruta_atual * 100) if receita_bruta_atual > 0 else 0.0

    # Calculate Ratios - Previous (PoP)
    ratio_margem_anterior = (lucro_liquido_anterior / receita_bruta_anterior * 100) if receita_bruta_anterior > 0 else 0.0
    ratio_comissao_anterior = (abs(comissao_anterior) / receita_bruta_anterior * 100) if receita_bruta_anterior > 0 else 0.0
    ratio_taxas_anterior = (abs(taxas_anterior) / receita_bruta_anterior * 100) if receita_bruta_anterior > 0 else 0.0

    # Calculate Ratios - YoY
    ratio_margem_yoy = (lucro_liquido_yoy / receita_bruta_yoy * 100) if receita_bruta_yoy > 0 else 0.0
    ratio_comissao_yoy = (abs(comissao_yoy) / receita_bruta_yoy * 100) if receita_bruta_yoy > 0 else 0.0
    ratio_taxas_yoy = (abs(taxas_yoy) / receita_bruta_yoy * 100) if receita_bruta_yoy > 0 else 0.0

    # Calculate Main KPI Deltas (Percentage Change)
    pct_receita_pop = ((receita_bruta_atual - receita_bruta_anterior) / receita_bruta_anterior * 100) if receita_bruta_anterior != 0 else 0
    pct_comissao_pop = ((abs(comissao_atual) - abs(comissao_anterior)) / abs(comissao_anterior) * 100) if comissao_anterior != 0 else 0
    pct_despesas_pop = ((abs(despesas_atual) - abs(despesas_anterior)) / abs(despesas_anterior) * 100) if despesas_anterior != 0 else 0
    pct_lucro_pop = ((lucro_liquido_atual - lucro_liquido_anterior) / abs(lucro_liquido_anterior) * 100) if lucro_liquido_anterior != 0 else 0
    
    # Calculate YoY deltas (percentage) - Handle division by zero/missing data
    pct_receita_yoy = ((receita_bruta_atual - receita_bruta_yoy) / receita_bruta_yoy * 100) if receita_bruta_yoy != 0 else None
    pct_comissao_yoy = ((abs(comissao_atual) - abs(comissao_yoy)) / abs(comissao_yoy) * 100) if comissao_yoy != 0 else None
    pct_despesas_yoy = ((abs(despesas_atual) - abs(despesas_yoy)) / abs(despesas_yoy) * 100) if despesas_yoy != 0 else None
    pct_lucro_yoy = ((lucro_liquido_atual - lucro_liquido_yoy) / abs(lucro_liquido_yoy) * 100) if lucro_liquido_yoy != 0 else None
    
    # Calculate Efficiency Deltas (Percentage Points - p.p.)
    delta_margem_pop = ratio_margem_atual - ratio_margem_anterior
    delta_margem_yoy = ratio_margem_atual - ratio_margem_yoy
    
    delta_comissao_pop = ratio_comissao_atual - ratio_comissao_anterior
    delta_comissao_yoy = ratio_comissao_atual - ratio_comissao_yoy
    
    delta_taxas_pop = ratio_taxas_atual - ratio_taxas_anterior
    delta_taxas_yoy = ratio_taxas_atual - ratio_taxas_yoy

    # Helper to format composite delta string for Main KPIs (Percentage)
    def format_delta_str(pct_pop, pct_yoy):
        pop_str = f"{pct_pop:+.1f}%".replace('.', ',')
        if pct_yoy is None:
            return f"{pop_str} (Mês)"
        yoy_str = f"{pct_yoy:+.1f}%".replace('.', ',')
        return f"{yoy_str} (Ano) | {pop_str} (Mês)"

    # Helper to format composite delta string for Efficiency KPIs (p.p.)
    def format_delta_pp_str(pp_pop, pp_yoy):
        pop_str = f"{pp_pop:+.1f}".replace('.', ',')
        yoy_str = f"{pp_yoy:+.1f}".replace('.', ',')
        return f"{yoy_str} p.p. (Ano) | {pop_str} p.p. (Mês)"

    # Build Main KPIs array
    metrics = [
        {
            "title": "Receita Bruta",
            "value": format_currency(receita_bruta_atual),
            "delta": format_delta_str(pct_receita_pop, pct_receita_yoy),
            "delta_color": "normal",
            "help_text": "Total de receitas no período selecionado"
        },
        {
            "title": "Custo de Comissão",
            "value": format_currency(abs(comissao_atual)),
            "delta": format_delta_str(pct_comissao_pop, pct_comissao_yoy),
            "delta_color": "inverse",
            "help_text": "Total de comissões pagas aos profissionais"
        },
        {
            "title": "Despesas",
            "value": format_currency(abs(despesas_atual)),
            "delta": format_delta_str(pct_despesas_pop, pct_despesas_yoy),
            "delta_color": "inverse",
            "help_text": "Despesas operacionais e financeiras"
        },
        {
            "title": "Lucro Líquido",
            "value": format_currency(lucro_liquido_atual),
            "delta": format_delta_str(pct_lucro_pop, pct_lucro_yoy),
            "delta_color": "normal",
            "help_text": "Resultado líquido após todos os custos e despesas"
        }
    ]
    
    render_kpi_grid(metrics)

    st.markdown("#### Eficiência Operacional")
    
    # Efficiency KPIs Row
    cols_eff = st.columns(3)
    
    with cols_eff[0]:
        st.metric(
            label="Margem Líquida",
            value=f"{ratio_margem_atual:.1f}%".replace('.', ','),
            delta=format_delta_pp_str(delta_margem_pop, delta_margem_yoy),
            delta_color="normal",
            help="Quanto sobra de lucro para cada R$ 100 vendidos. \n\nCálculo: (Lucro Líquido / Receita Bruta) * 100"
        )
        
    with cols_eff[1]:
        st.metric(
            label="Custo Comissão (%)",
            value=f"{ratio_comissao_atual:.1f}%".replace('.', ','),
            delta=format_delta_pp_str(delta_comissao_pop, delta_comissao_yoy),
            delta_color="inverse",
            help="Impacto das comissões sobre o faturamento total. \n\nCálculo: (Total Comissões / Receita Bruta) * 100"
        )
        
    with cols_eff[2]:
        st.metric(
            label="Impacto Taxas (%)",
            value=f"{ratio_taxas_atual:.1f}%".replace('.', ','),
            delta=format_delta_pp_str(delta_taxas_pop, delta_taxas_yoy),
            delta_color="inverse",
            help="Peso das taxas de cartão sobre o faturamento. \n\nCálculo: (Total Taxas / Receita Bruta) * 100"
        )
    
    st.markdown("---")
    
    # Charts Section (Layout: 2/3 Evolution, 1/3 Top Expenses)
    col_charts = st.columns([2, 1])
    
    with col_charts[0]:
        st.markdown("### Evolução Financeira")
        if not df_current.empty:
            render_financial_evolution(df_current, start_date, end_date)
        else:
            st.info("Sem dados no período.")
            
    with col_charts[1]:
        st.markdown("### Top Despesas")
        if not df_current.empty:
            render_top_expenses(df_current)
        else:
            st.info("Sem dados no período.")

    # Analytical Table Section
    st.markdown("")
    with st.expander("Detalhamento de Lançamentos", expanded=False):
        if not df_current.empty:
            # Data Quality & Formatting
            
            # Sort by Date (Descending)
            df_current = df_current.sort_values(by="data", ascending=False)
            
            # Fill NaNs in text columns and force string conversion for title case
            if 'categoria' in df_current.columns:
                df_current['categoria'] = df_current['categoria'].astype(str).str.title()
            if 'descricao' in df_current.columns:
                df_current['descricao'] = df_current['descricao'].astype(str).str.title()
            if 'grupo_metrica' in df_current.columns:
                df_current['grupo_metrica'] = df_current['grupo_metrica'].fillna("-")

            # Create formatted value column for display
            if 'valor' in df_current.columns:
                df_current['valor_formatado'] = df_current['valor'].apply(lambda x: format_currency(x))

            # Select and rename columns for display
            # We use a copy to avoid SettingWithCopy warnings on slice
            display_cols = ['data', 'grupo_metrica', 'categoria', 'descricao', 'valor_formatado']
            
            # Filter only existing columns
            display_cols = [c for c in display_cols if c in df_current.columns]
            
            df_display = df_current[display_cols].copy()

            st.dataframe(
                df_display,
                width="stretch",
                column_config={
                    "data": st.column_config.DateColumn(
                        "Data",
                        format="DD/MM/YYYY"
                    ),
                    "valor_formatado": st.column_config.TextColumn(
                        "Valor (R$)"
                    ),
                    "grupo_metrica": st.column_config.TextColumn("Grupo"),
                    "categoria": st.column_config.TextColumn("Categoria"),
                    "descricao": st.column_config.TextColumn(
                        "Descrição",
                        width="large"
                    )
                },
                hide_index=True
            )
        else:
            st.info("Nenhum lançamento encontrado para os filtros selecionados.")
