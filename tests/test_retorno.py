import unittest
import pandas as pd
import sys
import os

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.etl.transformers import retorno
from src.etl import transform

class TestRetornoTransformer(unittest.TestCase):
    
    def test_process_retorno_basic(self):
        """Test basic transformation logic for Report 0007"""
        df_input = pd.DataFrame({
            'Cliente': ['  Joao Silva  ', 'MARIA SOUZA', None],
            'E-mail': ['JOAO@TEST.COM', 'maria@test.com ', None],
            'Sexo': ['m', 'F', None],
            'Última Visita': ['01/01/2023', '02/01/2023', None]
        })
        
        result = retorno.process_retorno([df_input])
        
        # Check columns exist
        expected_cols = ['cliente', 'email', 'sexo', 'ultima_visita']
        for col in expected_cols:
            self.assertIn(col, result.columns)
            
        # Check cleaning
        self.assertEqual(result.iloc[0]['cliente'], 'Joao Silva') # Title case
        self.assertEqual(result.iloc[1]['cliente'], 'Maria Souza') # Title case
        
        self.assertEqual(result.iloc[0]['email'], 'joao@test.com') # Lower case
        self.assertEqual(result.iloc[1]['email'], 'maria@test.com')
        
        self.assertEqual(result.iloc[0]['sexo'], 'M') # Upper case
        self.assertEqual(result.iloc[1]['sexo'], 'F')
        
        # Check dates
        self.assertEqual(str(result.iloc[0]['ultima_visita']), '2023-01-01')
        self.assertEqual(str(result.iloc[1]['ultima_visita']), '2023-01-02')

    def test_factory_routing_0007(self):
        """Test if transform factory correctly routes report 0007"""
        df_input = pd.DataFrame({'Cliente': ['Test']})
        result = transform.transform_factory('0007', [df_input])
        self.assertIn('cliente', result.columns)
        self.assertEqual(result.iloc[0]['cliente'], 'Test')

if __name__ == '__main__':
    unittest.main()
