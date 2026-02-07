import duckdb
import pandas as pd
import os
from dotenv import load_dotenv
from pathlib import Path

def load_categorias_to_motherduck():
    """
    Loads the categories seed CSV into Motherduck as a physical table.
    This replaces the broken vw_dim_categorias view that referenced a local file.
    """
    # Locate .env in config directory
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    env_path = project_root / "config" / ".env"
    
    load_dotenv(env_path)
    token = os.getenv("MOTHERDUCK_TOKEN")
    
    if not token:
        raise ValueError(f"MOTHERDUCK_TOKEN not found in {env_path}")

    # Read the CSV file
    csv_path = script_dir / "seeds" / "categorias.csv"
    print(f"📂 Lendo arquivo: {csv_path}")
    df = pd.read_csv(csv_path)
    
    print(f"✓ {len(df)} categorias carregadas do CSV")
    print(f"  Colunas: {df.columns.tolist()}")
    
    # Connect to Motherduck
    con = duckdb.connect(f'md:?motherduck_token={token}')
    
    try:
        # Drop the old view if it exists
        print("\n🗑️  Removendo view antiga (se existir)...")
        con.execute("DROP VIEW IF EXISTS vw_dim_categorias")
        print("✓ View removida")
        
        # Create physical table from DataFrame
        print("\n📊 Criando tabela física tbl_dim_categorias...")
        con.execute("""
            CREATE OR REPLACE TABLE tbl_dim_categorias AS 
            SELECT 
                Categoria,
                "Nivel 1" AS nivel_1,
                "Nivel 2" AS nivel_2,
                ExcluirDRE AS excluir_dre
            FROM df
        """)
        print("✓ Tabela tbl_dim_categorias criada com sucesso")
        
        # Verify the data
        result = con.execute("SELECT COUNT(*) FROM tbl_dim_categorias").fetchone()
        print(f"✓ Verificação: {result[0]} registros na tabela")
        
        # Show sample data
        print("\n📋 Amostra dos dados:")
        sample = con.execute("""
            SELECT categoria, nivel_1, nivel_2, excluir_dre 
            FROM tbl_dim_categorias 
            LIMIT 3
        """).fetchdf()
        print(sample.to_string(index=False))
        
    except Exception as e:
        print(f"❌ Erro ao criar tabela: {e}")
        raise
    finally:
        con.close()

if __name__ == "__main__":
    load_categorias_to_motherduck()
