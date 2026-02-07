import pandas as pd
import logging
from typing import Any
from .transformers import financeiro, clientes, operacional, comandas, bandeiras, retorno, profissionais

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
        return financeiro.process_financeiro(data)
        
    elif report_id == '0002':
        # Dimensão Clientes
        return clientes.process_dim_clientes(data)
        
    elif report_id == '0126':
        # Operacional: Ocupação
        return operacional.process_ocupacao(data)

    elif report_id == '0186':
        # Fato Comandas
        return comandas.process_comandas(data)

    elif report_id == '0188':
        # Financeiro: Bandeiras (Taxas Maquininha)
        return bandeiras.process_bandeiras(data)

    elif report_id == '0007':
        # Retorno (Retenção de Clientes)
        return retorno.process_retorno(data)

    elif report_id == '0229':
        # Profissionais
        return profissionais.process_profissionais(data)
        
    else:
        # Strict Mode: Fail if report ID is unknown
        raise ValueError(f"No transformer implementation found for report_id: {report_id}")
