"""
Studio21 Business Intelligence Dashboard
Main application entry point.
"""

import streamlit as st
from datetime import datetime, timedelta, date
from pathlib import Path

# Import utilities and components
from utils.database import query_data, clear_query_cache
from utils.formatters import calculate_previous_period, calculate_same_period_last_year
from components.kpi_cards import render_kpi_card, render_kpi_grid, render_section_header

# Import tab modules
from tabs import financeiro, performance, marketing


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
    if "date_start_picker" not in st.session_state:
        # Default: Last 30 days
        st.session_state.date_start_picker = date.today() - timedelta(days=30)
    
    if "date_end_picker" not in st.session_state:
        st.session_state.date_end_picker = date.today()


initialize_session_state()


# ============================================================================
# SIDEBAR
# ============================================================================
with st.sidebar:
    # Logo
    logo_path = Path(__file__).parent.parent / "assets" / "Logo Studio21 Rosé sem fundo.png"
    
    if logo_path.exists():
        st.image(str(logo_path), width=300)
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
            key="date_start_picker",
            format="DD/MM/YYYY"
        )
    
    with col2:
        end_date = st.date_input(
            "Data Final",
            key="date_end_picker",
            format="DD/MM/YYYY"
        )
    
    # Update session state
    st.session_state.start_date = start_date
    st.session_state.end_date = end_date
    
    # Callback to update date range
    def update_date_range(days=None, start=None):
        """Update date range pickers in session state."""
        if start:
            st.session_state.date_start_picker = start
        elif days:
            st.session_state.date_start_picker = date.today() - timedelta(days=days)
            
        st.session_state.date_end_picker = date.today()
    
    # First row: 30 dias and 3 meses
    col_btn1, col_btn2 = st.columns(2)
    
    with col_btn1:
        st.button(
            "30 dias", 
            width='stretch',
            on_click=update_date_range,
            kwargs={"days": 30}
        )
    
    with col_btn2:
        st.button(
            "3 meses", 
            width='stretch',
            on_click=update_date_range,
            kwargs={"days": 90}
        )
    
    # Second row: 6 meses and 1 ano
    col_btn3, col_btn4 = st.columns(2)
    
    with col_btn3:
        st.button(
            "6 meses", 
            width='stretch',
            on_click=update_date_range,
            kwargs={"days": 180}
        )
    
    with col_btn4:
        st.button(
            "1 ano", 
            width='stretch',
            on_click=update_date_range,
            kwargs={"days": 365}
        )
    
    # Third row: Desde o início and Nova Gestão
    col_btn5, col_btn6 = st.columns(2)
    
    with col_btn5:
        st.button(
            "Desde o início", 
            width='stretch',
            on_click=update_date_range,
            kwargs={"start": date(2023, 8, 1)}
        )
        
    with col_btn6:
        st.button(
            "Nova Gestão", 
            width='stretch',
            on_click=update_date_range,
            kwargs={"start": date(2025, 8, 17)}
        )
    
    # Filter summary
    st.markdown("---")
    st.caption(f"**Período Selecionado:**")
    st.caption(f"{start_date.strftime('%d/%m/%Y')} até {end_date.strftime('%d/%m/%Y')}")
    
    days_diff = (end_date - start_date).days + 1
    st.caption(f"**Total:** {days_diff} dias")
    
    # Calculate comparison periods for display
    prev_start, prev_end = calculate_previous_period(start_date, end_date)
    yoy_start, yoy_end = calculate_same_period_last_year(start_date, end_date)

    st.caption("**Período Anterior (Mês):**")
    st.caption(f"{prev_start.strftime('%d/%m/%Y')} até {prev_end.strftime('%d/%m/%Y')}")
    
    st.caption("**Mesmo Período Ano Anterior (Ano):**")
    st.caption(f"{yoy_start.strftime('%d/%m/%Y')} até {yoy_end.strftime('%d/%m/%Y')}")
    
    # Cache control
    st.markdown("---")
    if st.button("Atualizar Dados", width='stretch'):
        clear_query_cache()
        st.rerun()


# ============================================================================
# MAIN CONTENT
# ============================================================================
# Main title
st.title("Dashboard Studio21")
st.caption("Análise integrada de indicadores de performance")

# Warning for old management period
if start_date < date(2025, 8, 17):
    st.warning(
        """
        **Atenção: Período Misto/Gestão Anterior (Antes de 17/08/2025)**
            
        Você está visualizando dados históricos. Considere as seguintes ressalvas:
        * **Receita e Comissões:** Dados confiáveis (baseados no histórico de vendas importado).
        * **Despesas e Lucro:** Estão **subestimados**. Os custos fixos da gestão anterior (Aluguel, Luz, etc.) não foram lançados no sistema.
        * **Impacto Estimado:** Considere um custo adicional de aprox. **R$ 6.000,00/mês** para o período anterior a Ago/25.
            
        *Consequência: Lucro Líquido e Margem Líquida estão incorretos.*
        """,
        icon="⚠️"
    )


# Create tabs
tab1, tab2, tab3 = st.tabs(["Financeiro", "Performance", "Marketing"])


# ============================================================================
# TAB: FINANCEIRO
# ============================================================================
with tab1:
    financeiro.render()


# ============================================================================
# TAB: PERFORMANCE
# ============================================================================
with tab2:
    performance.render()

# ============================================================================
# TAB: MARKETING
# ============================================================================
with tab3:
    marketing.render()


# ============================================================================
# FOOTER
# ============================================================================
st.markdown("---")
st.caption("Dashboard Studio21 | Developed by Thiago Amaral")
