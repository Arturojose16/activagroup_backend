"""
ActivaGroup API views using the CustomDataTransformer
"""
import logging
import pandas as pd
import numpy as np
from django.http import JsonResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings

from .utils import S3Connector
from .transform import CustomDataTransformer

# Configure logging
logger = logging.getLogger(__name__)

@api_view(['GET'])
def test_connection(request):
    return Response({"message": "API Connection Successful!"}, status=status.HTTP_200_OK)

@api_view(['GET'])
def combined_metrics(request):
    """
    API endpoint that provides combined metrics from all data sources.
    Uses the custom transformer for ActivaGroup's specific CSV formats.
    
    Returns:
        Response: JSON response with combined metrics
    """
    import pandas as pd
    import numpy as np
    
    try:
        # Initialize S3 connector
        logger.info("Initializing S3 connector")
        s3_connector = S3Connector()
        
        # Initialize custom transformer
        logger.info("Initializing custom data transformer")
        transformer = CustomDataTransformer()
        
        # Load and parse raw data in one step
        logger.info("Loading and parsing CSV files from S3")
        raw_dataframes = transformer.load_raw_data(s3_connector)
        
        if not raw_dataframes:
            logger.error("No CSV files were loaded successfully")
            return Response(
                {"status": "error", "message": "No data files could be loaded"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Transform and combine all data
        logger.info("Transforming and combining all data")
        combined_data = transformer.transform_and_combine()
        
        if combined_data.empty:
            logger.error("Failed to create combined data")
            return Response(
                {"status": "error", "message": "Failed to create combined data"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Get combined data as dictionary
        logger.info("Getting combined data as dictionary")
        
        # Manual conversion - safer approach
        safe_data = []
        for _, row in combined_data.iterrows():
            record = {}
            for col in combined_data.columns:
                value = row[col]
                # Handle different types
                if isinstance(value, (int, bool)) or value is None:
                    record[col] = value
                elif isinstance(value, float):
                    if pd.isna(value) or np.isinf(value):
                        record[col] = None
                    else:
                        record[col] = value
                elif isinstance(value, str):
                    record[col] = value
                elif isinstance(value, list):
                    record[col] = [str(x) for x in value]
                else:
                    # Convert anything else to string
                    record[col] = str(value)
            safe_data.append(record)
            
        result = {
            "status": "success",
            "message": f"Combined data with {len(combined_data)} clients and {len(combined_data.columns)} metrics",
            "data": safe_data
        }
        
        logger.info("Successfully processed and combined data")
        return Response(result, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error processing data: {str(e)}")
        return Response(
            {"status": "error", "message": f"Error processing data: {str(e)}"}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
@api_view(['GET'])
def financial_summary(request):
    """
    API endpoint that provides financial summary data from the Profit & Loss file.
    """
    try:
        logger.info("Initializing S3 connector")
        s3_connector = S3Connector()
        
        transformer = CustomDataTransformer()
        transformer.load_raw_data(s3_connector)
        transformer.transform_and_combine()
        
        result = transformer.get_financial_summary()

        # 🔥 Safely clean NaN and Infinity in financial summary too
        for k, v in result.items():
            if isinstance(v, (float, np.floating)) and (np.isnan(v) or np.isinf(v)):
                result[k] = 0
        
        return Response(result, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error processing financial data: {str(e)}")
        return Response({"status": "error", "message": f"Error processing financial data: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def client_list(request):
    """
    API endpoint that returns a list of all clients.
    """
    try:
        logger.info("Initializing S3 connector")
        s3_connector = S3Connector()
        
        transformer = CustomDataTransformer()
        raw_dataframes = transformer.load_raw_data(s3_connector)
        
        if not raw_dataframes:
            logger.error("No CSV files were loaded successfully")
            return Response({"status": "error", "message": "No data files could be loaded"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        client_df = None
        for key, df in raw_dataframes.items():
            if 'clientes_ag' in key.lower() and 'cliente' in df.columns:
                client_df = df
                break
        
        if client_df is None:
            logger.error("Could not find client data")
            return Response({"status": "error", "message": "Client data not found"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        clients = client_df[['cliente', 'industria']].dropna(subset=['cliente']).to_dict(orient='records')
        
        return Response({"status": "success", "count": len(clients), "clients": clients}, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error retrieving client list: {str(e)}")
        return Response({"status": "error", "message": f"Error retrieving client list: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def client_detail(request, client_name):
    """
    API endpoint that provides detailed information for a specific client.
    """
    try:
        logger.info(f"Getting details for client: {client_name}")
        s3_connector = S3Connector()
        
        transformer = CustomDataTransformer()
        transformer.load_raw_data(s3_connector)
        combined_data = transformer.transform_and_combine()
        
        if combined_data.empty:
            logger.error("Failed to create combined data")
            return Response({"status": "error", "message": "Failed to create combined data"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        clean_client_name = client_name.replace(':', '')
        combined_data['cliente'] = combined_data['cliente'].astype(str)
        client_data = combined_data[combined_data['cliente'].str.contains(clean_client_name, case=False, na=False)]
        
        if client_data.empty:
            logger.warning(f"No data found for client: {client_name}")
            return Response({"status": "error", "message": f"No data found for client: {client_name}"}, status=status.HTTP_404_NOT_FOUND)
        
        client_details = client_data.to_dict(orient='records')
        
        return Response({"status": "success", "client": client_name, "count": len(client_details), "data": client_details}, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error retrieving client details: {str(e)}")
        return Response({"status": "error", "message": f"Error retrieving client details: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def industry_summary(request):
    """
    API endpoint that provides a summary of clients by industry.
    """
    try:
        logger.info("Initializing S3 connector")
        s3_connector = S3Connector()
        
        transformer = CustomDataTransformer()
        raw_dataframes = transformer.load_raw_data(s3_connector)
        
        if not raw_dataframes:
            logger.error("No CSV files were loaded successfully")
            return Response({"status": "error", "message": "No data files could be loaded"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        client_df = None
        for key, df in raw_dataframes.items():
            if 'clientes_ag' in key.lower() and 'cliente' in df.columns and 'industria' in df.columns:
                client_df = df
                break
        
        if client_df is None:
            logger.error("Could not find client industry data")
            return Response({"status": "error", "message": "Client industry data not found"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        industry_counts = client_df.groupby('industria')['cliente'].count().reset_index()
        industry_counts.rename(columns={'cliente': 'count'}, inplace=True)
        industry_counts = industry_counts.sort_values('count', ascending=False)
        industry_summary = industry_counts.to_dict(orient='records')
        
        return Response({"status": "success", "total_industries": len(industry_summary), "industries": industry_summary}, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error generating industry summary: {str(e)}")
        return Response({"status": "error", "message": f"Error generating industry summary: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)