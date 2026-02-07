"""
Financeiro Tab - Financial KPIs and Analysis
"""

import streamlit as st
from utils.formatters import format_currency, calculate_previous_period
from utils.database import query_data
from components.kpi_cards import render_kpi_grid


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
    
    # Calculate previous period
    prev_start, prev_end = calculate_previous_period(start_date, end_date)
    
    # Query current period data
    current_query = f"""
        SELECT 
            grupo_metrica,
            SUM(valor) as valor
        FROM vw_competencia
        WHERE data BETWEEN '{start_date}' AND '{end_date}'
        GROUP BY grupo_metrica
    """
    
    # Query previous period data
    previous_query = f"""
        SELECT 
            grupo_metrica,
            SUM(valor) as valor
        FROM vw_competencia
        WHERE data BETWEEN '{prev_start}' AND '{prev_end}'
        GROUP BY grupo_metrica
    """
    
    # Execute queries
    df_current = query_data(current_query)
    df_previous = query_data(previous_query)
    
    # Calculate metrics for current period
    receita_bruta_atual = calculate_metric(df_current, 'Receita Bruta')
    comissao_atual = calculate_metric(df_current, 'Comissões')
    despesas_atual = calculate_metric(df_current, ['Despesas Operacionais', 'Despesas Financeiras', 'Resultado Financeiro'])
    lucro_liquido_atual = df_current['valor'].sum() if not df_current.empty else 0.0
    
    # Calculate metrics for previous period
    receita_bruta_anterior = calculate_metric(df_previous, 'Receita Bruta')
    comissao_anterior = calculate_metric(df_previous, 'Comissões')
    despesas_anterior = calculate_metric(df_previous, ['Despesas Operacionais', 'Despesas Financeiras', 'Resultado Financeiro'])
    lucro_liquido_anterior = df_previous['valor'].sum() if not df_previous.empty else 0.0
    
    # Calculate deltas (absolute difference)
    delta_receita = receita_bruta_atual - receita_bruta_anterior
    delta_comissao = comissao_atual - comissao_anterior
    delta_despesas = despesas_atual - despesas_anterior
    delta_lucro = lucro_liquido_atual - lucro_liquido_anterior
    
    # Calculate percentage deltas for display
    pct_receita = (delta_receita / receita_bruta_anterior * 100) if receita_bruta_anterior != 0 else 0
    pct_comissao = (delta_comissao / abs(comissao_anterior) * 100) if comissao_anterior != 0 else 0
    pct_despesas = (delta_despesas / abs(despesas_anterior) * 100) if despesas_anterior != 0 else 0
    pct_lucro = (delta_lucro / lucro_liquido_anterior * 100) if lucro_liquido_anterior != 0 else 0
    
    # Format delta strings with percentage
    delta_receita_str = f"{'+' if delta_receita > 0 else ''}{pct_receita:.1f}%".replace('.', ',')
    delta_comissao_str = f"{'+' if delta_comissao > 0 else ''}{pct_comissao:.1f}%".replace('.', ',')
    delta_despesas_str = f"{'+' if delta_despesas > 0 else ''}{pct_despesas:.1f}%".replace('.', ',')
    delta_lucro_str = f"{'+' if delta_lucro > 0 else ''}{pct_lucro:.1f}%".replace('.', ',')
    
    # Build metrics array
    metrics = [
        {
            "title": "Receita Bruta",
            "value": format_currency(receita_bruta_atual),
            "delta": delta_receita_str if receita_bruta_anterior != 0 else "N/A",
            "delta_color": "normal",  # Higher revenue is good
            "help_text": "Total de receitas no período selecionado"
        },
        {
            "title": "Custo de Comissão",
            "value": format_currency(abs(comissao_atual)),  # Show as positive for display
            "delta": delta_comissao_str if comissao_anterior != 0 else "N/A",
            "delta_color": "inverse",  # Higher cost is bad
            "help_text": "Total de comissões pagas aos profissionais"
        },
        {
            "title": "Despesas",
            "value": format_currency(abs(despesas_atual)),  # Show as positive for display
            "delta": delta_despesas_str if despesas_anterior != 0 else "N/A",
            "delta_color": "inverse",  # Higher expenses is bad
            "help_text": "Despesas operacionais e financeiras"
        },
        {
            "title": "Lucro Líquido",
            "value": format_currency(lucro_liquido_atual),
            "delta": delta_lucro_str if lucro_liquido_anterior != 0 else "N/A",
            "delta_color": "normal",  # Higher profit is good
            "help_text": "Resultado líquido após todos os custos e despesas"
        }
    ]
    
    render_kpi_grid(metrics)
    
    st.markdown("---")
    
    # Debug info (optional - can be removed in production)
    with st.expander("🔍 Informações de Período"):
        col1, col2 = st.columns(2)
        with col1:
            st.caption("**Período Atual:**")
            st.caption(f"{start_date.strftime('%d/%m/%Y')} até {end_date.strftime('%d/%m/%Y')}")
            st.caption(f"{(end_date - start_date).days + 1} dias")
        with col2:
            st.caption("**Período Anterior:**")
            st.caption(f"{prev_start.strftime('%d/%m/%Y')} até {prev_end.strftime('%d/%m/%Y')}")
            st.caption(f"{(prev_end - prev_start).days + 1} dias")
    
    # Placeholder for future charts
    st.info("📊 Gráficos e análises detalhadas serão implementados na próxima fase")

