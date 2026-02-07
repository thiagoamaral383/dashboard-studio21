import sys
import unittest
import pandas as pd
import datetime
from unittest.mock import MagicMock

# Adjust path to include src
sys.path.append('c:/Projetos/Studio21/src')
sys.path.append('c:/Projetos/Studio21')
from src.etl.transformers import operacional

class TestOperacional(unittest.TestCase):
    
    def test_parse_time_to_decimal(self):
        """Test robust time parsing logic"""
        self.assertEqual(operacional.parse_time_to_decimal("01:30"), 1.5)
        self.assertEqual(operacional.parse_time_to_decimal("00:45"), 0.75)
        self.assertEqual(operacional.parse_time_to_decimal("1:30"), 1.5) # loose formatting
        self.assertEqual(operacional.parse_time_to_decimal(1.5), 1.5)
        self.assertEqual(operacional.parse_time_to_decimal(datetime.time(1, 30)), 1.5)
        self.assertEqual(operacional.parse_time_to_decimal(None), 0.0)
        self.assertEqual(operacional.parse_time_to_decimal("Invalid"), 0.0)
        
    def test_process_ocupacao_logic(self):
        """Test full transformation logic for 0126"""
        
        dt_ref = datetime.datetime(2023, 10, 1)
        
        df_input = pd.DataFrame({
            'Profissional': ['  Maria  ', 'JOAO', None],
            'Total Agendado': ['01:30', '02:00', '00:00'],
            'Outra Coluna': [1, 2, 3]
        })
        # Simulate Runtime Injection
        df_input['data_competencia'] = dt_ref
        
        data = [df_input]
        
        result = operacional.process_ocupacao(data)
        
        # Schema
        expected_cols = ['data_competencia', 'profissional', 'horas_agendadas_decimal']
        self.assertEqual(list(result.columns), expected_cols)
        
        # Values
        self.assertEqual(result.iloc[0]['profissional'], 'Maria')
        self.assertEqual(result.iloc[0]['horas_agendadas_decimal'], 1.5)
        
        self.assertEqual(result.iloc[1]['profissional'], 'Joao')
        self.assertEqual(result.iloc[1]['horas_agendadas_decimal'], 2.0)
        
        self.assertEqual(result.iloc[2]['profissional'], 'Desconhecido') # Handled None
        
    def test_missing_date_column(self):
        """Test failing gracefully (or returning empty) if data_competencia missing"""
        df_input = pd.DataFrame({'Profissional': ['Maria']})
        # No injection
        result = operacional.process_ocupacao([df_input])
        self.assertTrue(result.empty)

if __name__ == '__main__':
    unittest.main()
