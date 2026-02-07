import unittest
import pandas as pd
import numpy as np
import datetime
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.etl.cleaning import clean_column_name, clean_currency, clean_date

class TestCleaning(unittest.TestCase):
    def test_clean_column_name(self):
        self.assertEqual(clean_column_name("Valor Total"), "valor_total")
        self.assertEqual(clean_column_name("Mês/Ano"), "mes_ano")
        self.assertEqual(clean_column_name("Ação!"), "acao!")
        self.assertEqual(clean_column_name("  Espaços  "), "espacos")
        self.assertEqual(clean_column_name("Custos (R$)"), "custos_r$") # Wait, regex removes (), but what about $?
        # My regex was r'[().%]' -> so $ stays. Let's check implementation. 
        # clean_column_name regex: r'[().%]' removes these.
        # then unicodedata normalize removes accents.
        # then re.sub(r'[\s-]+', '_', name_clean)
        # then re.sub(r'_+', '_', name_clean).strip('_')
        # So "Custos (R$)" -> "custos r$" -> "custos_r$"
        
    def test_clean_currency(self):
        s = pd.Series(["R$ 1.000,00", "1,50", "(100)", "invalid", None])
        clean = list(clean_currency(s))
        
        # Check values
        self.assertEqual(clean[0], 1000.0)
        self.assertEqual(clean[1], 1.5)
        self.assertEqual(clean[2], -100.0)
        self.assertTrue(pd.isna(clean[3])) # coercing invalid to NaN
        self.assertTrue(pd.isna(clean[4]))

    def test_clean_date(self):
        s = pd.Series(["01/01/2023", "30/12/2022", "inv", None])
        clean = list(clean_date(s))
        
        self.assertEqual(clean[0], datetime.date(2023, 1, 1))
        self.assertEqual(clean[1], datetime.date(2022, 12, 30))
        self.assertTrue(pd.isna(clean[2])) # NaT is not None, but pd.isna handles it
        self.assertTrue(pd.isna(clean[3]))

if __name__ == '__main__':
    unittest.main()
