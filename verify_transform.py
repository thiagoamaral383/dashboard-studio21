import pandas as pd
import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

from src.etl.transform import process_financial_data, _clean_currency

def test_clean_currency():
    print("Testing currency conversion...")
    assert _clean_currency("1.200,50") == 1200.50
    assert _clean_currency("100,00") == 100.0
    assert _clean_currency(100) == 100.0
    print("Currency conversion PASSED.")

def test_deduplication_and_id():
    print("Testing deduplication and ID generation...")
    # Mock Data
    data_comp = {
        'Título': ['Pagamento Aluguel', 'Compra Material'],
        'Competência': ['01/01/2023', '05/01/2023'],
        'Valor': ['1.000,00', '500,00'],
        'Pagamento': [None, None]
    }
    
    data_caixa = {
        'Título': ['Pagamento Aluguel', 'Serviço Extra'], # Aluguel duplicated
        'Competência': ['01/01/2023', '10/01/2023'],
        'Valor': ['1.000,00', '200,00'],
        'Pagamento': ['05/01/2023', '10/01/2023'] # Has payment date
    }

    df_comp = pd.DataFrame(data_comp)
    df_caixa = pd.DataFrame(data_caixa)

    df_final = process_financial_data(df_comp, df_caixa)

    print("Result Columns:", df_final.columns)
    print(df_final[['Título', 'Pagamento', 'id_transacao']])

    # Verification
    # 1. 'Pagamento Aluguel' should appear once
    aluguel = df_final[df_final['Título'] == 'Pagamento Aluguel']
    assert len(aluguel) == 1, "Deduplication failed: Aluguel should be 1 row"
    
    # 2. It should have the payment date (from Caixa)
    assert pd.notna(aluguel.iloc[0]['Pagamento']), "Merge preference failed: Should keep row with Payment date"
    
    # 3. ID should be present
    assert 'id_transacao' in df_final.columns
    
    print("Deduplication and ID generation PASSED.")

if __name__ == "__main__":
    test_clean_currency()
    test_deduplication_and_id()
