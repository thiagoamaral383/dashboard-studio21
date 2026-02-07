"""
Studio21 Business Intelligence Dashboard
Main application entry point.
"""

import streamlit as st
from datetime import datetime, timedelta
from pathlib import Path

# Import utilities and components
from utils.database import query_data, clear_query_cache
from components.kpi_cards import render_kpi_card, render_kpi_grid, render_section_header

# Import tab modules
from tabs import financeiro, rh, marketing


# ============================================================================
# PAGE CONFIGURATION
# ============================================================================
st.set_page_config(
    page_title="Studio21 | Business Intelligence",
    layout="wide",
    initial_sidebar_state="expanded"
)





# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================
def initialize_session_state():
    """Initialize session state variables."""
    if "start_date" not in st.session_state:
        # Default: Last 30 days
        st.session_state.start_date = datetime.now().date() - timedelta(days=30)
    
    if "end_date" not in st.session_state:
        st.session_state.end_date = datetime.now().date()


initialize_session_state()


# ============================================================================
# SIDEBAR
# ============================================================================
with st.sidebar:
    # Logo
    logo_path = Path(__file__).parent.parent / "assets" / "Logo Studio21 Rosé sem fundo.png"
    
    if logo_path.exists():
        st.image(str(logo_path), width=200)
    else:
        st.title("Studio21")
    
    st.markdown("---")
    
    # Date Filter Section
    st.subheader("Filtros")
    
    # Date range picker
    col1, col2 = st.columns(2)
    
    with col1:
        start_date = st.date_input(
            "Data Inicial",
            value=st.session_state.start_date,
            key="date_start_picker"
        )
    
    with col2:
        end_date = st.date_input(
            "Data Final",
            value=st.session_state.end_date,
            key="date_end_picker"
        )
    
    # Update session state
    st.session_state.start_date = start_date
    st.session_state.end_date = end_date
    
    # Quick shortcuts
    st.caption("Atalhos Rápidos:")
    
    col_btn1, col_btn2, col_btn3 = st.columns(3)
    
    with col_btn1:
        if st.button("30 dias", use_container_width=True):
            st.session_state.start_date = datetime.now().date() - timedelta(days=30)
            st.session_state.end_date = datetime.now().date()
            st.rerun()
    
    with col_btn2:
        if st.button("3 meses", use_container_width=True):
            st.session_state.start_date = datetime.now().date() - timedelta(days=90)
            st.session_state.end_date = datetime.now().date()
            st.rerun()
    
    with col_btn3:
        if st.button("1 ano", use_container_width=True):
            st.session_state.start_date = datetime.now().date() - timedelta(days=365)
            st.session_state.end_date = datetime.now().date()
            st.rerun()
    
    # Filter summary
    st.markdown("---")
    st.caption(f"**Período Selecionado:**")
    st.caption(f"{start_date.strftime('%d/%m/%Y')} até {end_date.strftime('%d/%m/%Y')}")
    
    days_diff = (end_date - start_date).days + 1
    st.caption(f"**Total:** {days_diff} dias")
    
    # Cache control
    st.markdown("---")
    if st.button("Atualizar Dados", use_container_width=True):
        clear_query_cache()
        st.rerun()


# ============================================================================
# MAIN CONTENT
# ============================================================================
# Main title
st.title("Dashboard Studio21")
st.caption("Análise integrada de indicadores de performance")

# Create tabs
tab1, tab2, tab3 = st.tabs(["Financeiro", "RH", "Marketing"])

# ============================================================================
# TAB: FINANCEIRO
# ============================================================================
with tab1:
    financeiro.render()


# ============================================================================
# TAB: RH
# ============================================================================
with tab2:
    rh.render()


# ============================================================================
# TAB: MARKETING
# ============================================================================
with tab3:
    marketing.render()


# ============================================================================
# FOOTER
# ============================================================================
st.markdown("---")
st.caption("Studio21 Business Intelligence | Developed by Thiago Amaral")
