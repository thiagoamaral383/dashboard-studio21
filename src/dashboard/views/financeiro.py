import streamlit as st
import pandas as pd

def render(get_connection):
    st.header("Módulo Financeiro")
    st.markdown("---")
    
    con = get_connection()
    if not con:
        st.warning("Conexão com Motherduck não estabelecida.")
        return

    st.write("### Dados Financeiros (Exemplo)")
    
    # Try to query a table if it exists, else show message
    try:
        # This is a placeholder query. In real usage, we would query specific tables.
        # For now, let's just list tables again or try a common name.
        tables = con.execute("SHOW TABLES").df()
        if not tables.empty:
            table_name = tables.iloc[0, 0] # simplified access
            st.write(f"Visualizando dados de: {table_name}")
            df = con.query(f"SELECT * FROM {table_name} LIMIT 5").df()
            st.dataframe(df)
        else:
            st.info("Nenhuma tabela encontrada no Motherduck.")
            
    except Exception as e:
        st.error(f"Erro ao consultar dados: {e}")
