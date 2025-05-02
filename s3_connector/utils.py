"""
S3 Connector Utility Functions for ActivaGroup Data Lakehouse
"""
import os
import io
import logging
import pandas as pd
import boto3
from botocore.exceptions import ClientError
from django.conf import settings

# Configure logging
logger = logging.getLogger(__name__)

class S3Connector:
    """
    Class for connecting to AWS S3 and retrieving CSV files.
    """
    def __init__(self, bucket_name=None):
        """
        Initialize S3 client and bucket.
        
        Args:
            bucket_name (str, optional): S3 bucket name. Defaults to settings.AWS_STORAGE_BUCKET_NAME.
        """
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME
        )
        # Use AWS_STORAGE_BUCKET_NAME instead of S3_BUCKET_NAME
        self.bucket_name = bucket_name or settings.AWS_STORAGE_BUCKET_NAME
        logger.info(f"Initialized S3Connector for bucket: {self.bucket_name}")
    
    def list_objects(self, prefix=""):
        """
        List all objects in the S3 bucket with the given prefix.
        
        Args:
            prefix (str, optional): Filter objects by prefix. Defaults to "".
            
        Returns:
            list: List of object keys (filenames)
        """
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            
            # Check if any objects were found
            if 'Contents' not in response:
                logger.warning(f"No objects found with prefix: {prefix}")
                return []
                
            # Extract object keys (filenames)
            object_keys = [obj['Key'] for obj in response['Contents']]
            logger.info(f"Found {len(object_keys)} objects with prefix: {prefix}")
            return object_keys
            
        except ClientError as e:
            logger.error(f"Error listing objects in bucket {self.bucket_name}: {e}")
            return []
    
    def load_csv(self, key, **pandas_kwargs):
        """
        Load a CSV file from S3 into a pandas DataFrame.
        
        Args:
            key (str): Object key (filename) in S3
            **pandas_kwargs: Additional keyword arguments to pass to pd.read_csv
            
        Returns:
            pandas.DataFrame or None: DataFrame containing CSV data or None if error
        """
        try:
            logger.info(f"Loading CSV file: {key}")
            # Get object from S3
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
            
            # Read CSV into DataFrame
            df = pd.read_csv(
                io.BytesIO(response['Body'].read()),
                **pandas_kwargs
            )
            
            logger.info(f"Successfully loaded CSV: {key} with shape {df.shape}")
            # Return column names for logging
            logger.info(f"Columns: {df.columns.tolist()}")
            return df
            
        except ClientError as e:
            logger.error(f"Error loading CSV from S3: {e}")
            return None
        except pd.errors.ParserError as e:
            logger.error(f"Error parsing CSV: {e}")
            return None
    
    def load_all_csvs(self, prefix="", **pandas_kwargs):
        """
        Load all CSVs with a given prefix from S3 into a dictionary of DataFrames.
        
        Args:
            prefix (str, optional): Filter objects by prefix. Defaults to "".
            **pandas_kwargs: Additional keyword arguments to pass to pd.read_csv
            
        Returns:
            dict: Dictionary mapping filenames to DataFrames
        """
        csv_files = self.list_objects(prefix=prefix)
        csv_files = [f for f in csv_files if f.lower().endswith('.csv')]
        
        if not csv_files:
            logger.warning(f"No CSV files found with prefix: {prefix}")
            return {}
        
        dataframes = {}
        for csv_file in csv_files:
            df = self.load_csv(csv_file, **pandas_kwargs)
            if df is not None:
                # Use the filename (without extension) as the key
                key = os.path.splitext(os.path.basename(csv_file))[0]
                dataframes[key] = df
        
        logger.info(f"Loaded {len(dataframes)} CSV files successfully")
        return dataframes

# Utility function to test the connection
def test_s3_connection():
    """
    Test the S3 connection by listing available CSV files.
    
    Returns:
        list: List of CSV file names in the S3 bucket
    """
    connector = S3Connector()
    files = connector.list_objects()
    csv_files = [f for f in files if f.lower().endswith('.csv')]
    
    if csv_files:
        logger.info(f"Successfully connected to S3. Found {len(csv_files)} CSV files:")
        for csv_file in csv_files:
            logger.info(f"  - {csv_file}")
    else:
        logger.warning("Connected to S3 but no CSV files found.")
    
    return csv_files