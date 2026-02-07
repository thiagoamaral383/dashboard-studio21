"""
Verificação das Views de Competência (Studio21)
Script para testar a criação e estrutura das views vw_fato_vendas e vw_competencia
"""

import duckdb
import os
from dotenv import load_dotenv
from pathlib import Path

# Carrega variáveis de ambiente do diretório config
script_dir = Path(__file__).parent
project_root = script_dir.parent
env_path = project_root / "config" / ".env"

load_dotenv(env_path)
motherduck_token = os.getenv('MOTHERDUCK_TOKEN')

if not motherduck_token:
    raise ValueError(f"MOTHERDUCK_TOKEN não encontrado em {env_path}")

# Conecta ao Motherduck
conn = duckdb.connect(f'md:?motherduck_token={motherduck_token}')

print("=" * 80)
print("TESTE 1: Verificar Criação das Views")
print("=" * 80)

query1 = """
SELECT table_name 
FROM information_schema.tables 
WHERE table_name IN ('vw_fato_vendas', 'vw_competencia')
ORDER BY table_name;
"""

result1 = conn.execute(query1).fetchall()
print(f"Views encontradas: {len(result1)}")
for row in result1:
    print(f"  ✓ {row[0]}")

print("\n" + "=" * 80)
print("TESTE 2: Estrutura vw_fato_vendas (5 primeiras linhas)")
print("=" * 80)

query2 = """
SELECT * FROM vw_fato_vendas LIMIT 5;
"""

result2 = conn.execute(query2).fetchdf()
print(result2.to_string())

print("\n" + "=" * 80)
print("TESTE 3: Validar Recorrência")
print("=" * 80)

query3 = """
SELECT 
    id_cliente,
    COUNT(*) as total_vendas,
    SUM(CASE WHEN is_recorrente THEN 1 ELSE 0 END) as vendas_recorrentes
FROM vw_fato_vendas
GROUP BY id_cliente
ORDER BY total_vendas DESC
LIMIT 10;
"""

result3 = conn.execute(query3).fetchdf()
print(result3.to_string())

print("\n" + "=" * 80)
print("TESTE 4: Estrutura vw_competencia (10 primeiras linhas)")
print("=" * 80)

query4 = """
SELECT * FROM vw_competencia LIMIT 10;
"""

result4 = conn.execute(query4).fetchdf()
print(result4.to_string())

print("\n" + "=" * 80)
print("TESTE 5: Validar Convenção de Sinais (por Grupo)")
print("=" * 80)

query5 = """
SELECT 
    grupo_metrica,
    COUNT(*) as registros,
    ROUND(MIN(valor), 2) as valor_min,
    ROUND(MAX(valor), 2) as valor_max,
    ROUND(SUM(valor), 2) as total
FROM vw_competencia
GROUP BY grupo_metrica
ORDER BY grupo_metrica;
"""

result5 = conn.execute(query5).fetchdf()
print(result5.to_string())

print("\n" + "=" * 80)
print("TESTE 6: Contagem de Registros por Grupo")
print("=" * 80)

query6 = """
SELECT 
    grupo_metrica,
    COUNT(*) as total_registros
FROM vw_competencia
GROUP BY grupo_metrica
ORDER BY grupo_metrica;
"""

result6 = conn.execute(query6).fetchdf()
print(result6.to_string())

conn.close()

print("\n" + "=" * 80)
print("TESTES CONCLUÍDOS COM SUCESSO!")
print("=" * 80)
