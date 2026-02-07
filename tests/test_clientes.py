import pandas as pd
import sys
import os

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from etl.transformers import clientes

def test_clientes_transformer():
    print("Running Client Transformer Test...")

    # Mock Data matching the user's "reality"
    data = [
        # Case 1: Simple Valid
        {'Cliente': 'JOAO DA SILVA', 'Celular': '11999991111', 'E-mail': 'joao@email.com', 'Data de Nascimento': '1990-01-01', 'Sexo': 'M'},
        
        # Case 2: Dirty Name
        {'Cliente': 'maria s.', 'Celular': '11-8888-7777', 'E-mail': 'MARIA@EMAIL.COM'},
        
        # Case 3: Duplicates with Richness (Phone wins)
        # Entry A: No phone
        {'Cliente': 'Carlos Oliveira', 'E-mail': 'carlos@old.com'},
        # Entry B: Has phone (Should win due to richness)
        {'Cliente': 'CARLOS OLIVEIRA', 'Celular': '(11) 91234-5678', 'E-mail': 'carlos@new.com'},
        
        # Case 4: Duplicates with Tie (Recency wins)
        # Entry A (Old)
        {'Cliente': 'Ana Souza', 'Celular': '11900001111', 'E-mail': 'ana@old.com'},
        # Entry B (New - Should win due to index)
        {'Cliente': 'ANA SOUZA', 'Celular': '11900002222', 'E-mail': 'ana@new.com'},
        
        # Case 5: Garbage Phone
        {'Cliente': 'Pedro', 'Celular': 'abc', 'E-mail': 'pedro@email.com'}
    ]

    df_input = pd.DataFrame(data)
    
    # Process
    df_result = clientes.process_dim_clientes([df_input])
    
    print("\n--- Result DataFrame ---")
    print(df_result.to_string())
    
    # Assertions
    
    # 1. Check Case 2 (Maria)
    maria = df_result[df_result['cliente'] == 'MARIA S']
    assert not maria.empty, "Maria not found or name not standardized"
    assert maria.iloc[0]['email'] == 'maria@email.com', "Email not normalized"
    assert maria.iloc[0]['celular'] == '1188887777', "Phone not sanitized"

    # 2. Check Case 3 (Carlos - Richness)
    carlos = df_result[df_result['cliente'] == 'CARLOS OLIVEIRA']
    assert len(carlos) == 1, "Duplicate Carlos not removed"
    assert carlos.iloc[0]['celular'] == '11912345678', "Richness logic failed: Record with phone should satisfy"
    
    # 3. Check Case 4 (Ana - Recency)
    ana = df_result[df_result['cliente'] == 'ANA SOUZA']
    assert len(ana) == 1, "Duplicate Ana not removed"
    assert ana.iloc[0]['email'] == 'ana@new.com', "Recency logic failed: Last record should win on tie"

    # 4. Check Case 5 (Pedro - Garbage Phone)
    pedro = df_result[df_result['cliente'] == 'PEDRO']
    assert pedro.iloc[0]['celular'] is None, "Garbage phone should be None"

    print("\n\nALL TESTS PASSED!")

if __name__ == "__main__":
    test_clientes_transformer()
