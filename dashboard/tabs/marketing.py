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
            "Risco de Churn",
            "—",
            help="Percentual de clientes que deixam o negócio"
        )
    
    with col3:
        st.metric(
            "Ranking de Clientes",
            "—",
            help="Clientes com maior fidelidade"
        )
