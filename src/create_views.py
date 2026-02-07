import duckdb
import os
from dotenv import load_dotenv

from pathlib import Path

def create_views():
    # Locate .env in config directory
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    env_path = project_root / "config" / ".env"
    
    load_dotenv(env_path)
    token = os.getenv("MOTHERDUCK_TOKEN")
    
    if not token:
        raise ValueError(f"MOTHERDUCK_TOKEN not found in {env_path}")

    con = duckdb.connect(f'md:?motherduck_token={token}')
    
    try:
        with open('src/sql/views.sql', 'r', encoding='utf-8') as f:
            sql_script = f.read()
            
        con.execute(sql_script)
        print("✓ Todas as views criadas com sucesso:")
        print("  - vw_dim_profissionais")
        print("  - vw_dim_clientes")
        print("  - vw_dim_servicos")
        print("  - vw_dim_calendario")
        print("  - vw_dim_categorias")
        print("  - vw_fato_financeiro")
        print("  - vw_fato_taxas_cartao")
        print("  - vw_fato_ocupacao")
        
    except Exception as e:
        print(f"Erro ao criar view: {e}")
    finally:
        con.close()

if __name__ == "__main__":
    create_views()
