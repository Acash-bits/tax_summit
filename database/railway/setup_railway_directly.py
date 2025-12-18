import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv

load_dotenv()

def connect_to_railway():
    """Connect directly to Railway"""
    try:
        connection = mysql.connector.connect(
            host=os.getenv("RAILWAY_DB_HOST"),
            user=os.getenv("RAILWAY_DB_USER"),
            password=os.getenv("RAILWAY_DB_PASS"),
            database=os.getenv("RAILWAY_DB_NAME"),
            port=int(os.getenv("RAILWAY_DB_PORT", 3306))
        )
        if connection.is_connected():
            print(f"✓ Connected to Railway database")
            return connection
    except Error as e:
        print(f"✗ Error: {e}")
        return None

def get_local_master_columns():
    """Get actual column list from local master table"""
    try:
        connection = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS"),
            database=os.getenv("DB_NAME"),
            port=int(os.getenv("DB_PORT", 3306))
        )
        cursor = connection.cursor()
        cursor.execute("SHOW COLUMNS FROM tax_summit_master_data")
        columns = [row[0] for row in cursor.fetchall() if row[0] != 'id']
        cursor.close()
        connection.close()
        print(f"   Found {len(columns)} columns in local master table")
        return columns
    except Exception as e:
        print(f"   ⚠️  Could not read local columns: {e}")
        return []

def create_master_table(connection):
    """Create master table with optimized column types"""
    cursor = connection.cursor()
    
    # Get columns from local
    local_columns = get_local_master_columns()
    
    if not local_columns:
        print("⚠️  Could not read local columns, using default structure")
        local_columns = [
            'Practice_Head', 'Partner', 'Client_Name', 'Sector', 'Location',
            'numInvitees', 'numRegistrations', 'Response', 'Invite_Status',
            'Invite_Dt', 'Circle_Back_Dt', 'Tax_Contact', 'Designation',
            'Email_ID', 'Phone_Number', 'Response_1', 'CFO_Name',
            'Designation_2', 'Email_ID_3', 'Phone_Number_4', 'Location_6',
            'Response_7', 'Others', 'Designation_8', 'Email_ID_9',
            'Phone_Number_10', 'Location_12', 'Response_13'
        ]
    
    # Build CREATE TABLE statement with smart column types
    column_defs = ["id INT AUTO_INCREMENT PRIMARY KEY"]
    
    # Special handling for important columns
    important_columns = {
        'Client_Name': 'VARCHAR(255) UNIQUE',  # Keep unique constraint
        'Practice_Head': 'VARCHAR(100)',
        'Partner': 'VARCHAR(100)',
        'Sector': 'VARCHAR(100)',
        'Location': 'VARCHAR(100)',
        'Email_ID': 'VARCHAR(255)',
        'Email_ID_3': 'VARCHAR(255)',
        'Email_ID_9': 'VARCHAR(255)',
        'Phone_Number': 'VARCHAR(50)',
        'Phone_Number_4': 'VARCHAR(50)',
        'Phone_Number_10': 'VARCHAR(50)',
    }
    
    # Add columns with appropriate types
    for col in local_columns:
        if col in important_columns:
            column_defs.append(f"`{col}` {important_columns[col]}")
        else:
            # Use TEXT for less critical columns to save row size
            column_defs.append(f"`{col}` TEXT")
    
    # Add timestamps
    column_defs.append("Data_Insert_Time TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    column_defs.append("Last_Updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP")
    
    # Add indexes only on important columns
    indexes = []
    if 'Practice_Head' in local_columns:
        indexes.append("INDEX idx_practice_head (Practice_Head)")
    if 'Partner' in local_columns:
        indexes.append("INDEX idx_partner (Partner)")
    if 'Sector' in local_columns:
        indexes.append("INDEX idx_sector (Sector)")
    if 'Location' in local_columns:
        indexes.append("INDEX idx_location (Location)")
    if 'Response' in local_columns:
        indexes.append("INDEX idx_response (Response(100))")  # Prefix index for TEXT
    
    create_table_sql = f"""
    CREATE TABLE IF NOT EXISTS tax_summit_master_data (
        {', '.join(column_defs + indexes)}
    )
    """
    
    try:
        cursor.execute(create_table_sql)
        connection.commit()
        print(f"✓ Master table created with {len(local_columns) + 3} columns")
        print(f"   Using optimized column types (VARCHAR for key fields, TEXT for others)")
        return True
    except Error as e:
        print(f"✗ Error creating master table: {e}")
        print(f"   Trying with all TEXT columns...")
        
        # Fallback: Use TEXT for everything except key fields
        column_defs_fallback = ["id INT AUTO_INCREMENT PRIMARY KEY"]
        
        if 'Client_Name' in local_columns:
            column_defs_fallback.append("Client_Name VARCHAR(255) UNIQUE")
            local_columns_copy = [c for c in local_columns if c != 'Client_Name']
        else:
            local_columns_copy = local_columns
        
        for col in local_columns_copy:
            column_defs_fallback.append(f"`{col}` TEXT")
        
        column_defs_fallback.append("Data_Insert_Time TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        column_defs_fallback.append("Last_Updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP")
        
        create_table_fallback = f"""
        CREATE TABLE IF NOT EXISTS tax_summit_master_data (
            {', '.join(column_defs_fallback)}
        )
        """
        
        try:
            cursor.execute(create_table_fallback)
            connection.commit()
            print(f"✓ Master table created with TEXT columns (fallback)")
            return True
        except Error as e2:
            print(f"✗ Fallback also failed: {e2}")
            return False
    finally:
        cursor.close()

def create_child_tables(connection):
    """Create child tables with lowercase names"""
    cursor = connection.cursor()
    
    tables = [
        """
        CREATE TABLE IF NOT EXISTS tax_persons_details (
            id INT AUTO_INCREMENT PRIMARY KEY,
            Client_Name VARCHAR(255) NOT NULL,
            numRegistrations VARCHAR(50),
            Tax_Contact VARCHAR(255),
            Designation VARCHAR(255),
            Email_ID VARCHAR(255),
            Phone_Number VARCHAR(50) UNIQUE,
            Response_1 TEXT,
            Data_Insert_Time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            Contact_File_Created_Time_Stamp TIMESTAMP NULL,
            Contact_Created_Status TINYINT(1) DEFAULT 0,
            FOREIGN KEY (Client_Name) REFERENCES tax_summit_master_data(Client_Name) 
                ON UPDATE CASCADE ON DELETE CASCADE,
            INDEX idx_client (Client_Name),
            INDEX idx_status (Contact_Created_Status)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS cfo_persons_details (
            id INT AUTO_INCREMENT PRIMARY KEY,
            Company_Name VARCHAR(255) NOT NULL,
            numRegistrations VARCHAR(50),
            CFO_Name VARCHAR(255),
            Designation_2 VARCHAR(255),
            Email_ID_3 VARCHAR(255),
            Phone_Number_4 VARCHAR(50) UNIQUE,
            Response_7 TEXT,
            Data_Insert_Time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            Contact_File_Created_Time_Stamp TIMESTAMP NULL,
            Contact_Created_Status TINYINT(1) DEFAULT 0,
            FOREIGN KEY (Company_Name) REFERENCES tax_summit_master_data(Client_Name) 
                ON UPDATE CASCADE ON DELETE CASCADE,
            INDEX idx_company (Company_Name),
            INDEX idx_status (Contact_Created_Status)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS other_persons_details (
            id INT AUTO_INCREMENT PRIMARY KEY,
            Company_Name VARCHAR(255) NOT NULL,
            numRegistrations VARCHAR(50),
            Others VARCHAR(255),
            Designation_8 VARCHAR(255),
            Email_ID_9 VARCHAR(255),
            Phone_Number_10 VARCHAR(50) UNIQUE,
            Response_13 TEXT,
            Data_Insert_Time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            Contact_File_Created_Time_Stamp TIMESTAMP NULL,
            Contact_Created_Status TINYINT(1) DEFAULT 0,
            FOREIGN KEY (Company_Name) REFERENCES tax_summit_master_data(Client_Name) 
                ON UPDATE CASCADE ON DELETE CASCADE,
            INDEX idx_company (Company_Name),
            INDEX idx_status (Contact_Created_Status)
        )
        """
    ]
    
    try:
        for table_sql in tables:
            cursor.execute(table_sql)
        connection.commit()
        print("✓ Child tables created (lowercase, optimized)")
        return True
    except Error as e:
        print(f"✗ Error creating child tables: {e}")
        return False
    finally:
        cursor.close()

def create_analysis_tables(connection):
    """Create analysis tables with lowercase names"""
    cursor = connection.cursor()
    
    tables = [
        """
        CREATE TABLE IF NOT EXISTS tax_persons_analysis (
            id INT AUTO_INCREMENT PRIMARY KEY,
            Client_Name VARCHAR(255) NOT NULL,
            Practice_Head VARCHAR(100),
            Partner VARCHAR(100),
            Invite_Status VARCHAR(100),
            numInvitees VARCHAR(50),
            Response TEXT,
            Sector VARCHAR(100),
            numRegistrations VARCHAR(50),
            Tax_Contact VARCHAR(255),
            Designation VARCHAR(255),
            Email_ID VARCHAR(255),
            Phone_Number VARCHAR(50) UNIQUE,
            Location VARCHAR(100),
            Response_1 TEXT,
            Data_Insert_Time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            Last_Updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (Client_Name) REFERENCES tax_summit_master_data(Client_Name) 
                ON UPDATE CASCADE ON DELETE CASCADE,
            INDEX idx_client (Client_Name),
            INDEX idx_practice_head (Practice_Head),
            INDEX idx_partner (Partner)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS cfo_persons_analysis (
            id INT AUTO_INCREMENT PRIMARY KEY,
            Company_Name VARCHAR(255) NOT NULL,
            Practice_Head VARCHAR(100),
            Partner VARCHAR(100),
            Invite_Status VARCHAR(100),
            numInvitees VARCHAR(50),
            Response TEXT,
            Sector VARCHAR(100),
            numRegistrations VARCHAR(50),
            CFO_Name VARCHAR(255),
            Designation_2 VARCHAR(255),
            Email_ID_3 VARCHAR(255),
            Phone_Number_4 VARCHAR(50) UNIQUE,
            Location_6 VARCHAR(100),
            Response_7 TEXT,
            Data_Insert_Time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            Last_Updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (Company_Name) REFERENCES tax_summit_master_data(Client_Name) 
                ON UPDATE CASCADE ON DELETE CASCADE,
            INDEX idx_company (Company_Name),
            INDEX idx_practice_head (Practice_Head),
            INDEX idx_partner (Partner)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS other_persons_analysis (
            id INT AUTO_INCREMENT PRIMARY KEY,
            Company_Name VARCHAR(255) NOT NULL,
            Practice_Head VARCHAR(100),
            Partner VARCHAR(100),
            Invite_Status VARCHAR(100),
            numInvitees VARCHAR(50),
            Response TEXT,
            Sector VARCHAR(100),
            numRegistrations VARCHAR(50),
            Others VARCHAR(255),
            Designation_8 VARCHAR(255),
            Email_ID_9 VARCHAR(255),
            Phone_Number_10 VARCHAR(50) UNIQUE,
            Location_12 VARCHAR(100),
            Response_13 TEXT,
            Data_Insert_Time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            Last_Updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (Company_Name) REFERENCES tax_summit_master_data(Client_Name) 
                ON UPDATE CASCADE ON DELETE CASCADE,
            INDEX idx_company (Company_Name),
            INDEX idx_practice_head (Practice_Head),
            INDEX idx_partner (Partner)
        )
        """
    ]
    
    try:
        for table_sql in tables:
            cursor.execute(table_sql)
        connection.commit()
        print("✓ Analysis tables created (lowercase, optimized)")
        return True
    except Error as e:
        print(f"✗ Error creating analysis tables: {e}")
        return False
    finally:
        cursor.close()

def setup_railway_schema():
    """Main setup function"""
    print("\n" + "="*70)
    print("  🚂 RAILWAY DATABASE SETUP (ROW SIZE OPTIMIZED)")
    print("="*70 + "\n")
    
    connection = connect_to_railway()
    if not connection:
        return
    
    try:
        print("\n[Step 1] Creating master table (optimized for row size)...")
        if not create_master_table(connection):
            print("\n⚠️  Master table creation failed. Cannot proceed.")
            return
        
        print("\n[Step 2] Creating child tables...")
        if not create_child_tables(connection):
            print("\n⚠️  Warning: Child tables creation had issues")
        
        print("\n[Step 3] Creating analysis tables...")
        if not create_analysis_tables(connection):
            print("\n⚠️  Warning: Analysis tables creation had issues")
        
        print("\n" + "="*70)
        print("✅ RAILWAY DATABASE SETUP COMPLETE!")
        print("="*70)
        print("\n💡 Column Type Strategy:")
        print("   • Key fields (names, emails, phones): VARCHAR")
        print("   • Less critical fields: TEXT")
        print("   • This avoids the 65KB row size limit")
        print("\n📝 Next steps:")
        print("  1. Run: python test_railway.py")
        print("  2. Run: python auto_sync_to_railway.py --once --force")
        print()
        
    finally:
        if connection.is_connected():
            connection.close()
            print("✓ Connection closed\n")

if __name__ == "__main__":
    setup_railway_schema()