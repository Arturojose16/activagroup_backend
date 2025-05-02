"""
Custom transformation functions for ActivaGroup data
Specifically designed for the file formats we've analyzed
"""
import re
import pandas as pd
import numpy as np
import logging
from io import StringIO

# Configure logging
logger = logging.getLogger(__name__)

class CustomDataTransformer:
    """
    Class for transforming and cleaning ActivaGroup data from CSV files.
    Custom-built for the specific file formats used by ActivaGroup.
    """
    
    def __init__(self):
        """Initialize the transformer with empty dataframes."""
        self.raw_dataframes = {}
        self.clean_dataframes = {}
        self.combined_data = None
    
    def load_raw_data(self, s3_connector, prefix="raw-data-activa/"):
        """
        Load raw dataframes from S3 with custom processing for each file type.
        
        Args:
            s3_connector: The S3Connector instance
            prefix: S3 prefix to filter files
        """
        # List objects in S3
        all_files = s3_connector.list_objects(prefix=prefix)
        csv_files = [f for f in all_files if f.lower().endswith('.csv')]
        
        if not csv_files:
            logger.warning(f"No CSV files found with prefix: {prefix}")
            return {}
        
        # Process each file based on its name
        for csv_file in csv_files:
            filename = csv_file.split('/')[-1]
            
            # Load raw CSV content
            try:
                response = s3_connector.s3_client.get_object(
                    Bucket=s3_connector.bucket_name, 
                    Key=csv_file
                )
                csv_content = response['Body'].read().decode('utf-8', errors='replace')
                
                # Determine which parser to use based on filename
                if "Clientes AG" in filename:
                    df = self._parse_clientes_ag(csv_content)
                elif "CLIENTES MARCAS" in filename:
                    df = self._parse_clientes_marcas(csv_content)
                elif "Ingresos" in filename:
                    df = self._parse_ingresos(csv_content)
                elif "Presupuesto" in filename:
                    df = self._parse_presupuesto(csv_content)
                elif "Profit" in filename or "Loss" in filename:
                    df = self._parse_profit_loss(csv_content)
                else:
                    # Generic parser for other files
                    df = pd.read_csv(StringIO(csv_content), encoding='utf-8')
                
                # Store with clean key name
                key = self._clean_filename(filename)
                self.raw_dataframes[key] = df
                
                logger.info(f"Successfully loaded and parsed: {filename}")
                logger.info(f"  Shape: {df.shape}")
                logger.info(f"  Columns: {df.columns.tolist()}")
                
            except Exception as e:
                logger.error(f"Error processing {filename}: {str(e)}")
        
        logger.info(f"Loaded {len(self.raw_dataframes)} CSV files")
        return self.raw_dataframes
    
    def _clean_filename(self, filename):
        """Create a clean key from filename."""
        # Remove extension and prefix
        name = filename.split('/')[-1].replace('.csv', '')
        # Remove spaces and special characters
        name = re.sub(r'[^a-zA-Z0-9]', '_', name)
        # Clean up multiple underscores
        name = re.sub(r'_+', '_', name)
        # Remove leading/trailing underscores
        name = name.strip('_')
        return name.lower()
    
    def _parse_clientes_ag(self, csv_content):
        """Parse the Clientes AG CSV."""
        # This file has headers in the first row
        df = pd.read_csv(StringIO(csv_content), encoding='utf-8')
        
        # Ensure we have the right columns
        if 'CLIENTE' in df.columns and 'INDUSTRIA:' in df.columns:
            # Clean up column names
            df.rename(columns={
                'CLIENTE': 'cliente',
                'INDUSTRIA:': 'industria'
            }, inplace=True)
        
        # Remove empty rows
        df = df.dropna(how='all')
        
        return df
    
    def _parse_clientes_marcas(self, csv_content):
        """Parse the CLIENTES MARCAS CSV."""
        # Skip the first 2 rows, headers are in row 3
        rows = csv_content.split('\n')
        header_row = None
        
        # Find the header row (the one with "Clientes / Marcas")
        for i, row in enumerate(rows):
            if "Clientes / Marcas" in row:
                header_row = i
                break
        
        if header_row is None:
            logger.warning("Could not find header row in CLIENTES MARCAS")
            # Try reading without skipping
            return pd.read_csv(StringIO(csv_content), encoding='utf-8')
        
        # Read with the correct header row
        df = pd.read_csv(
            StringIO(csv_content), 
            encoding='utf-8',
            skiprows=header_row,
            header=0
        )
        
        # Standardize column names
        column_mapping = {
            'Clientes / Marcas': 'cliente_marca',
            'TIPO DE CLIENTE:': 'tipo_cliente',
            'CLIENTE DESDE:': 'cliente_desde',
            'RUBRO DE NEGOCIOS': 'rubro_negocios'
        }
        
        # Only rename columns that exist
        rename_dict = {k: v for k, v in column_mapping.items() if k in df.columns}
        if rename_dict:
            df.rename(columns=rename_dict, inplace=True)
        
        # Drop rows with all NaN values
        df = df.dropna(how='all')
        
        return df
    
    def _parse_ingresos(self, csv_content):
        """Parse the Ingresos CSV."""
        rows = csv_content.split('\n')
        cliente_row = None
        
        # Find the row with CLIENTE header
        for i, row in enumerate(rows):
            if "CLIENTE,FACTURACION" in row:
                cliente_row = i
                break
        
        if cliente_row is None:
            logger.warning("Could not find CLIENTE row in Ingresos")
            # Try reading without skipping
            return pd.read_csv(StringIO(csv_content), encoding='utf-8')
        
        # The actual columns are in two rows
        header_row1 = rows[cliente_row].split(',')
        header_row2 = rows[cliente_row + 1].split(',')
        
        # Create a combined header
        headers = []
        for i in range(max(len(header_row1), len(header_row2))):
            if i < len(header_row1) and header_row1[i].strip():
                header = header_row1[i].strip()
            elif i < len(header_row2) and header_row2[i].strip():
                header = header_row2[i].strip()
            else:
                header = f"column_{i}"
            headers.append(header)
        
        # Read the CSV skipping the header rows
        df = pd.read_csv(
            StringIO(csv_content),
            encoding='utf-8',
            skiprows=cliente_row + 2,  # Skip both header rows
            header=None
        )
        
        # Assign our custom headers
        if len(df.columns) == len(headers):
            df.columns = headers
        else:
            logger.warning(f"Header length mismatch in Ingresos: {len(headers)} headers vs {len(df.columns)} columns")
            # Assign as many as we can
            for i in range(min(len(df.columns), len(headers))):
                df = df.rename(columns={i: headers[i]})
        
        # Clean up column names
        df.columns = [re.sub(r'[^\w\s]', '', col).strip().lower().replace(' ', '_') for col in df.columns]
        
        # Special column handling
        if 'cliente' in df.columns:
            # FIXED: Safer string handling
            # Convert to string first, then apply string methods
            df['cliente'] = df['cliente'].apply(lambda x: str(x).replace(':', '') if pd.notna(x) else x)
        
        # Convert numeric columns
        for col in df.columns:
            if col != 'cliente':
                try:
                    # FIXED: Safer numeric conversion
                    df[col] = df[col].apply(
                        lambda x: pd.to_numeric(
                            str(x).replace(',', '')
                            .replace('"', '')
                            .replace('$', '')
                            .replace('₡', '')
                            .replace('RD', ''),
                            errors='coerce'
                        ) if pd.notna(x) else np.nan
                    )
                except Exception as e:
                    logger.warning(f"Could not convert column {col} to numeric: {str(e)}")
        
        # Drop rows with no client name or all NaNs
        df = df.dropna(subset=['cliente'])
        df = df.dropna(how='all')
        
        return df
    
    def _parse_presupuesto(self, csv_content):
        """Parse the Presupuesto CSV - similar to Ingresos."""
        rows = csv_content.split('\n')
        cliente_row = None
        
        # Find the row with CLIENTE header
        for i, row in enumerate(rows):
            if "CLIENTE,FACTURACION" in row:
                cliente_row = i
                break
        
        if cliente_row is None:
            logger.warning("Could not find CLIENTE row in Presupuesto")
            # Try reading without skipping
            return pd.read_csv(StringIO(csv_content), encoding='utf-8')
        
        # The actual columns are in two rows
        header_row1 = rows[cliente_row].split(',')
        header_row2 = rows[cliente_row + 1].split(',')
        
        # Create a combined header
        headers = []
        for i in range(max(len(header_row1), len(header_row2))):
            if i < len(header_row1) and header_row1[i].strip():
                header = header_row1[i].strip()
            elif i < len(header_row2) and header_row2[i].strip():
                header = header_row2[i].strip()
            else:
                header = f"column_{i}"
            headers.append(header)
        
        # Read the CSV skipping the header rows
        df = pd.read_csv(
            StringIO(csv_content),
            encoding='utf-8',
            skiprows=cliente_row + 2,  # Skip both header rows
            header=None
        )
        
        # Assign our custom headers
        if len(df.columns) == len(headers):
            df.columns = headers
        else:
            logger.warning(f"Header length mismatch in Presupuesto: {len(headers)} headers vs {len(df.columns)} columns")
            # Assign as many as we can
            for i in range(min(len(df.columns), len(headers))):
                df = df.rename(columns={i: headers[i]})
        
        # Clean up column names
        df.columns = [re.sub(r'[^\w\s]', '', col).strip().lower().replace(' ', '_') for col in df.columns]
        
        # Special column handling
        if 'cliente' in df.columns:
            # FIXED: Safer string handling
            # Convert to string first, then apply string methods
            df['cliente'] = df['cliente'].apply(lambda x: str(x).replace(':', '') if pd.notna(x) else x)
        
        # Convert numeric columns
        for col in df.columns:
            if col != 'cliente':
                try:
                    # FIXED: Safer numeric conversion
                    df[col] = df[col].apply(
                        lambda x: pd.to_numeric(
                            str(x).replace(',', '')
                            .replace('"', '')
                            .replace('$', '')
                            .replace('₡', '')
                            .replace('RD', ''),
                            errors='coerce'
                        ) if pd.notna(x) else np.nan
                    )
                except Exception as e:
                    logger.warning(f"Could not convert column {col} to numeric: {str(e)}")
        
        # Drop rows with no client name or all NaNs
        df = df.dropna(subset=['cliente'])
        df = df.dropna(how='all')
        
        return df
    
    def _parse_profit_loss(self, csv_content):
        """Parse the Profit & Loss CSV."""
        rows = csv_content.split('\n')
        header_row = None
        
        # Find the row with Descripción
        for i, row in enumerate(rows):
            if "Descripción" in row:
                header_row = i
                break
        
        if header_row is None:
            logger.warning("Could not find Descripción row in Profit & Loss")
            # Try reading without skipping
            return pd.read_csv(StringIO(csv_content), encoding='utf-8')
        
        # Read the CSV with the correct header row
        df = pd.read_csv(
            StringIO(csv_content),
            encoding='utf-8',
            skiprows=header_row,
            header=0
        )
        
        # Rename the description column
        if 'Descripción' in df.columns:
            df.rename(columns={'Descripción': 'concepto'}, inplace=True)
        
        # Convert numeric columns
        for col in df.columns:
            if col != 'concepto':
                try:
                    # FIXED: Safer numeric conversion
                    df[col] = df[col].apply(
                        lambda x: pd.to_numeric(
                            str(x).replace(',', '')
                            .replace('"', '')
                            .replace('$', '')
                            .replace('₡', '')
                            .replace('RD', ''),
                            errors='coerce'
                        ) if pd.notna(x) else np.nan
                    )
                except Exception as e:
                    logger.warning(f"Could not convert column {col} to numeric: {str(e)}")
        
        # Drop empty rows
        df = df.dropna(how='all')
        
        return df
    
    def transform_and_combine(self):
        """
        Transform all dataframes and combine them.
        
        Returns:
            DataFrame: Combined dataframe with all client data
        """
        if not self.raw_dataframes:
            logger.warning("No raw dataframes to transform")
            return pd.DataFrame()
        
        # Extract client list from Clientes AG
        clientes_df = None
        for key, df in self.raw_dataframes.items():
            if 'clientes_ag' in key.lower():
                clientes_df = df.copy()
                break
        
        if clientes_df is None or 'cliente' not in clientes_df.columns:
            logger.warning("Could not find base client dataframe")
            # Try to find any dataframe with a client column
            for key, df in self.raw_dataframes.items():
                client_cols = [col for col in df.columns if 'client' in col.lower()]
                if client_cols:
                    clientes_df = df[[client_cols[0]]].copy()
                    clientes_df.rename(columns={client_cols[0]: 'cliente'}, inplace=True)
                    logger.info(f"Using {key} as base client dataframe")
                    break
        
        if clientes_df is None:
            logger.error("Cannot create combined dataframe: no client data found")
            return pd.DataFrame()
        
        # Start with the client dataframe
        combined = clientes_df.copy()
        
        # Process other dataframes
        for key, df in self.raw_dataframes.items():
            # Skip the base client dataframe
            if df is clientes_df:
                continue
            
            # Find client column in this dataframe
            client_cols = [col for col in df.columns if 'client' in col.lower()]
            
            if client_cols:
                client_col = client_cols[0]
                
                # For CLIENTES MARCAS, we need special handling
                if 'marcas' in key.lower() and 'cliente_marca' in df.columns:
                    # Create a mapping of brands to clients
                    marca_mapping = {}
                    current_client = None
                    
                    for idx, row in df.iterrows():
                        marca = row['cliente_marca']
                        if pd.notna(marca):
                            # Check if this is a client or a brand
                            if isinstance(marca, str) and marca.endswith(':'):  # Client
                                current_client = marca.rstrip(':')
                            else:  # Brand
                                if current_client:
                                    marca_mapping[marca] = current_client
                    
                    # Create a new dataframe with client-brand mappings
                    if marca_mapping:
                        brands_df = pd.DataFrame({
                            'marca': list(marca_mapping.keys()),
                            'cliente': list(marca_mapping.values())
                        })
                        
                        # Merge with combined dataframe
                        # First, convert both to string to avoid type mismatches
                        combined['cliente'] = combined['cliente'].astype(str)
                        brands_df['cliente'] = brands_df['cliente'].astype(str)
                        
                        # Group by client to get a list of brands per client
                        brand_groups = brands_df.groupby('cliente')['marca'].apply(list).reset_index()
                        brand_groups.rename(columns={'marca': 'marcas'}, inplace=True)
                        
                        # Merge with combined
                        combined = pd.merge(
                            combined,
                            brand_groups,
                            on='cliente',
                            how='left'
                        )
                        
                        logger.info(f"Added brand information to {len(brand_groups)} clients")
                
                # For income and budget files
                elif ('ingreso' in key.lower() or 'presupuesto' in key.lower()) and 'cliente' in df.columns:
                    # Remove any colon from client names
                    df['cliente'] = df['cliente'].apply(lambda x: str(x).replace(':', '') if pd.notna(x) else x)
                    combined['cliente'] = combined['cliente'].apply(lambda x: str(x).replace(':', '') if pd.notna(x) else x)
                    
                    # Select columns to merge, excluding the client column
                    cols_to_merge = [col for col in df.columns if col != 'cliente']
                    
                    if cols_to_merge:
                        # Merge with combined dataframe
                        combined = pd.merge(
                            combined,
                            df[['cliente'] + cols_to_merge],
                            on='cliente',
                            how='left'
                        )
                        
                        logger.info(f"Merged {len(cols_to_merge)} columns from {key}")
            
            # For Profit & Loss, which doesn't have client data
            elif 'profit' in key.lower() or 'loss' in key.lower():
                # This is summary financial data, not client-specific
                # We'll save it separately
                self.clean_dataframes['financial_summary'] = df
                logger.info(f"Saved financial summary data from {key}")
        
        # Clean up the combined dataframe
        # Remove duplicate columns
        combined = combined.loc[:, ~combined.columns.duplicated()]
        
        # Store the result
        self.combined_data = combined
        logger.info(f"Created combined dataframe with {len(combined)} clients and {len(combined.columns)} columns")
        
        return combined
    
    def get_combined_data(self):
        """
        Get the combined data as a dictionary for API response.
        
        Returns:
            dict: Combined data in dictionary format suitable for API response
        """
        if self.combined_data is None or self.combined_data.empty:
            return {
                'status': 'error',
                'message': 'No combined data available',
                'data': {}
            }
        
        # Create a safe copy to avoid modifying the original
        safe_data = []
        
        # Convert to dictionary with safe JSON values
        for record in self.combined_data.to_dict(orient='records'):
            # Create a safe record with JSON-compatible values
            safe_record = {}
            for key, value in record.items():
                # Handle different data types
                if isinstance(value, (int, bool)) or value is None:
                    safe_record[key] = value
                elif isinstance(value, float):
                    if pd.isna(value) or np.isinf(value):
                        safe_record[key] = None
                    else:
                        safe_record[key] = value
                elif isinstance(value, str):
                    safe_record[key] = value
                elif isinstance(value, list):
                    # Handle lists (like brand lists)
                    safe_list = []
                    for item in value:
                        if isinstance(item, str):
                            safe_list.append(item)
                        else:
                            # Convert non-string items to strings
                            try:
                                safe_list.append(str(item))
                            except:
                                # If conversion fails, use placeholder
                                safe_list.append("Unknown item")
                    safe_record[key] = safe_list
                else:
                    # Convert any other types to string
                    try:
                        safe_record[key] = str(value)
                    except:
                        # If conversion fails, use placeholder
                        safe_record[key] = "Unknown value"
            
            safe_data.append(safe_record)
        
        # Convert to dictionary
        result = {
            'status': 'success',
            'message': f'Combined data with {len(self.combined_data)} clients and {len(self.combined_data.columns)} metrics',
            'data': safe_data
        }
        
        return result
    
    def get_financial_summary(self):
        """
        Get the financial summary data as a dictionary for API response.
        
        Returns:
            dict: Financial summary in dictionary format
        """
        if 'financial_summary' not in self.clean_dataframes:
            return {
                'status': 'error',
                'message': 'No financial summary data available',
                'data': {}
            }
        
        financial_df = self.clean_dataframes['financial_summary']
        
        # Calculate some key metrics
        total_income = None
        total_costs = None
        gross_profit = None
        
        try:
            # Find rows with these specific concepts
            if 'concepto' in financial_df.columns and 'CONSOLIDADO' in financial_df.columns:
                total_income_row = financial_df[financial_df['concepto'] == 'Total Ingresos']
                if not total_income_row.empty:
                    total_income = float(total_income_row['CONSOLIDADO'].iloc[0])
                
                total_costs_row = financial_df[financial_df['concepto'] == 'Total Costos']
                if not total_costs_row.empty:
                    total_costs = float(total_costs_row['CONSOLIDADO'].iloc[0])
                
                gross_profit_row = financial_df[financial_df['concepto'] == 'GROSS PROFIT']
                if not gross_profit_row.empty:
                    gross_profit = float(gross_profit_row['CONSOLIDADO'].iloc[0])
        except Exception as e:
            logger.warning(f"Error calculating financial metrics: {str(e)}")
        
        # Calculate gross margin percentage with safeguards
        gross_margin_pct = None
        if total_income is not None and gross_profit is not None and total_income != 0:
            gross_margin_pct = (gross_profit / total_income * 100)
        
        # Prepare financial data with JSON-safe values
        safe_data = []
        for record in financial_df.to_dict(orient='records'):
            # Replace any NaN or Infinity values with None (null in JSON)
            safe_record = {}
            for key, value in record.items():
                if isinstance(value, float) and (pd.isna(value) or np.isinf(value)):
                    safe_record[key] = None
                else:
                    safe_record[key] = value
            safe_data.append(safe_record)
        
        # Convert to dictionary
        result = {
            'status': 'success',
            'message': 'Financial summary data',
            'summary': {
                'total_income': total_income,
                'total_costs': total_costs,
                'gross_profit': gross_profit,
                'gross_margin_percentage': gross_margin_pct
            },
            'data': safe_data
        }
        
        return result