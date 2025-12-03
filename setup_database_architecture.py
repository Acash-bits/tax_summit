import pandas as pd
import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv

load_dotenv()

def connect_to_mysql(host, user, password, database):
    """Establish connection to MySQL database"""
    try:
        connection = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database
        )
        if connection.is_connected():
            print(f"✓ Connected to MySQL database: {database}")
            return connection
    except Error as e:
        print(f"✗ Error connecting to MySQL: {e}")
        return None

def create_child_tables(connection):
    """Create the 3 child tables with proper foreign keys and tracking columns"""
    cursor = connection.cursor()
    
    tables = [
        """
        CREATE TABLE IF NOT EXISTS Tax_Persons_details (
            S_No INT AUTO_INCREMENT PRIMARY KEY,
            Client_Name VARCHAR(255) NOT NULL,
            numRegistrations VARCHAR(255),
            Tax_Contact VARCHAR(255),
            Designation VARCHAR(255),
            Email_ID VARCHAR(255),
            Phone_Number VARCHAR(255) UNIQUE,
            Response_1 VARCHAR(255),
            Data_Insert_Time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            Contact_File_Created_Time_Stamp TIMESTAMP NULL,
            Contact_Created_Status TINYINT(1) DEFAULT 0,
            FOREIGN KEY (Client_Name) REFERENCES tax_summit_master_data(Client_Name) 
                ON UPDATE CASCADE ON DELETE CASCADE,
            INDEX idx_client (Client_Name),
            INDEX idx_contact_status (Contact_Created_Status),
            INDEX idx_created_time (Contact_File_Created_Time_Stamp)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS CFO_Persons_details (
            S_No INT AUTO_INCREMENT PRIMARY KEY,
            Company_Name VARCHAR(255) NOT NULL,
            numRegistrations VARCHAR(255),
            CFO_Name VARCHAR(255),
            Designation_2 VARCHAR(255),
            Email_ID_3 VARCHAR(255),
            Phone_Number_4 VARCHAR(255) UNIQUE,
            Response_7 VARCHAR(255),
            Data_Insert_Time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            Contact_File_Created_Time_Stamp TIMESTAMP NULL,
            Contact_Created_Status TINYINT(1) DEFAULT 0,
            FOREIGN KEY (Company_Name) REFERENCES tax_summit_master_data(Client_Name) 
                ON UPDATE CASCADE ON DELETE CASCADE,
            INDEX idx_company (Company_Name),
            INDEX idx_contact_status (Contact_Created_Status),
            INDEX idx_created_time (Contact_File_Created_Time_Stamp)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS Other_Persons_Details (
            S_No INT AUTO_INCREMENT PRIMARY KEY,
            Company_Name VARCHAR(255) NOT NULL,
            numRegistrations VARCHAR(255),
            Others VARCHAR(255),
            Designation_8 VARCHAR(255),
            Email_ID_9 VARCHAR(255),
            Phone_Number_10 VARCHAR(255) UNIQUE,
            Response_13 VARCHAR(255),
            Data_Insert_Time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            Contact_File_Created_Time_Stamp TIMESTAMP NULL,
            Contact_Created_Status TINYINT(1) DEFAULT 0,
            FOREIGN KEY (Company_Name) REFERENCES tax_summit_master_data(Client_Name) 
                ON UPDATE CASCADE ON DELETE CASCADE,
            INDEX idx_company_other (Company_Name),
            INDEX idx_contact_status (Contact_Created_Status),
            INDEX idx_created_time (Contact_File_Created_Time_Stamp)
        )
        """
    ]
    
    try:
        for table_sql in tables:
            cursor.execute(table_sql)
        connection.commit()
        print("✓ Child tables created successfully")
    except Error as e:
        print(f"✗ Error creating child tables: {e}")
    finally:
        cursor.close()

def create_triggers(connection):
    """Create triggers to auto-populate child tables from master table"""
    cursor = connection.cursor()
    
    # Drop existing triggers first
    drop_triggers = [
        "DROP TRIGGER IF EXISTS after_master_insert",
        "DROP TRIGGER IF EXISTS after_master_update"
    ]
    
    for drop_sql in drop_triggers:
        try:
            cursor.execute(drop_sql)
        except Error:
            pass
    
    # Trigger for INSERT - populates child tables when new row added to master
    insert_trigger = """
    CREATE TRIGGER after_master_insert
    AFTER INSERT ON tax_summit_master_data
    FOR EACH ROW
    BEGIN
        -- Insert into Tax_Persons_details (only if Phone_Number is not null and doesn't exist)
        IF NEW.Phone_Number IS NOT NULL AND NEW.Phone_Number != '' THEN
            INSERT IGNORE INTO Tax_Persons_details 
                (Client_Name, numRegistrations, Tax_Contact, Designation, Email_ID, Phone_Number, Response_1)
            VALUES 
                (NEW.Client_Name, NEW.numRegistrations, NEW.Tax_Contact, NEW.Designation, 
                 NEW.Email_ID, NEW.Phone_Number, NEW.Response_1);
        END IF;
        
        -- Insert into CFO_Persons_details (only if Phone_Number_4 is not null and doesn't exist)
        IF NEW.Phone_Number_4 IS NOT NULL AND NEW.Phone_Number_4 != '' THEN
            INSERT IGNORE INTO CFO_Persons_details 
                (Company_Name, numRegistrations, CFO_Name, Designation_2, Email_ID_3, Phone_Number_4, Response_7)
            VALUES 
                (NEW.Client_Name, NEW.numRegistrations, NEW.CFO_Name, NEW.Designation_2, 
                 NEW.Email_ID_3, NEW.Phone_Number_4, NEW.Response_7);
        END IF;
        
        -- Insert into Other_Persons_Details (only if Phone_Number_10 is not null and doesn't exist)
        IF NEW.Phone_Number_10 IS NOT NULL AND NEW.Phone_Number_10 != '' THEN
            INSERT IGNORE INTO Other_Persons_Details 
                (Company_Name, numRegistrations, Others, Designation_8, Email_ID_9, Phone_Number_10, Response_13)
            VALUES 
                (NEW.Client_Name, NEW.numRegistrations, NEW.Others, NEW.Designation_8, 
                 NEW.Email_ID_9, NEW.Phone_Number_10, NEW.Response_13);
        END IF;
    END
    """
    
    # Trigger for UPDATE - updates child tables when master table is updated
    update_trigger = """
    CREATE TRIGGER after_master_update
    AFTER UPDATE ON tax_summit_master_data
    FOR EACH ROW
    BEGIN
        -- Update Tax_Persons_details
        UPDATE Tax_Persons_details 
        SET 
            numRegistrations = NEW.numRegistrations,
            Tax_Contact = NEW.Tax_Contact,
            Designation = NEW.Designation,
            Email_ID = NEW.Email_ID,
            Response_1 = NEW.Response_1
        WHERE Phone_Number = NEW.Phone_Number;
        
        -- Update CFO_Persons_details
        UPDATE CFO_Persons_details 
        SET 
            numRegistrations = NEW.numRegistrations,
            CFO_Name = NEW.CFO_Name,
            Designation_2 = NEW.Designation_2,
            Email_ID_3 = NEW.Email_ID_3,
            Response_7 = NEW.Response_7
        WHERE Phone_Number_4 = NEW.Phone_Number_4;
        
        -- Update Other_Persons_Details
        UPDATE Other_Persons_Details 
        SET 
            numRegistrations = NEW.numRegistrations,
            Others = NEW.Others,
            Designation_8 = NEW.Designation_8,
            Email_ID_9 = NEW.Email_ID_9,
            Response_13 = NEW.Response_13
        WHERE Phone_Number_10 = NEW.Phone_Number_10;
    END
    """
    
    try:
        cursor.execute(insert_trigger)
        cursor.execute(update_trigger)
        connection.commit()
        print("✓ Triggers created successfully - Auto-sync enabled!")
    except Error as e:
        print(f"✗ Error creating triggers: {e}")
    finally:
        cursor.close()

def populate_child_tables_from_existing(connection):
    """Populate child tables from existing master table data"""
    cursor = connection.cursor()
    
    queries = [
        # Populate Tax_Persons_details
        """
        INSERT IGNORE INTO Tax_Persons_details 
            (Client_Name, numRegistrations, Tax_Contact, Designation, Email_ID, Phone_Number, Response_1)
        SELECT 
            Client_Name, numRegistrations, Tax_Contact, Designation, Email_ID, Phone_Number, Response_1
        FROM tax_summit_master_data
        WHERE Phone_Number IS NOT NULL AND Phone_Number != ''
        """,
        # Populate CFO_Persons_details
        """
        INSERT IGNORE INTO CFO_Persons_details 
            (Company_Name, numRegistrations, CFO_Name, Designation_2, Email_ID_3, Phone_Number_4, Response_7)
        SELECT 
            Client_Name, numRegistrations, CFO_Name, Designation_2, Email_ID_3, Phone_Number_4, Response_7
        FROM tax_summit_master_data
        WHERE Phone_Number_4 IS NOT NULL AND Phone_Number_4 != ''
        """,
        # Populate Other_Persons_Details
        """
        INSERT IGNORE INTO Other_Persons_Details 
            (Company_Name, numRegistrations, Others, Designation_8, Email_ID_9, Phone_Number_10, Response_13)
        SELECT 
            Client_Name, numRegistrations, Others, Designation_8, Email_ID_9, Phone_Number_10, Response_13
        FROM tax_summit_master_data
        WHERE Phone_Number_10 IS NOT NULL AND Phone_Number_10 != ''
        """
    ]
    
    try:
        for query in queries:
            cursor.execute(query)
        connection.commit()
        print("✓ Child tables populated from existing master data")
        
        # Show counts
        cursor.execute("SELECT COUNT(*) FROM Tax_Persons_details")
        tax_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM CFO_Persons_details")
        cfo_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM Other_Persons_Details")
        other_count = cursor.fetchone()[0]
        
        print(f"  → Tax_Persons_details: {tax_count} records")
        print(f"  → CFO_Persons_details: {cfo_count} records")
        print(f"  → Other_Persons_Details: {other_count} records")
        
    except Error as e:
        print(f"✗ Error populating child tables: {e}")
    finally:
        cursor.close()

def get_pending_contacts_count(connection):
    """Get count of contacts that haven't been created yet"""
    cursor = connection.cursor()
    
    try:
        cursor.execute("SELECT COUNT(*) FROM Tax_Persons_details WHERE Contact_Created_Status = 0")
        tax_pending = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM CFO_Persons_details WHERE Contact_Created_Status = 0")
        cfo_pending = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM Other_Persons_Details WHERE Contact_Created_Status = 0")
        other_pending = cursor.fetchone()[0]
        
        return tax_pending, cfo_pending, other_pending
    finally:
        cursor.close()

def setup_database_architecture():
    """Main function to set up the complete database architecture"""
    print("\n" + "="*60)
    print("  SETTING UP MULTI-TABLE AUTO-SYNC ARCHITECTURE")
    print("="*60 + "\n")
    
    # Connect to database
    connection = connect_to_mysql(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS"),
        database=os.getenv("DB_NAME")
    )
    
    if not connection:
        return
    
    try:
        # Step 1: Create child tables
        print("\n[Step 1] Creating child tables...")
        create_child_tables(connection)
        
        # Step 2: Create triggers for auto-sync
        print("\n[Step 2] Setting up auto-sync triggers...")
        create_triggers(connection)
        
        # Step 3: Populate from existing data
        print("\n[Step 3] Populating child tables from existing master data...")
        populate_child_tables_from_existing(connection)
        
        # Step 4: Show pending contacts
        print("\n[Step 4] Checking contact creation status...")
        tax_pending, cfo_pending, other_pending = get_pending_contacts_count(connection)
        
        print("\n" + "="*60)
        print("  ✓ SETUP COMPLETE!")
        print("="*60)
        print("\nYour database architecture is now ready:")
        print("  → 3 child tables created with foreign keys")
        print("  → Phone number uniqueness enforced")
        print("  → Auto-sync triggers activated")
        print("  → Existing data migrated")
        print("  → Tracking columns added:")
        print("    • Data_Insert_Time (auto-set on insert)")
        print("    • Contact_File_Created_Time_Stamp (for vCard generation)")
        print("    • Contact_Created_Status (0 = pending, 1 = created)")
        print("\nPending Contacts to be Created:")
        print(f"  → Tax Persons: {tax_pending}")
        print(f"  → CFO Persons: {cfo_pending}")
        print(f"  → Other Persons: {other_pending}")
        print(f"  → Total: {tax_pending + cfo_pending + other_pending}")
        print("\nFrom now on, any INSERT/UPDATE to master table will")
        print("automatically sync to the child tables! 🚀")
        
    finally:
        if connection.is_connected():
            connection.close()
            print("\n✓ MySQL connection closed\n")

if __name__ == "__main__":
    setup_database_architecture()