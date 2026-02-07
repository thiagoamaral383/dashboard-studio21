import pandas as pd
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Paths - Assuming this file is in src/etl/
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
PASTA_RAIZ_RELATORIOS = PROJECT_ROOT / "reports"

def save_to_excel(df: pd.DataFrame, subpasta: str, filename: str):
    """Saves DataFrame to Excel in the specified subfolder."""
    subpasta_path = PASTA_RAIZ_RELATORIOS / subpasta
    subpasta_path.mkdir(parents=True, exist_ok=True)
    
    caminho_completo_arquivo = subpasta_path / filename
    
    try:
        df.to_excel(caminho_completo_arquivo, index=False, header=True)
        logger.info(f">>> SUCESSO! Salvo em: {caminho_completo_arquivo}")
    except Exception as e:
        logger.error(f"Erro ao salvar Excel localmente: {e}")
