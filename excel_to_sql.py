import pandas as pd
import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

def connect_to_mysql(host, user, password, database):
    """
    Establish connection to MySQL database
    """
    try:
        connection = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database
        )
        if connection.is_connected():
            print(f"Successfully connected to MySQL database: {database}")
            return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

def create_table_from_dataframe(connection, table_name, df, unique_column='company_name'):
    """
    Create a table based on DataFrame columns with unique constraint on company_name
    """
    cursor = connection.cursor()
    
    # Generate CREATE TABLE statement
    columns = []
    for col in df.columns:
        # Simple type mapping - adjust as needed
        dtype = df[col].dtype
        if dtype == 'int64':
            col_type = 'INT'
        elif dtype == 'float64':
            col_type = 'FLOAT'
        else:
            col_type = 'VARCHAR(255)'
        
        # Add UNIQUE constraint to company_name column
        if col.lower() == unique_column.lower():
            columns.append(f"`{col}` {col_type} UNIQUE")
        else:
            columns.append(f"`{col}` {col_type}")
    
    create_table_query = f"""
    CREATE TABLE IF NOT EXISTS `{table_name}` (
        id INT AUTO_INCREMENT PRIMARY KEY,
        {', '.join(columns)}
    )
    """
    
    try:
        cursor.execute(create_table_query)
        connection.commit()
        print(f"Table '{table_name}' created successfully with UNIQUE constraint on '{unique_column}'")
    except Error as e:
        print(f"Error creating table: {e}")
    finally:
        cursor.close()

def insert_data_to_mysql(connection, table_name, df):
    """
    Insert DataFrame data into MySQL table (only new records)
    """
    cursor = connection.cursor()
    
    # Prepare INSERT IGNORE statement to skip duplicates
    cols = ', '.join([f"`{col}`" for col in df.columns])
    placeholders = ', '.join(['%s'] * len(df.columns))
    insert_query = f"INSERT IGNORE INTO `{table_name}` ({cols}) VALUES ({placeholders})"
    
    # Convert DataFrame to list of tuples, replacing NaN with None
    data = [tuple(None if pd.isna(x) else x for x in row) for row in df.values]
    
    try:
        cursor.executemany(insert_query, data)
        connection.commit()
        print(f"{cursor.rowcount} new rows inserted into '{table_name}'")
    except Error as e:
        print(f"Error inserting data: {e}")
        connection.rollback()
    finally:
        cursor.close()

def upsert_data_to_mysql(connection, table_name, df, unique_column='company_name'):
    """
    Insert or update data in MySQL table based on company_name
    """
    cursor = connection.cursor()
    
    # Prepare column lists for INSERT and UPDATE
    columns = list(df.columns)
    cols_str = ', '.join([f"`{col}`" for col in columns])
    placeholders = ', '.join(['%s'] * len(columns))
    
    # Create UPDATE clause for all columns except the unique column
    update_clause = ', '.join([f"`{col}` = VALUES(`{col}`)" for col in columns if col.lower() != unique_column.lower()])
    
    # INSERT ... ON DUPLICATE KEY UPDATE query
    upsert_query = f"""
    INSERT INTO `{table_name}` ({cols_str}) 
    VALUES ({placeholders})
    ON DUPLICATE KEY UPDATE {update_clause}
    """
    
    # Convert DataFrame to list of tuples, replacing NaN with None
    data = [tuple(None if pd.isna(x) else x for x in row) for row in df.values]
    
    try:
        cursor.executemany(upsert_query, data)
        connection.commit()
        print(f"{cursor.rowcount} rows inserted/updated in '{table_name}'")
    except Error as e:
        print(f"Error upserting data: {e}")
        connection.rollback()
    finally:
        cursor.close()

def excel_to_mysql(excel_file, sheet_name, host, user, password, database, table_name, unique_column='company_name', sync_mode='upsert'):
    """
    Main function to transfer data from Excel to MySQL
    
    Args:
        sync_mode: 'upsert' (insert new + update existing) or 'insert' (only add new records)
    """
    # Read Excel file with multiple attempts
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            # Try reading with openpyxl engine and read_only mode
            df = pd.read_excel(excel_file, sheet_name=sheet_name, engine='openpyxl')
            
            # Clean column names - remove NaN, empty strings, and invalid characters
            new_columns = []
            for i, col in enumerate(df.columns):
                if pd.isna(col) or str(col).strip() == '' or str(col).lower() == 'nan':
                    new_columns.append(f'Unnamed_Column_{i+1}')
                else:
                    # Replace spaces and special characters with underscores
                    clean_col = str(col).strip().replace(' ', '_').replace('#', 'num').replace('-', '_')
                    # Remove other problematic characters
                    clean_col = ''.join(c if c.isalnum() or c == '_' else '_' for c in clean_col)
                    new_columns.append(clean_col)
            
            df.columns = new_columns
            
            print(f"Excel file loaded: {len(df)} rows, {len(df.columns)} columns")
            print(f"Cleaned columns: {list(df.columns)}")
            
            # Update unique_column to cleaned version
            unique_column_clean = unique_column.strip().replace(' ', '_').replace('#', 'num').replace('-', '_')
            unique_column_clean = ''.join(c if c.isalnum() or c == '_' else '_' for c in unique_column_clean)
            
            # Check if unique_column exists
            if unique_column_clean not in df.columns:
                print(f"Warning: Column '{unique_column_clean}' not found in Excel. Available columns: {list(df.columns)}")
                return
            
            # Replace NaN values with None for proper NULL handling in MySQL
            df = df.where(pd.notnull(df), None)
            
            break
                
        except PermissionError as e:
            print(f"Attempt {attempt + 1}/{max_attempts}: File is locked or in use")
            if attempt < max_attempts - 1:
                print("Please close the Excel file and OneDrive sync, then press Enter to retry...")
                input()
            else:
                print(f"\nError: Cannot access the file after {max_attempts} attempts.")
                print("\nSolutions:")
                print("1. Close the Excel file if it's open")
                print("2. Pause OneDrive sync temporarily")
                print("3. Copy the file to a local folder (not in OneDrive)")
                print("4. Save the file as .csv and update the script to use pd.read_csv()")
                return
        except Exception as e:
            print(f"Error reading Excel file: {e}")
            return
    
    # Connect to MySQL
    connection = connect_to_mysql(host, user, password, database)
    if not connection:
        return
    
    try:
        # Create table with unique constraint
        create_table_from_dataframe(connection, table_name, df, unique_column_clean)
        
        # Sync data based on mode
        if sync_mode == 'upsert':
            print("Using UPSERT mode: Will insert new records and update existing ones")
            upsert_data_to_mysql(connection, table_name, df, unique_column_clean)
        else:
            print("Using INSERT mode: Will only add new records, skip duplicates")
            insert_data_to_mysql(connection, table_name, df)
        
    finally:
        if connection.is_connected():
            connection.close()
            print("MySQL connection closed")

# Example usage
if __name__ == "__main__":
    # Configure these parameters
    EXCEL_FILE = "C:\\Users\\Akash.saxena\\OneDrive - LAKSHMIKUMARAN & SRIDHARAN\\1 - KM\\Tax Summit\\Kalpana Verma's files - Akash Tax Summit File\\Tax Summit (Akash).xlsx"  # Path to your Excel file
    SHEET_NAME = "Master"      # Name of the sheet to read
    
    # MySQL connection parameters
    HOST = os.getenv("DB_HOST")
    USER = os.getenv("DB_USER")
    PASSWORD = os.getenv("DB_PASS")
    DATABASE = os.getenv("DB_NAME")
    TABLE_NAME = os.getenv("DB_TABLE")
    
    # Column name that should be unique (case-insensitive match)
    UNIQUE_COLUMN = "Client Name"  # Change this to match your Excel column name
    
    # Sync mode: 'upsert' or 'insert'
    # 'upsert': Insert new records AND update existing ones (recommended for syncing)
    # 'insert': Only insert new records, ignore duplicates
    SYNC_MODE = 'upsert'
    
    # Execute the transfer
    excel_to_mysql(
        excel_file=EXCEL_FILE,
        sheet_name=SHEET_NAME,
        host=HOST,
        user=USER,
        password=PASSWORD,
        database=DATABASE,
        table_name=TABLE_NAME,
        unique_column=UNIQUE_COLUMN,
        sync_mode=SYNC_MODE
    )
    
    print("\n✓ Sync completed! You can run this script anytime to update the database from Excel.")