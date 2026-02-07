"""
Database utility module for Studio21 Dashboard.
Provides cached MotherDuck connection and query execution using DuckDB.
"""

import streamlit as st
import pandas as pd
import duckdb
from typing import Optional


@st.cache_resource
def get_motherduck_connection():
    """
    Get a singleton MotherDuck connection using DuckDB.
    Connection is cached across reruns for performance.
    
    Returns:
        DuckDB connection object configured for MotherDuck
    """
    try:
        # Get MotherDuck token from secrets
        if "connections" in st.secrets and "motherduck" in st.secrets.connections:
            # Extract token from URL format: "md:?motherduck_token=XXX"
            url = st.secrets.connections.motherduck.get("url", "")
            if "motherduck_token=" in url:
                token = url.split("motherduck_token=")[1]
            else:
                # Fallback: try direct token field
                token = st.secrets.connections.motherduck.get("token", "")
        else:
            st.error("MotherDuck token não encontrado em secrets.toml")
            st.stop()
        
        if not token:
            st.error("MotherDuck token está vazio")
            st.stop()
        
        # Connect to MotherDuck
        conn = duckdb.connect(f"md:?motherduck_token={token}")
        return conn
        
    except Exception as e:
        st.error(f"Erro ao conectar com MotherDuck: {e}")
        st.stop()


@st.cache_data(ttl=600)  # Cache for 10 minutes
def query_data(sql: str) -> pd.DataFrame:
    """
    Execute a SQL query against MotherDuck with caching.
    Results are cached for 10 minutes to reduce database load.
    
    Args:
        sql: SQL query string to execute
        
    Returns:
        pandas DataFrame with query results
        
    Raises:
        Exception: If query execution fails
    """
    try:
        conn = get_motherduck_connection()
        df = conn.execute(sql).fetchdf()
        return df
    except Exception as e:
        st.error(f"Erro ao executar query: {e}")
        st.error(f"SQL: {sql}")
        return pd.DataFrame()  # Return empty DataFrame on error


def clear_query_cache():
    """
    Clear the query data cache.
    Useful for forcing data refresh.
    """
    query_data.clear()
    st.success("Cache de queries limpo com sucesso!")
