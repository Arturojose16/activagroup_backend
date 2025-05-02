"""
Test script for the API views
"""
import os
import sys
import logging
import json
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s [%(asctime)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Base URL - update this for your actual server
BASE_URL = "http://127.0.0.1:8000"

def test_connection_endpoint():
    """Test the connection endpoint"""
    url = f"{BASE_URL}/api/test-connection/"
    logger.info(f"Testing endpoint: {url}")
    
    try:
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"Success! Status: {data.get('status')}")
            logger.info(f"Message: {data.get('message')}")
            if 'files' in data:
                logger.info(f"Found {len(data['files'])} files")
        else:
            logger.error(f"Error: Status code {response.status_code}")
            logger.error(response.text)
    
    except Exception as e:
        logger.error(f"Error connecting to endpoint: {str(e)}")

def test_clients_endpoint():
    """Test the clients endpoint"""
    url = f"{BASE_URL}/api/clients/"
    logger.info(f"Testing endpoint: {url}")
    
    try:
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"Success! Status: {data.get('status')}")
            
            if 'clients' in data:
                clients = data['clients']
                logger.info(f"Found {len(clients)} clients")
                
                # Show a few sample clients
                sample_size = min(5, len(clients))
                logger.info(f"Sample of {sample_size} clients:")
                for i, client in enumerate(clients[:sample_size]):
                    logger.info(f"  {i+1}. {client.get('cliente', 'Unknown')} - {client.get('industria', 'Unknown')}")
                
                # Save to JSON for inspection
                clients_file = 'clients_list.json'
                with open(clients_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                
                logger.info(f"Saved clients list to {clients_file}")
        else:
            logger.error(f"Error: Status code {response.status_code}")
            logger.error(response.text)
    
    except Exception as e:
        logger.error(f"Error connecting to endpoint: {str(e)}")

def test_financial_summary_endpoint():
    """Test the financial summary endpoint"""
    url = f"{BASE_URL}/api/financial-summary/"
    logger.info(f"Testing endpoint: {url}")
    
    try:
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"Success! Status: {data.get('status')}")
            
            if 'summary' in data:
                summary = data['summary']
                logger.info("Financial summary:")
                for key, value in summary.items():
                    logger.info(f"  - {key}: {value}")
                
                # Save to JSON for inspection
                summary_file = 'financial_summary_api.json'
                with open(summary_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                
                logger.info(f"Saved financial summary to {summary_file}")
        else:
            logger.error(f"Error: Status code {response.status_code}")
            logger.error(response.text)
    
    except Exception as e:
        logger.error(f"Error connecting to endpoint: {str(e)}")

def test_combined_metrics_endpoint():
    """Test the combined metrics endpoint"""
    url = f"{BASE_URL}/api/combined-metrics/"
    logger.info(f"Testing endpoint: {url}")
    
    try:
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"Success! Status: {data.get('status')}")
            logger.info(f"Message: {data.get('message')}")
            
            if 'data' in data and isinstance(data['data'], list):
                records = data['data']
                logger.info(f"Received {len(records)} records")
                
                # Show a sample of the first record
                if records:
                    logger.info("Sample data from first record:")
                    first_record = records[0]
                    for key, value in list(first_record.items())[:5]:
                        logger.info(f"  - {key}: {value}")
                    
                    # Save to JSON for inspection
                    sample_size = min(5, len(records))
                    sample = records[:sample_size]
                    
                    metrics_file = 'combined_metrics_sample.json'
                    with open(metrics_file, 'w', encoding='utf-8') as f:
                        json.dump(sample, f, ensure_ascii=False, indent=2)
                    
                    logger.info(f"Saved sample of {sample_size} records to {metrics_file}")
        else:
            logger.error(f"Error: Status code {response.status_code}")
            logger.error(response.text)
    
    except Exception as e:
        logger.error(f"Error connecting to endpoint: {str(e)}")

def run_tests():
    """Run all endpoint tests"""
    logger.info("Starting API endpoint tests")
    
    # Test basic connection
    test_connection_endpoint()
    
    # Test clients list
    test_clients_endpoint()
    
    # Test financial summary
    test_financial_summary_endpoint()
    
    # Test combined metrics
    test_combined_metrics_endpoint()
    
    logger.info("API tests completed")

if __name__ == '__main__':
    run_tests()