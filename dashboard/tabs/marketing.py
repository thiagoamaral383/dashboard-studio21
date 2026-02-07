"""
Marketing Tab - Marketing and Customer Retention KPIs
"""

import streamlit as st


def render():
    """Render the Marketing tab content."""
    st.markdown("### Marketing & Retenção")
    st.info("🚧 Em desenvolvimento - Indicadores de aquisição e retenção de clientes")
    
    # Placeholder cards
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Novos Clientes",
            "—",
            help="Clientes que fizeram a primeira compra"
        )
    
    with col2:
        st.metric(
            "Taxa de Recorrência",
            "—",
            help="Percentual de clientes recorrentes"
        )
    
    with col3:
        st.metric(
            "Ticket Médio",
            "—",
            help="Valor médio por venda"
        )
