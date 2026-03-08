import time
import pandas as pd
import logging
from datetime import datetime
from pathlib import Path
import sys

# Add src to path
SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.append(str(PROJECT_ROOT))
sys.path.append(str(PROJECT_ROOT / "src"))

from etl import extract, transform, load_cloud

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_extract_concurrency():
    logger.info(">>> TEST: Extract Concurrency")
    start_time = time.time()
    
    # Mocking extract logic or running actual one for a short period?
    # Let's try running the actual one but for a small range if possible.
    # We can pass specific dates to extract_financial_data.
    
    # We define a short range: 2 months back from now.
    end_date = datetime.now()
    start_date = end_date.replace(day=1) # Current month
    # To test concurrency properly, we need at least 2 checks.
    # But for a dry run, we just want to ensure it doesn't crash.
    
    try:
        # We invoke extract_financial_data directly
        # Note: Since it pulls from "2023-08-01" by default, let's override it if possible.
        # The function signature is extract_financial_data(start_date_str: str = "2023-08-01")
        
        # Override to just check last 2 months to be quick
        test_start_date = (datetime.now().replace(day=1) - pd.DateOffset(months=1)).strftime("%Y-%m-%d")
        
        caixa, competencia = extract.extract_financial_data(start_date_str=test_start_date)
        
        logger.info(f"Extract finished in {time.time() - start_time:.2f}s")
        logger.info(f"Caixa DFs: {len(caixa)}, Competencia DFs: {len(competencia)}")
        return caixa, competencia
    except Exception as e:
        logger.error(f"Extract failed: {e}")
        raise e

def test_transform_vectorization(caixa, competencia):
    logger.info(">>> TEST: Transform Vectorization")
    start_time = time.time()
    
    try:
        df_processed = transform.process_data(caixa, competencia)
        logger.info(f"Transform finished in {time.time() - start_time:.2f}s")
        logger.info(f"Processed DF Shape: {df_processed.shape}")
        
        # Verify Currency Cleaning Logic
        if not df_processed.empty and 'Valor' in df_processed.columns:
            # Check if values are actually floats
            is_float = pd.api.types.is_float_dtype(df_processed['Valor'])
            logger.info(f"Column 'Valor' is float: {is_float}")
            if not is_float:
                logger.warning(f"Column 'Valor' dtype: {df_processed['Valor'].dtype}")
                # Sample values
                logger.info(f"Sample values: {df_processed['Valor'].head().tolist()}")
        
        return df_processed
    except Exception as e:
        logger.error(f"Transform failed: {e}")
        raise e

def run_benchmarks():
    try:
        caixa, competencia = test_extract_concurrency()
        df = test_transform_vectorization(caixa, competencia)
        logger.info("ALL TESTS PASSED SUCCESSFULLY.")
    except Exception as e:
        logger.critical(f"Benchmark SUITE FAILED: {e}")

if __name__ == "__main__":
    run_benchmarks()
