"""
Simple test script for S3 connection
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

# Add Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'activagroup_backend.settings')
import django
django.setup()

from s3_connector.utils import S3Connector

def test_s3_connection():
    """Test S3 connection and list files"""
    logger.info("Testing S3 connection...")
    
    connector = S3Connector()
    files = connector.list_objects()
    
    if files:
        logger.info(f"Success! Found {len(files)} files in the S3 bucket:")
        for file in files:
            logger.info(f"  - {file}")
    else:
        logger.error("No files found in the S3 bucket")
    
    # Find CSV files
    csv_files = [f for f in files if f.lower().endswith('.csv')]
    if csv_files:
        logger.info(f"Found {len(csv_files)} CSV files")
    
    return files

def test_load_csv_sample():
    """Test loading a sample CSV file to see its contents"""
    logger.info("Testing CSV loading...")
    
    connector = S3Connector()
    files = connector.list_objects()
    
    # Find CSV files
    csv_files = [f for f in files if f.lower().endswith('.csv')]
    
    if not csv_files:
        logger.error("No CSV files found")
        return
    
    # Try to load the first CSV file
    sample_file = csv_files[0]
    logger.info(f"Loading sample file: {sample_file}")
    
    try:
        df = connector.load_csv(sample_file)
        
        if df is not None:
            logger.info(f"Successfully loaded {sample_file}")
            logger.info(f"Shape: {df.shape}")
            logger.info(f"Columns: {df.columns.tolist()}")
            
            # Show first few rows
            logger.info("First 5 rows:")
            pd.set_option('display.max_columns', None)
            pd.set_option('display.width', 1000)
            logger.info(df.head(5))
            
            # Save to CSV for inspection
            output_file = 'sample_data.csv'
            df.to_csv(output_file, index=False)
            logger.info(f"Saved sample to {output_file}")
        else:
            logger.error(f"Failed to load {sample_file}")
    
    except Exception as e:
        logger.error(f"Error loading CSV: {str(e)}")

if __name__ == '__main__':
    logger.info("Starting simple S3 test")
    test_s3_connection()
    test_load_csv_sample()
    logger.info("Test completed")