"""
Financeiro Tab - Financial KPIs and Analysis
"""

import streamlit as st
from utils.formatters import format_currency, calculate_previous_period, calculate_same_period_last_year
from utils.database import query_data
from components.kpi_cards import render_kpi_grid
from components.charts import render_financial_evolution


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
    
    # Query current period data
    current_query = f"""
        SELECT 
            grupo_metrica,
            SUM(valor) as valor
        FROM rep_financeiro_competencia
        WHERE data BETWEEN '{start_date}' AND '{end_date}'
        GROUP BY grupo_metrica
    """
    
    # Query previous period data
    previous_query = f"""
        SELECT 
            grupo_metrica,
            SUM(valor) as valor
        FROM rep_financeiro_competencia
        WHERE data BETWEEN '{prev_start}' AND '{prev_end}'
        GROUP BY grupo_metrica
    """
    
    # Query YoY data
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
    receita_bruta_atual = calculate_metric(df_current, 'Receita Bruta')
    comissao_atual = calculate_metric(df_current, 'Comissões')
    despesas_atual = calculate_metric(df_current, ['Despesas Operacionais', 'Despesas Financeiras', 'Resultado Financeiro'])
    lucro_liquido_atual = df_current['valor'].sum() if not df_current.empty else 0.0
    
    # Calculate metrics for previous period (PoP)
    receita_bruta_anterior = calculate_metric(df_previous, 'Receita Bruta')
    comissao_anterior = calculate_metric(df_previous, 'Comissões')
    despesas_anterior = calculate_metric(df_previous, ['Despesas Operacionais', 'Despesas Financeiras', 'Resultado Financeiro'])
    lucro_liquido_anterior = df_previous['valor'].sum() if not df_previous.empty else 0.0
    
    # Calculate metrics for YoY
    receita_bruta_yoy = calculate_metric(df_yoy, 'Receita Bruta')
    comissao_yoy = calculate_metric(df_yoy, 'Comissões')
    despesas_yoy = calculate_metric(df_yoy, ['Despesas Operacionais', 'Despesas Financeiras', 'Resultado Financeiro'])
    lucro_liquido_yoy = df_yoy['valor'].sum() if not df_yoy.empty else 0.0
    
    # Calculate PoP deltas (percentage)
    pct_receita_pop = ((receita_bruta_atual - receita_bruta_anterior) / receita_bruta_anterior * 100) if receita_bruta_anterior != 0 else 0
    pct_comissao_pop = ((comissao_atual - comissao_anterior) / abs(comissao_anterior) * 100) if comissao_anterior != 0 else 0
    pct_despesas_pop = ((despesas_atual - despesas_anterior) / abs(despesas_anterior) * 100) if despesas_anterior != 0 else 0
    pct_lucro_pop = ((lucro_liquido_atual - lucro_liquido_anterior) / abs(lucro_liquido_anterior) * 100) if lucro_liquido_anterior != 0 else 0
    
    # Calculate YoY deltas (percentage) - Handle division by zero/missing data
    pct_receita_yoy = ((receita_bruta_atual - receita_bruta_yoy) / receita_bruta_yoy * 100) if receita_bruta_yoy != 0 else None
    pct_comissao_yoy = ((comissao_atual - comissao_yoy) / abs(comissao_yoy) * 100) if comissao_yoy != 0 else None
    pct_despesas_yoy = ((despesas_atual - despesas_yoy) / abs(despesas_yoy) * 100) if despesas_yoy != 0 else None
    pct_lucro_yoy = ((lucro_liquido_atual - lucro_liquido_yoy) / abs(lucro_liquido_yoy) * 100) if lucro_liquido_yoy != 0 else None
    
    # Helper to format composite delta string
    def format_delta_str(pct_pop, pct_yoy):
        pop_str = f"{pct_pop:+.1f}%".replace('.', ',')
        if pct_yoy is None:
            return f"{pop_str} (Mês)"
        yoy_str = f"{pct_yoy:+.1f}%".replace('.', ',')
        return f"{yoy_str} (Ano) | {pop_str} (Mês)"
        
    # Helper to determine delta color (YoY drives color if available)
    def get_delta_color(pct_pop, pct_yoy, inverse=False):
        # Use YoY if available, otherwise PoP
        val = pct_yoy if pct_yoy is not None else pct_pop
        
        if val == 0:
            return "off"
            
        # Determine strict color based on direction
        is_positive = val > 0
        
        if inverse:
            # For costs: Positive (increase) is Bad (inverse), Negative (decrease) is Good (normal)
            return "inverse" if is_positive else "normal"
        else:
            # For revenue/profit: Positive (increase) is Good (normal), Negative (decrease) is Bad (inverse)
            return "normal" if is_positive else "inverse"

    # Build metrics array
    metrics = [
        {
            "title": "Receita Bruta",
            "value": format_currency(receita_bruta_atual),
            "delta": format_delta_str(pct_receita_pop, pct_receita_yoy),
            "delta_color": get_delta_color(pct_receita_pop, pct_receita_yoy, inverse=False),
            "help_text": "Total de receitas no período selecionado"
        },
        {
            "title": "Custo de Comissão",
            "value": format_currency(abs(comissao_atual)),
            "delta": format_delta_str(pct_comissao_pop, pct_comissao_yoy),
            "delta_color": get_delta_color(pct_comissao_pop, pct_comissao_yoy, inverse=True),
            "help_text": "Total de comissões pagas aos profissionais"
        },
        {
            "title": "Despesas",
            "value": format_currency(abs(despesas_atual)),
            "delta": format_delta_str(pct_despesas_pop, pct_despesas_yoy),
            "delta_color": get_delta_color(pct_despesas_pop, pct_despesas_yoy, inverse=True),
            "help_text": "Despesas operacionais e financeiras"
        },
        {
            "title": "Lucro Líquido",
            "value": format_currency(lucro_liquido_atual),
            "delta": format_delta_str(pct_lucro_pop, pct_lucro_yoy),
            "delta_color": get_delta_color(pct_lucro_pop, pct_lucro_yoy, inverse=False),
            "help_text": "Resultado líquido após todos os custos e despesas"
        }
    ]
    
    render_kpi_grid(metrics)
    
    st.markdown("---")
    
    # Financial Evolution Chart
    st.markdown("### Evolução Financeira")
    
    # Query granular data for the chart
    evolution_query = f"""
        SELECT 
            data,
            valor
        FROM rep_financeiro_competencia
        WHERE data BETWEEN '{start_date}' AND '{end_date}'
        ORDER BY data
    """
    
    df_evolution = query_data(evolution_query)
    render_financial_evolution(df_evolution, start_date, end_date)
    
    st.markdown("---")
    
    # Debug info (optional - can be removed in production)
    with st.expander("Informações de Período"):
        col1, col2 = st.columns(2)
        with col1:
            st.caption("**Período Atual:**")
            st.caption(f"{start_date.strftime('%d/%m/%Y')} até {end_date.strftime('%d/%m/%Y')}")
            st.caption(f"{(end_date - start_date).days + 1} dias")
        with col2:
            st.caption("**Período Anterior (PoP):**")
            st.caption(f"{prev_start.strftime('%d/%m/%Y')} até {prev_end.strftime('%d/%m/%Y')}")
            
        with st.expander("Detalhes YoY"):
            st.caption("**Mesmo Período Ano Anterior (YoY):**")
            st.caption(f"{yoy_start.strftime('%d/%m/%Y')} até {yoy_end.strftime('%d/%m/%Y')}")

