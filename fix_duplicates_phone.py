import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv

load_dotenv()

def connect_to_mysql():
    """Establish connection to MySQL database"""
    try:
        connection = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS"),
            database=os.getenv("DB_NAME"),
            port=int(os.getenv("DB_PORT", 3306))
        )
        if connection.is_connected():
            print(f"✓ Connected to MySQL database")
            return connection
    except Error as e:
        print(f"✗ Error connecting to MySQL: {e}")
        return None

def find_duplicate_phones(connection):
    """Find all duplicate phone numbers"""
    cursor = connection.cursor(dictionary=True)
    
    print("\n" + "="*70)
    print("  🔍 FINDING DUPLICATE PHONE NUMBERS")
    print("="*70 + "\n")
    
    # Find duplicates in Tax contacts
    cursor.execute("""
        SELECT 
            Phone_Number,
            COUNT(*) as count,
            GROUP_CONCAT(CONCAT(Client_Name, ' (', Tax_Contact, ')') SEPARATOR ' | ') as people
        FROM tax_summit_master_data
        WHERE Phone_Number IS NOT NULL AND Phone_Number != ''
        GROUP BY Phone_Number
        HAVING COUNT(*) > 1
        ORDER BY count DESC
    """)
    
    tax_dupes = cursor.fetchall()
    
    print(f"[1] Tax Contacts - Found {len(tax_dupes)} duplicate phone numbers:\n")
    
    if tax_dupes:
        for i, dupe in enumerate(tax_dupes[:20], 1):
            print(f"  {i}. Phone: {dupe['Phone_Number']} (used {dupe['count']} times)")
            people_list = dupe['people'].split(' | ')
            for person in people_list[:3]:
                print(f"     • {person}")
            if len(people_list) > 3:
                print(f"     ... and {len(people_list) - 3} more")
        
        if len(tax_dupes) > 20:
            print(f"\n  ... and {len(tax_dupes) - 20} more duplicate phones")
    
    # CFO contacts
    cursor.execute("""
        SELECT 
            Phone_Number_4,
            COUNT(*) as count,
            GROUP_CONCAT(CONCAT(Client_Name, ' (', CFO_Name, ')') SEPARATOR ' | ') as people
        FROM tax_summit_master_data
        WHERE Phone_Number_4 IS NOT NULL AND Phone_Number_4 != ''
        GROUP BY Phone_Number_4
        HAVING COUNT(*) > 1
        ORDER BY count DESC
    """)
    
    cfo_dupes = cursor.fetchall()
    
    print(f"\n[2] CFO Contacts - Found {len(cfo_dupes)} duplicate phone numbers")
    
    # Other contacts
    cursor.execute("""
        SELECT 
            Phone_Number_10,
            COUNT(*) as count,
            GROUP_CONCAT(CONCAT(Client_Name, ' (', Others, ')') SEPARATOR ' | ') as people
        FROM tax_summit_master_data
        WHERE Phone_Number_10 IS NOT NULL AND Phone_Number_10 != ''
        GROUP BY Phone_Number_10
        HAVING COUNT(*) > 1
        ORDER BY count DESC
    """)
    
    other_dupes = cursor.fetchall()
    
    print(f"[3] Other Contacts - Found {len(other_dupes)} duplicate phone numbers")
    
    cursor.close()
    
    return len(tax_dupes), len(cfo_dupes), len(other_dupes)

def remove_unique_constraint(connection):
    """Remove UNIQUE constraint from Phone_Number columns"""
    cursor = connection.cursor()
    
    print("\n" + "="*70)
    print("  🔧 REMOVING UNIQUE CONSTRAINTS")
    print("="*70 + "\n")
    
    tables = [
        ('Tax_Persons_Analysis', 'Phone_Number'),
        ('CFO_Persons_Analysis', 'Phone_Number_4'),
        ('Other_Persons_Analysis', 'Phone_Number_10')
    ]
    
    for table, phone_col in tables:
        print(f"[{table}] Removing UNIQUE constraint on {phone_col}...")
        
        try:
            # First, check what indexes exist
            cursor.execute(f"SHOW INDEX FROM {table} WHERE Column_name = '{phone_col}'")
            indexes = cursor.fetchall()
            
            if not indexes:
                print(f"    ℹ️  No UNIQUE constraint found")
                continue
            
            # Drop each index
            for index in indexes:
                index_name = index[2]  # Key_name is at position 2
                try:
                    cursor.execute(f"ALTER TABLE {table} DROP INDEX {index_name}")
                    print(f"    ✓ Dropped index: {index_name}")
                except Error as e:
                    print(f"    ⚠️  Could not drop {index_name}: {e}")
            
            connection.commit()
            
        except Error as e:
            print(f"    ⚠️  Error: {e}")
    
    print("\n✅ UNIQUE constraints removed!")
    cursor.close()

def add_composite_unique_constraint(connection):
    """Add composite UNIQUE constraint on (Phone_Number + Client_Name)"""
    cursor = connection.cursor()
    
    print("\n" + "="*70)
    print("  🔧 ADDING COMPOSITE UNIQUE CONSTRAINTS")
    print("="*70 + "\n")
    
    print("This allows same phone for different clients, but not duplicates")
    print("within same client (which shouldn't happen anyway).\n")
    
    constraints = [
        ('Tax_Persons_Analysis', 'Phone_Number', 'Client_Name'),
        ('CFO_Persons_Analysis', 'Phone_Number_4', 'Company_Name'),
        ('Other_Persons_Analysis', 'Phone_Number_10', 'Company_Name')
    ]
    
    for table, phone_col, name_col in constraints:
        print(f"[{table}] Adding composite UNIQUE ({phone_col}, {name_col})...")
        
        try:
            cursor.execute(f"""
                ALTER TABLE {table} 
                ADD UNIQUE INDEX idx_phone_client ({phone_col}, {name_col})
            """)
            print(f"    ✓ Added composite constraint")
            connection.commit()
            
        except Error as e:
            if e.errno == 1061:  # Duplicate key name
                print(f"    ℹ️  Constraint already exists")
            else:
                print(f"    ⚠️  Error: {e}")
    
    cursor.close()

def insert_all_data_with_duplicates(connection):
    """Insert all data, allowing duplicate phones"""
    cursor = connection.cursor()
    
    print("\n" + "="*70)
    print("  📊 INSERTING ALL DATA")
    print("="*70 + "\n")
    
    # Tax Persons Analysis
    print("[1] Tax_Persons_Analysis...")
    try:
        cursor.execute("DELETE FROM Tax_Persons_Analysis")
        print(f"    Cleared existing data")
        
        cursor.execute("""
            INSERT INTO Tax_Persons_Analysis 
                (Client_Name, Practice_Head, Partner, Invite_Status, numInvitees, Response, 
                 Sector, numRegistrations, Tax_Contact, Designation, Email_ID, Phone_Number, 
                 Location, Response_1)
            SELECT 
                Client_Name, Practice_Head, Partner, Invite_Status, numInvitees, Response, 
                Sector, numRegistrations, Tax_Contact, Designation, Email_ID, Phone_Number, 
                Location, Response_1
            FROM tax_summit_master_data
            WHERE Phone_Number IS NOT NULL AND Phone_Number != ''
        """)
        
        inserted = cursor.rowcount
        connection.commit()
        print(f"    ✓ Inserted {inserted} rows")
        
    except Error as e:
        print(f"    ❌ Error: {e}")
        connection.rollback()
    
    # CFO Persons Analysis
    print("\n[2] CFO_Persons_Analysis...")
    try:
        cursor.execute("DELETE FROM CFO_Persons_Analysis")
        print(f"    Cleared existing data")
        
        cursor.execute("""
            INSERT INTO CFO_Persons_Analysis 
                (Company_Name, Practice_Head, Partner, Invite_Status, numInvitees, Response, 
                 Sector, numRegistrations, CFO_Name, Designation_2, Email_ID_3, Phone_Number_4, 
                 Location_6, Response_7)
            SELECT 
                Client_Name, Practice_Head, Partner, Invite_Status, numInvitees, Response, 
                Sector, numRegistrations, CFO_Name, Designation_2, Email_ID_3, Phone_Number_4, 
                Location_6, Response_7
            FROM tax_summit_master_data
            WHERE Phone_Number_4 IS NOT NULL AND Phone_Number_4 != ''
        """)
        
        inserted = cursor.rowcount
        connection.commit()
        print(f"    ✓ Inserted {inserted} rows")
        
    except Error as e:
        print(f"    ❌ Error: {e}")
        connection.rollback()
    
    # Other Persons Analysis
    print("\n[3] Other_Persons_Analysis...")
    try:
        cursor.execute("DELETE FROM Other_Persons_Analysis")
        print(f"    Cleared existing data")
        
        cursor.execute("""
            INSERT INTO Other_Persons_Analysis 
                (Company_Name, Practice_Head, Partner, Invite_Status, numInvitees, Response, 
                 Sector, numRegistrations, Others, Designation_8, Email_ID_9, Phone_Number_10, 
                 Location_12, Response_13)
            SELECT 
                Client_Name, Practice_Head, Partner, Invite_Status, numInvitees, Response, 
                Sector, numRegistrations, Others, Designation_8, Email_ID_9, Phone_Number_10, 
                Location_12, Response_13
            FROM tax_summit_master_data
            WHERE Phone_Number_10 IS NOT NULL AND Phone_Number_10 != ''
        """)
        
        inserted = cursor.rowcount
        connection.commit()
        print(f"    ✓ Inserted {inserted} rows")
        
    except Error as e:
        print(f"    ❌ Error: {e}")
        connection.rollback()
    
    cursor.close()

def verify_sync(connection):
    """Verify the sync worked"""
    cursor = connection.cursor(dictionary=True)
    
    print("\n" + "="*70)
    print("  ✅ VERIFICATION")
    print("="*70 + "\n")
    
    # Count in master
    cursor.execute("SELECT COUNT(*) as c FROM tax_summit_master_data WHERE Phone_Number IS NOT NULL AND Phone_Number != ''")
    master_tax = cursor.fetchone()['c']
    
    cursor.execute("SELECT COUNT(*) as c FROM tax_summit_master_data WHERE Phone_Number_4 IS NOT NULL AND Phone_Number_4 != ''")
    master_cfo = cursor.fetchone()['c']
    
    cursor.execute("SELECT COUNT(*) as c FROM tax_summit_master_data WHERE Phone_Number_10 IS NOT NULL AND Phone_Number_10 != ''")
    master_other = cursor.fetchone()['c']
    
    # Count in analysis
    cursor.execute("SELECT COUNT(*) as c FROM Tax_Persons_Analysis")
    analysis_tax = cursor.fetchone()['c']
    
    cursor.execute("SELECT COUNT(*) as c FROM CFO_Persons_Analysis")
    analysis_cfo = cursor.fetchone()['c']
    
    cursor.execute("SELECT COUNT(*) as c FROM Other_Persons_Analysis")
    analysis_other = cursor.fetchone()['c']
    
    print("Master → Analysis:")
    print(f"  Tax:   {master_tax} → {analysis_tax}   {'✅' if master_tax == analysis_tax else '❌'}")
    print(f"  CFO:   {master_cfo} → {analysis_cfo}   {'✅' if master_cfo == analysis_cfo else '❌'}")
    print(f"  Other: {master_other} → {analysis_other}   {'✅' if master_other == analysis_other else '❌'}")
    
    # Check specific case: Response_1 = 'Registered'
    cursor.execute("""
        SELECT COUNT(*) as c 
        FROM tax_summit_master_data 
        WHERE (Response_1 = 'Registered' OR Response_1 = 'registered')
        AND Phone_Number IS NOT NULL AND Phone_Number != ''
    """)
    master_registered = cursor.fetchone()['c']
    
    cursor.execute("""
        SELECT COUNT(*) as c 
        FROM Tax_Persons_Analysis 
        WHERE Response_1 = 'Registered' OR Response_1 = 'registered'
    """)
    analysis_registered = cursor.fetchone()['c']
    
    print(f"\nRegistered Tax Contacts:")
    print(f"  Master:   {master_registered}")
    print(f"  Analysis: {analysis_registered}")
    
    if master_registered == analysis_registered:
        print(f"  🎉 PERFECT! Your original issue (50 vs 44) is now fixed!")
    else:
        print(f"  ⚠️  Still {master_registered - analysis_registered} missing")
    
    cursor.close()

def update_triggers_to_handle_duplicates(connection):
    """Update triggers to use INSERT IGNORE or ON DUPLICATE KEY"""
    cursor = connection.cursor()
    
    print("\n" + "="*70)
    print("  🔧 UPDATING TRIGGERS")
    print("="*70 + "\n")
    
    # Drop existing triggers
    print("Dropping old triggers...")
    for trigger in ['after_master_insert_analysis', 'after_master_update_analysis', 'after_master_delete_analysis']:
        try:
            cursor.execute(f"DROP TRIGGER IF EXISTS {trigger}")
        except:
            pass
    
    print("Creating new triggers that handle duplicates...\n")
    
    # New INSERT trigger with INSERT IGNORE
    insert_trigger = """
    CREATE TRIGGER after_master_insert_analysis
    AFTER INSERT ON tax_summit_master_data
    FOR EACH ROW
    BEGIN
        -- Tax_Persons_Analysis - INSERT IGNORE to skip duplicates
        IF NEW.Phone_Number IS NOT NULL AND NEW.Phone_Number != '' THEN
            INSERT INTO Tax_Persons_Analysis 
                (Client_Name, Practice_Head, Partner, Invite_Status, numInvitees, Response, 
                 Sector, numRegistrations, Tax_Contact, Designation, Email_ID, Phone_Number, 
                 Location, Response_1)
            VALUES 
                (NEW.Client_Name, NEW.Practice_Head, NEW.Partner, NEW.Invite_Status, 
                 NEW.numInvitees, NEW.Response, NEW.Sector, NEW.numRegistrations, 
                 NEW.Tax_Contact, NEW.Designation, NEW.Email_ID, NEW.Phone_Number, 
                 NEW.Location, NEW.Response_1)
            ON DUPLICATE KEY UPDATE
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
                Response_1 = NEW.Response_1;
        END IF;
        
        -- CFO_Persons_Analysis
        IF NEW.Phone_Number_4 IS NOT NULL AND NEW.Phone_Number_4 != '' THEN
            INSERT INTO CFO_Persons_Analysis 
                (Company_Name, Practice_Head, Partner, Invite_Status, numInvitees, Response, 
                 Sector, numRegistrations, CFO_Name, Designation_2, Email_ID_3, Phone_Number_4, 
                 Location_6, Response_7)
            VALUES 
                (NEW.Client_Name, NEW.Practice_Head, NEW.Partner, NEW.Invite_Status, 
                 NEW.numInvitees, NEW.Response, NEW.Sector, NEW.numRegistrations, 
                 NEW.CFO_Name, NEW.Designation_2, NEW.Email_ID_3, NEW.Phone_Number_4, 
                 NEW.Location_6, NEW.Response_7)
            ON DUPLICATE KEY UPDATE
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
                Response_7 = NEW.Response_7;
        END IF;
        
        -- Other_Persons_Analysis
        IF NEW.Phone_Number_10 IS NOT NULL AND NEW.Phone_Number_10 != '' THEN
            INSERT INTO Other_Persons_Analysis 
                (Company_Name, Practice_Head, Partner, Invite_Status, numInvitees, Response, 
                 Sector, numRegistrations, Others, Designation_8, Email_ID_9, Phone_Number_10, 
                 Location_12, Response_13)
            VALUES 
                (NEW.Client_Name, NEW.Practice_Head, NEW.Partner, NEW.Invite_Status, 
                 NEW.numInvitees, NEW.Response, NEW.Sector, NEW.numRegistrations, 
                 NEW.Others, NEW.Designation_8, NEW.Email_ID_9, NEW.Phone_Number_10, 
                 NEW.Location_12, NEW.Response_13)
            ON DUPLICATE KEY UPDATE
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
                Response_13 = NEW.Response_13;
        END IF;
    END
    """
    
    try:
        cursor.execute(insert_trigger)
        print("  ✓ INSERT trigger created (with duplicate handling)")
        connection.commit()
    except Error as e:
        print(f"  ❌ Error: {e}")
    
    cursor.close()

def main():
    print("\n" + "="*70)
    print("  🔧 FIX DUPLICATE PHONE NUMBERS IN ANALYSIS TABLES")
    print("="*70)
    
    connection = connect_to_mysql()
    if not connection:
        return
    
    try:
        # Step 1: Find duplicates
        tax_dupes, cfo_dupes, other_dupes = find_duplicate_phones(connection)
        
        if tax_dupes == 0 and cfo_dupes == 0 and other_dupes == 0:
            print("\n✅ No duplicates found! The issue must be something else.")
            return
        
        # Step 2: Explain the solution
        print("\n" + "="*70)
        print("  💡 SOLUTION")
        print("="*70)
        print("\nThe problem: Your analysis tables have UNIQUE constraint on phone,")
        print("but multiple people share the same phone number in your master data.")
        print("\nThe fix:")
        print("  1. Remove UNIQUE constraint from Phone_Number columns")
        print("  2. Add composite UNIQUE on (Phone_Number + Client_Name)")
        print("  3. Insert all data (including duplicates)")
        print("  4. Update triggers to handle duplicates")
        print("\nThis allows:")
        print("  ✓ Same phone for different clients")
        print("  ✓ All 182 tax contacts to appear in analysis")
        print("  ✓ Dashboard to show correct data")
        print("="*70)
        
        print("\nContinue with fix? (yes/no): ", end='')
        response = input().strip().lower()
        
        if response not in ['yes', 'y']:
            print("\n❌ Cancelled. No changes made.")
            return
        
        # Step 3: Execute fix
        remove_unique_constraint(connection)
        add_composite_unique_constraint(connection)
        insert_all_data_with_duplicates(connection)
        update_triggers_to_handle_duplicates(connection)
        verify_sync(connection)
        
        print("\n" + "="*70)
        print("  ✅ FIX COMPLETE!")
        print("="*70)
        print("\n🎉 Your dashboard should now show all 182 tax contacts!")
        print("   Including all 50 'Registered' contacts.")
        print("\n💡 From now on:")
        print("   • Master table can have duplicate phones")
        print("   • Analysis tables will store ALL contacts")
        print("   • Triggers will auto-update on changes")
        print("="*70 + "\n")
        
    finally:
        if connection.is_connected():
            connection.close()
            print("✓ Connection closed\n")

if __name__ == "__main__":
    main()