"""
Local testing script for S3 connection and data transformation
"""
import os
import sys
import logging
import json
import pandas as pd

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s [%(asctime)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Add Django settings (modify as needed)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'activagroup_backend.settings')
import django
django.setup()

from s3_connector.utils import S3Connector
from s3_connector.transform import CustomDataTransformer

def test_s3_connection():
    """Test S3 connection and list files"""
    connector = S3Connector()
    files = connector.list_objects()
    
    if files:
        logger.info(f"Success! Found {len(files)} files in the S3 bucket")
        for file in files:
            logger.info(f"  - {file}")
    else:
        logger.error("No files found in the S3 bucket")
    
    return files

def test_custom_loader():
    """Test loading CSVs using the custom transformer"""
    connector = S3Connector()
    transformer = CustomDataTransformer()
    
    logger.info("Loading and parsing CSV files with custom transformer")
    dataframes = transformer.load_raw_data(connector)
    
    if dataframes:
        logger.info(f"Success! Loaded {len(dataframes)} CSV files")
        for name, df in dataframes.items():
            logger.info(f"  - {name}: {df.shape} - Columns: {df.columns.tolist()[:5]}...")
    else:
        logger.error("Failed to load any CSV files using custom transformer")
    
    return transformer, dataframes

def test_transform_and_combine(transformer):
    """Test transforming and combining the data"""
    logger.info("Transforming and combining data...")
    combined = transformer.transform_and_combine()
    
    if combined is not None and not combined.empty:
        logger.info(f"Success! Combined data has shape {combined.shape}")
        logger.info(f"Combined columns: {combined.columns.tolist()}")
        
        # Save a sample to JSON
        sample_size = min(5, len(combined))
        sample = combined.head(sample_size).reset_index(drop=True)
        
        sample_file = 'combined_sample.json'
        with open(sample_file, 'w', encoding='utf-8') as f:
            json.dump(sample.to_dict(orient='records'), f, ensure_ascii=False, indent=2)
        
        logger.info(f"Saved sample of {sample_size} records to {sample_file}")
    else:
        logger.error("Failed to combine dataframes")
    
    return combined

def test_financial_summary(transformer):
    """Test extracting the financial summary"""
    logger.info("Extracting financial summary...")
    summary = transformer.get_financial_summary()
    
    if summary['status'] == 'success':
        logger.info("Successfully extracted financial summary")
        if 'summary' in summary:
            for key, value in summary['summary'].items():
                logger.info(f"  - {key}: {value}")
        
        # Save summary to JSON
        summary_file = 'financial_summary.json'
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Saved financial summary to {summary_file}")
    else:
        logger.warning(f"No financial summary available: {summary['message']}")

def run_full_test():
    """Run full test of S3 connection, loading, transformation, and combination"""
    logger.info("Starting full test of S3 connector pipeline")
    
    # Test S3 connection
    files = test_s3_connection()
    if not files:
        logger.error("Stopping test due to connection failure")
        return
    
    # Test custom loader
    transformer, dataframes = test_custom_loader()
    if not dataframes:
        logger.error("Stopping test due to loading failure")
        return
    
    # Test transform and combine
    combined = test_transform_and_combine(transformer)
    if combined is None or combined.empty:
        logger.error("Combining data failed")
        return
    
    # Test financial summary
    test_financial_summary(transformer)
    
    logger.info("Full test completed successfully")

if __name__ == '__main__':
    run_full_test()