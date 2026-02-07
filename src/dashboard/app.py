import streamlit as st
import duckdb
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.append(str(PROJECT_ROOT))

# Load Env
load_dotenv(PROJECT_ROOT / "config" / ".env")

# Page Config
st.set_page_config(
    page_title="Dashboard Studio 21",
    page_icon="💄",
    layout="wide"
)

# Load CSS
css_path = PROJECT_ROOT / "assets" / "style.css"
if css_path.exists():
    with open(css_path, "r") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Helper: Connect to Motherduck
@st.cache_resource
def get_connection():
    token = os.getenv("MOTHERDUCK_TOKEN")
    if not token:
        st.error("MOTHERDUCK_TOKEN not found in .env")
        return None
    try:
        con = duckdb.connect(f'md:?motherduck_token={token}')
        return con
    except Exception as e:
        st.error(f"Failed to connect to Motherduck: {e}")
        return None

# Sidebar
st.sidebar.title("Studio 21")

# Try to find logo
logo_path = list(PROJECT_ROOT.glob("assets/Logo Studio21*"))
if logo_path:
    st.sidebar.image(str(logo_path[0]), use_container_width=True)

page = st.sidebar.radio("Navegação", ["Visão Geral", "Financeiro", "Clientes"])

# Views
if page == "Visão Geral":
    st.title("Visão Geral")
    st.write("Bem-vindo ao Dashboard Studio 21.")
    
    con = get_connection()
    if con:
        try:
            # List tables check
            tables = con.execute("SHOW TABLES").df()
            st.write("Tabelas Disponíveis no Motherduck:")
            st.dataframe(tables)
        except Exception as e:
            st.warning(f"Não foi possível listar as tabelas: {e}")

elif page == "Financeiro":
    from src.dashboard.views import financeiro
    financeiro.render(get_connection)

elif page == "Clientes":
    st.info("Módulo de Clientes em desenvolvimento.")
