import sys
import unittest
import pandas as pd
from unittest.mock import MagicMock

# Adjust path to include src if needed
sys.path.append('c:/Projetos/Studio21/src')
sys.path.append('c:/Projetos/Studio21')
from src.etl import transform

class TestArchitecture(unittest.TestCase):
    
    def test_factory_routing_financeiro(self):
        """Test if factory routes 0387 to financeiro processor"""
        data = ([], []) # Empty lists
        result = transform.transform_factory('0387', data)
        self.assertIsInstance(result, pd.DataFrame)
        
    def test_factory_routing_clientes_logic(self):
        """Test if factory routes 0002 to clientes processor AND logic correctness"""
        
        # Create dummy data for 0002
        df_input = pd.DataFrame({
            'Cliente': ['  Ana Silva  ', 'PEDRO SOUZA', None],
            'Celular': ['11999999999', None, '11888888888'],
            'E-mail': ['ana@test.com', 'pedro@test.com', None]
        })
        
        data = [df_input]
        
        # Call Factory
        result = transform.transform_factory('0002', data)
        
        # Assertions
        # Check Columns
        expected_cols = ['id_cliente', 'cliente', 'celular', 'email']
        for col in expected_cols:
            self.assertIn(col, result.columns)
            
        # Check cleaning
        val_ana = result[result['cliente'] == 'Ana Silva']
        self.assertFalse(val_ana.empty)
        
        val_pedro = result[result['cliente'] == 'Pedro Souza']
        self.assertFalse(val_pedro.empty)
        
        # Check UNKNOWN row
        unknown = result[result['id_cliente'] == 'UNKNOWN']
        self.assertEqual(len(unknown), 1)
        self.assertEqual(unknown.iloc[0]['cliente'], 'Não Identificado')
        self.assertEqual(unknown.iloc[0]['email'], 'Não Informado')
        
    def test_factory_routing_generico(self):
        """Test if factory routes unknown id to generic processor"""
        df_input = pd.DataFrame({'COL1': [1, 2]})
        data = [df_input]
        result = transform.transform_factory('9999', data)
        self.assertIn('col1', result.columns) # cleaned to lower

if __name__ == '__main__':
    unittest.main()
