"""
Database utility module for Studio21 Dashboard.
Provides cached MotherDuck connection and query execution.
"""

import streamlit as st
import pandas as pd
from typing import Optional


@st.cache_resource
def get_motherduck_connection():
    """
    Get a singleton MotherDuck connection.
    Connection is cached across reruns for performance.
    
    Returns:
        MotherDuck connection object
    """
    try:
        conn = st.connection("motherduck", type="sql")
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
        df = conn.query(sql)
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
