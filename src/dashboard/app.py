import streamlit as st
import duckdb
import pandas as pd
import plotly.express as px
import os
from pathlib import Path
from dotenv import load_dotenv

# Layout Config - Must be first
st.set_page_config(
    page_title="Studio21 Financeiro",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for "Rich Aesthetics"
st.markdown("""
<style>
    /* Global Background */
    .stApp {
        background-color: #0E1117;
        color: #E0E0E0;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #1E1E1E;
        border-right: 1px solid #333;
    }
    
    /* Cards (Metrics) */
    .stMetric {
        background-color: #262730;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #333;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    
    /* Headers */
    h1, h2, h3 {
        font-family: 'Helvetica Neue', sans-serif;
        color: #FAFAFA;
        font-weight: 600;
    }
    
    /* Dataframe */
    [data-testid="stDataFrame"] {
        border: 1px solid #333;
        border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)

# Load Environment
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
ENV_PATH = PROJECT_ROOT / "config" / ".env"
load_dotenv(ENV_PATH)

@st.cache_data(ttl=600)
def load_data():
    token = os.getenv("MOTHERDUCK_TOKEN")
    if not token:
        return None
    
    try:
        con = duckdb.connect(f'md:?motherduck_token={token}')
        con.sql("USE studio21")
        
        # Check if table exists
        tables = con.sql("SHOW TABLES").df()
        if 'tbl_0387_financeiro' not in tables['name'].values:
            return pd.DataFrame() # Table not created yet
            
        df = con.sql("SELECT * FROM tbl_0387_financeiro ORDER BY Competência DESC").df()
        return df
    except Exception as e:
        st.error(f"Erro ao conectar ao Motherduck: {e}")
        return None

def main():
    st.title("📊 Studio21 - Dashboard Financeiro")
    st.markdown("---")

    df = load_data()

    if df is None:
        st.warning("Token do Motherduck não encontrado ou erro de conexão.")
        return

    if df.empty:
        st.info("Nenhum dado encontrado na tabela 'tbl_0387_financeiro'. Execute o pipeline ETL primeiro.")
        return

    # Sidebar Filter
    st.sidebar.header("Filtros")
    
    # Date Filter
    if 'Competência' in df.columns:
        min_date = df['Competência'].min()
        max_date = df['Competência'].max()
        
        start_date, end_date = st.sidebar.date_input(
            "Período (Competência)",
            [min_date, max_date]
        )
        
        # Filter Data
        mask = (df['Competência'].dt.date >= start_date) & (df['Competência'].dt.date <= end_date)
        df_filtered = df[mask]
    else:
        df_filtered = df

    # Category Filter
    if 'Categoria' in df.columns:
        categorias = ['Todas'] + sorted(df['Categoria'].dropna().unique().tolist())
        cat_selecionada = st.sidebar.selectbox("Categoria", categorias)
        
        if cat_selecionada != 'Todas':
            df_filtered = df_filtered[df_filtered['Categoria'] == cat_selecionada]

    # KPIs
    st.subheader("Resumo do Período")
    col1, col2, col3 = st.columns(3)
    
    total_registros = len(df_filtered)
    valor_total = df_filtered['Valor'].sum() if 'Valor' in df_filtered.columns else 0
    media_valor = df_filtered['Valor'].mean() if 'Valor' in df_filtered.columns else 0
    
    col1.metric("Total Movimentações", f"{total_registros}")
    col2.metric("Volume Total (R$)", f"R$ {valor_total:,.2f}")
    col3.metric("Ticket Médio", f"R$ {media_valor:,.2f}")

    # Charts
    st.markdown("### Visão Temporal")
    if 'Competência' in df_filtered.columns and 'Valor' in df_filtered.columns:
        df_daily = df_filtered.groupby('Competência')['Valor'].sum().reset_index()
        fig = px.bar(df_daily, x='Competência', y='Valor', title="Evolução Financeira", template="plotly_dark")
        fig.update_layout(xaxis_title="Data", yaxis_title="Valor (R$)")
        st.plotly_chart(fig, use_container_width=True)

    # Detailed Data
    st.markdown("### Detalhamento")
    st.dataframe(
        df_filtered,
        use_container_width=True,
        column_order=['Competência', 'Pagamento', 'Título', 'Categoria', 'Valor', 'Observações', 'Conta Bancária'],
        hide_index=True
    )

if __name__ == "__main__":
    main()
