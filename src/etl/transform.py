import pandas as pd
import logging
from typing import Any, List, Union, Tuple
from .transformers import financeiro, clientes, generico

logger = logging.getLogger(__name__)

def transform_factory(report_id: str, data: Any) -> pd.DataFrame:
    """
    Factory function to route transformation logic based on Report ID.
    
    Args:
        report_id: The ID of the report (e.g., '0387', '0002').
        data: The raw data to be processed. 
              - For '0387': Tuple(lista_caixa, lista_competencia)
              - For others: List[pd.DataFrame]
              
    Returns:
        pd.DataFrame: The processed DataFrame ready for upload.
    """
    logger.info(f"Transform Factory: Routing for Report ID {report_id}")
    
    if report_id == '0387':
        # Financeiro (Caixa + Competência)
        # Expects data to be tuple of lists
        return financeiro.process_financeiro(data)
        
    elif report_id == '0002':
        # Dimensão Clientes
        # Expects data to be List[pd.DataFrame] (from generic extract)
        return clientes.process_dim_clientes(data)
        
    else:
        # Generic Fallback
        # Expects data to be List[pd.DataFrame]
        return generico.process_generic_data(data, report_id=report_id)
        
# Expose generic helpers if legacy code still imports them from here directly (unlikely but safe)
# Though ideally consumers should import from .transformers.generico or go through factory.
from .transformers.generico import clean_currency, clean_date
