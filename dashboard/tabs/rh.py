"""
RH Tab - Human Resources KPIs and Analysis
"""

import streamlit as st


def render():
    """Render the RH (Human Resources) tab content."""
    st.markdown("### Recursos Humanos")
    st.info("🚧 Em desenvolvimento - Indicadores de ocupação e performance de profissionais")
    
    # Placeholder cards
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Taxa de Ocupação",
            "—",
            help="Média de ocupação dos profissionais"
        )
    
    with col2:
        st.metric(
            "Horas Agendadas",
            "—",
            help="Total de horas agendadas no período"
        )
    
    with col3:
        st.metric(
            "Profissionais Ativos",
            "—",
            help="Número de profissionais ativos"
        )
