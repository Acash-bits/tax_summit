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

def create_analysis_tables(connection):
    """Create the 3 analysis tables with all required columns"""
    cursor = connection.cursor()
    
    tables = [
        """
        CREATE TABLE IF NOT EXISTS Tax_Persons_Analysis (
            S_No INT AUTO_INCREMENT PRIMARY KEY,
            Client_Name VARCHAR(255) NOT NULL,
            Practice_Head VARCHAR(255),
            Partner VARCHAR(255),
            Invite_Status VARCHAR(255),
            numInvitees VARCHAR(255),
            Response VARCHAR(255),
            Sector VARCHAR(255),
            numRegistrations VARCHAR(255),
            Tax_Contact VARCHAR(255),
            Designation VARCHAR(255),
            Email_ID VARCHAR(255),
            Phone_Number VARCHAR(255) UNIQUE,
            Location VARCHAR(255),
            Response_1 VARCHAR(255),
            Data_Insert_Time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            Last_Updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (Client_Name) REFERENCES tax_summit_master_data(Client_Name) 
                ON UPDATE CASCADE ON DELETE CASCADE,
            INDEX idx_client (Client_Name),
            INDEX idx_practice_head (Practice_Head),
            INDEX idx_partner (Partner),
            INDEX idx_invite_status (Invite_Status),
            INDEX idx_sector (Sector),
            INDEX idx_response (Response)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS CFO_Persons_Analysis (
            S_No INT AUTO_INCREMENT PRIMARY KEY,
            Company_Name VARCHAR(255) NOT NULL,
            Practice_Head VARCHAR(255),
            Partner VARCHAR(255),
            Invite_Status VARCHAR(255),
            numInvitees VARCHAR(255),
            Response VARCHAR(255),
            Sector VARCHAR(255),
            numRegistrations VARCHAR(255),
            CFO_Name VARCHAR(255),
            Designation_2 VARCHAR(255),
            Email_ID_3 VARCHAR(255),
            Phone_Number_4 VARCHAR(255) UNIQUE,
            Location_6 VARCHAR(255),
            Response_7 VARCHAR(255),
            Data_Insert_Time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            Last_Updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (Company_Name) REFERENCES tax_summit_master_data(Client_Name) 
                ON UPDATE CASCADE ON DELETE CASCADE,
            INDEX idx_company (Company_Name),
            INDEX idx_practice_head (Practice_Head),
            INDEX idx_partner (Partner),
            INDEX idx_invite_status (Invite_Status),
            INDEX idx_sector (Sector),
            INDEX idx_response (Response)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS Other_Persons_Analysis (
            S_No INT AUTO_INCREMENT PRIMARY KEY,
            Company_Name VARCHAR(255) NOT NULL,
            Practice_Head VARCHAR(255),
            Partner VARCHAR(255),
            Invite_Status VARCHAR(255),
            numInvitees VARCHAR(255),
            Response VARCHAR(255),
            Sector VARCHAR(255),
            numRegistrations VARCHAR(255),
            Others VARCHAR(255),
            Designation_8 VARCHAR(255),
            Email_ID_9 VARCHAR(255),
            Phone_Number_10 VARCHAR(255) UNIQUE,
            Location_12 VARCHAR(255),
            Response_13 VARCHAR(255),
            Data_Insert_Time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            Last_Updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (Company_Name) REFERENCES tax_summit_master_data(Client_Name) 
                ON UPDATE CASCADE ON DELETE CASCADE,
            INDEX idx_company_other (Company_Name),
            INDEX idx_practice_head (Practice_Head),
            INDEX idx_partner (Partner),
            INDEX idx_invite_status (Invite_Status),
            INDEX idx_sector (Sector),
            INDEX idx_response (Response)
        )
        """
    ]
    
    try:
        for table_sql in tables:
            cursor.execute(table_sql)
        connection.commit()
        print("✓ Analysis tables created successfully")
    except Error as e:
        print(f"✗ Error creating analysis tables: {e}")
    finally:
        cursor.close()

def create_analysis_triggers(connection):
    """Create triggers to auto-populate analysis tables from master table"""
    cursor = connection.cursor()
    
    # Drop existing triggers first
    drop_triggers = [
        "DROP TRIGGER IF EXISTS after_master_insert_analysis",
        "DROP TRIGGER IF EXISTS after_master_update_analysis"
    ]
    
    for drop_sql in drop_triggers:
        try:
            cursor.execute(drop_sql)
        except Error:
            pass
    
    # Trigger for INSERT - populates analysis tables when new row added to master
    insert_trigger = """
    CREATE TRIGGER after_master_insert_analysis
    AFTER INSERT ON tax_summit_master_data
    FOR EACH ROW
    BEGIN
        -- Insert into Tax_Persons_Analysis (only if Phone_Number is not null and doesn't exist)
        IF NEW.Phone_Number IS NOT NULL AND NEW.Phone_Number != '' THEN
            INSERT IGNORE INTO Tax_Persons_Analysis 
                (Client_Name, Practice_Head, Partner, Invite_Status, numInvitees, Response, 
                 Sector, numRegistrations, Tax_Contact, Designation, Email_ID, Phone_Number, 
                 Location, Response_1)
            VALUES 
                (NEW.Client_Name, NEW.Practice_Head, NEW.Partner, NEW.Invite_Status, 
                 NEW.numInvitees, NEW.Response, NEW.Sector, NEW.numRegistrations, 
                 NEW.Tax_Contact, NEW.Designation, NEW.Email_ID, NEW.Phone_Number, 
                 NEW.Location, NEW.Response_1);
        END IF;
        
        -- Insert into CFO_Persons_Analysis (only if Phone_Number_4 is not null and doesn't exist)
        IF NEW.Phone_Number_4 IS NOT NULL AND NEW.Phone_Number_4 != '' THEN
            INSERT IGNORE INTO CFO_Persons_Analysis 
                (Company_Name, Practice_Head, Partner, Invite_Status, numInvitees, Response, 
                 Sector, numRegistrations, CFO_Name, Designation_2, Email_ID_3, Phone_Number_4, 
                 Location_6, Response_7)
            VALUES 
                (NEW.Client_Name, NEW.Practice_Head, NEW.Partner, NEW.Invite_Status, 
                 NEW.numInvitees, NEW.Response, NEW.Sector, NEW.numRegistrations, 
                 NEW.CFO_Name, NEW.Designation_2, NEW.Email_ID_3, NEW.Phone_Number_4, 
                 NEW.Location_6, NEW.Response_7);
        END IF;
        
        -- Insert into Other_Persons_Analysis (only if Phone_Number_10 is not null and doesn't exist)
        IF NEW.Phone_Number_10 IS NOT NULL AND NEW.Phone_Number_10 != '' THEN
            INSERT IGNORE INTO Other_Persons_Analysis 
                (Company_Name, Practice_Head, Partner, Invite_Status, numInvitees, Response, 
                 Sector, numRegistrations, Others, Designation_8, Email_ID_9, Phone_Number_10, 
                 Location_12, Response_13)
            VALUES 
                (NEW.Client_Name, NEW.Practice_Head, NEW.Partner, NEW.Invite_Status, 
                 NEW.numInvitees, NEW.Response, NEW.Sector, NEW.numRegistrations, 
                 NEW.Others, NEW.Designation_8, NEW.Email_ID_9, NEW.Phone_Number_10, 
                 NEW.Location_12, NEW.Response_13);
        END IF;
    END
    """
    
    # Trigger for UPDATE - updates analysis tables when master table is updated
    update_trigger = """
    CREATE TRIGGER after_master_update_analysis
    AFTER UPDATE ON tax_summit_master_data
    FOR EACH ROW
    BEGIN
        -- Update Tax_Persons_Analysis
        UPDATE Tax_Persons_Analysis 
        SET 
            Practice_Head = NEW.Practice_Head,
            Partner = NEW.Partner,
            Invite_Status = NEW.Invite_Status,
            numInvitees = NEW.numInvitees,
            Response = NEW.Response,
            Sector = NEW.Sector,
            numRegistrations = NEW.numRegistrations,
            Tax_Contact = NEW.Tax_Contact,
            Designation = NEW.Designation,
            Email_ID = NEW.Email_ID,
            Location = NEW.Location,
            Response_1 = NEW.Response_1
        WHERE Phone_Number = NEW.Phone_Number;
        
        -- Update CFO_Persons_Analysis
        UPDATE CFO_Persons_Analysis 
        SET 
            Practice_Head = NEW.Practice_Head,
            Partner = NEW.Partner,
            Invite_Status = NEW.Invite_Status,
            numInvitees = NEW.numInvitees,
            Response = NEW.Response,
            Sector = NEW.Sector,
            numRegistrations = NEW.numRegistrations,
            CFO_Name = NEW.CFO_Name,
            Designation_2 = NEW.Designation_2,
            Email_ID_3 = NEW.Email_ID_3,
            Location_6 = NEW.Location_6,
            Response_7 = NEW.Response_7
        WHERE Phone_Number_4 = NEW.Phone_Number_4;
        
        -- Update Other_Persons_Analysis
        UPDATE Other_Persons_Analysis 
        SET 
            Practice_Head = NEW.Practice_Head,
            Partner = NEW.Partner,
            Invite_Status = NEW.Invite_Status,
            numInvitees = NEW.numInvitees,
            Response = NEW.Response,
            Sector = NEW.Sector,
            numRegistrations = NEW.numRegistrations,
            Others = NEW.Others,
            Designation_8 = NEW.Designation_8,
            Email_ID_9 = NEW.Email_ID_9,
            Location_12 = NEW.Location_12,
            Response_13 = NEW.Response_13
        WHERE Phone_Number_10 = NEW.Phone_Number_10;
    END
    """
    
    try:
        cursor.execute(insert_trigger)
        cursor.execute(update_trigger)
        connection.commit()
        print("✓ Analysis triggers created successfully - Auto-sync enabled!")
    except Error as e:
        print(f"✗ Error creating analysis triggers: {e}")
    finally:
        cursor.close()

def populate_analysis_tables_from_existing(connection):
    """Populate analysis tables from existing master table data"""
    cursor = connection.cursor()
    
    queries = [
        # Populate Tax_Persons_Analysis
        """
        INSERT IGNORE INTO Tax_Persons_Analysis 
            (Client_Name, Practice_Head, Partner, Invite_Status, numInvitees, Response, 
             Sector, numRegistrations, Tax_Contact, Designation, Email_ID, Phone_Number, 
             Location, Response_1)
        SELECT 
            Client_Name, Practice_Head, Partner, Invite_Status, numInvitees, Response, 
            Sector, numRegistrations, Tax_Contact, Designation, Email_ID, Phone_Number, 
            Location, Response_1
        FROM tax_summit_master_data
        WHERE Phone_Number IS NOT NULL AND Phone_Number != ''
        """,
        # Populate CFO_Persons_Analysis
        """
        INSERT IGNORE INTO CFO_Persons_Analysis 
            (Company_Name, Practice_Head, Partner, Invite_Status, numInvitees, Response, 
             Sector, numRegistrations, CFO_Name, Designation_2, Email_ID_3, Phone_Number_4, 
             Location_6, Response_7)
        SELECT 
            Client_Name, Practice_Head, Partner, Invite_Status, numInvitees, Response, 
            Sector, numRegistrations, CFO_Name, Designation_2, Email_ID_3, Phone_Number_4, 
            Location_6, Response_7
        FROM tax_summit_master_data
        WHERE Phone_Number_4 IS NOT NULL AND Phone_Number_4 != ''
        """,
        # Populate Other_Persons_Analysis
        """
        INSERT IGNORE INTO Other_Persons_Analysis 
            (Company_Name, Practice_Head, Partner, Invite_Status, numInvitees, Response, 
             Sector, numRegistrations, Others, Designation_8, Email_ID_9, Phone_Number_10, 
             Location_12, Response_13)
        SELECT 
            Client_Name, Practice_Head, Partner, Invite_Status, numInvitees, Response, 
            Sector, numRegistrations, Others, Designation_8, Email_ID_9, Phone_Number_10, 
            Location_12, Response_13
        FROM tax_summit_master_data
        WHERE Phone_Number_10 IS NOT NULL AND Phone_Number_10 != ''
        """
    ]
    
    try:
        for query in queries:
            cursor.execute(query)
        connection.commit()
        print("✓ Analysis tables populated from existing master data")
        
        # Show counts
        cursor.execute("SELECT COUNT(*) FROM Tax_Persons_Analysis")
        tax_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM CFO_Persons_Analysis")
        cfo_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM Other_Persons_Analysis")
        other_count = cursor.fetchone()[0]
        
        print(f"  → Tax_Persons_Analysis: {tax_count} records")
        print(f"  → CFO_Persons_Analysis: {cfo_count} records")
        print(f"  → Other_Persons_Analysis: {other_count} records")
        
    except Error as e:
        print(f"✗ Error populating analysis tables: {e}")
    finally:
        cursor.close()

def setup_analysis_architecture():
    """Main function to set up the complete analysis architecture"""
    print("\n" + "="*70)
    print("  SETTING UP ANALYSIS TABLES WITH AUTO-SYNC")
    print("="*70 + "\n")
    
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
        # Step 1: Create analysis tables
        print("[Step 1] Creating analysis tables...")
        create_analysis_tables(connection)
        
        # Step 2: Create triggers for auto-sync
        print("\n[Step 2] Setting up auto-sync triggers...")
        create_analysis_triggers(connection)
        
        # Step 3: Populate from existing data
        print("\n[Step 3] Populating analysis tables from existing master data...")
        populate_analysis_tables_from_existing(connection)
        
        print("\n" + "="*70)
        print("  ✓ ANALYSIS ARCHITECTURE COMPLETE!")
        print("="*70)
        print("\nYour analysis tables are ready with:")
        print("\n📊 Common Fields (All Tables):")
        print("  → Practice_Head, Partner, Invite_Status")
        print("  → numInvitees, Response, Sector")
        print("  → numRegistrations")
        print("\n👥 Person-Specific Fields:")
        print("  → Tax_Persons_Analysis: Tax_Contact, Designation, Email_ID, Phone, Location")
        print("  → CFO_Persons_Analysis: CFO_Name, Designation_2, Email_ID_3, Phone_4, Location_6")
        print("  → Other_Persons_Analysis: Others, Designation_8, Email_ID_9, Phone_10, Location_12")
        print("\n⚡ Auto-Sync Features:")
        print("  → Phone number uniqueness enforced")
        print("  → Foreign keys to master table (Client_Name)")
        print("  → Auto-insert on new master records")
        print("  → Auto-update on master changes")
        print("  → Indexed for fast analytics queries")
        print("\n🎯 Ready for analysis, graphs, and dashboards!")
        
    finally:
        if connection.is_connected():
            connection.close()
            print("\n✓ MySQL connection closed\n")

if __name__ == "__main__":
    setup_analysis_architecture()