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

def drop_existing_triggers(connection):
    """Drop all existing analysis triggers"""
    cursor = connection.cursor()
    
    print("\n[Step 1] Dropping old triggers...")
    
    triggers = [
        "after_master_insert_analysis",
        "after_master_update_analysis",
        "after_master_delete_analysis"
    ]
    
    for trigger in triggers:
        try:
            cursor.execute(f"DROP TRIGGER IF EXISTS {trigger}")
            print(f"  ✓ Dropped: {trigger}")
        except Error as e:
            print(f"  ⚠️  {trigger}: {e}")
    
    connection.commit()
    cursor.close()

def create_enhanced_triggers(connection):
    """Create enhanced triggers with proper update logic"""
    cursor = connection.cursor()
    
    print("\n[Step 2] Creating enhanced triggers...")
    
    # =====================================================================
    # TRIGGER 1: INSERT - Populate analysis tables on new master record
    # =====================================================================
    insert_trigger = """
    CREATE TRIGGER after_master_insert_analysis
    AFTER INSERT ON tax_summit_master_data
    FOR EACH ROW
    BEGIN
        -- Tax_Persons_Analysis
        IF NEW.Phone_Number IS NOT NULL AND NEW.Phone_Number != '' THEN
            INSERT INTO Tax_Persons_Analysis 
                (Client_Name, Practice_Head, Partner, Invite_Status, numInvitees, 
                 Response, Sector, numRegistrations, Tax_Contact, Designation, 
                 Email_ID, Phone_Number, Location, Response_1)
            VALUES 
                (NEW.Client_Name, NEW.Practice_Head, NEW.Partner, NEW.Invite_Status, 
                 NEW.numInvitees, NEW.Response, NEW.Sector, NEW.numRegistrations, 
                 NEW.Tax_Contact, NEW.Designation, NEW.Email_ID, NEW.Phone_Number, 
                 NEW.Location, NEW.Response_1)
            ON DUPLICATE KEY UPDATE
                Client_Name = NEW.Client_Name,
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
                Response_1 = NEW.Response_1,
                Last_Updated = CURRENT_TIMESTAMP;
        END IF;
        
        -- CFO_Persons_Analysis
        IF NEW.Phone_Number_4 IS NOT NULL AND NEW.Phone_Number_4 != '' THEN
            INSERT INTO CFO_Persons_Analysis 
                (Company_Name, Practice_Head, Partner, Invite_Status, numInvitees, 
                 Response, Sector, numRegistrations, CFO_Name, Designation_2, 
                 Email_ID_3, Phone_Number_4, Location_6, Response_7)
            VALUES 
                (NEW.Client_Name, NEW.Practice_Head, NEW.Partner, NEW.Invite_Status, 
                 NEW.numInvitees, NEW.Response, NEW.Sector, NEW.numRegistrations, 
                 NEW.CFO_Name, NEW.Designation_2, NEW.Email_ID_3, NEW.Phone_Number_4, 
                 NEW.Location_6, NEW.Response_7)
            ON DUPLICATE KEY UPDATE
                Company_Name = NEW.Client_Name,
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
                Response_7 = NEW.Response_7,
                Last_Updated = CURRENT_TIMESTAMP;
        END IF;
        
        -- Other_Persons_Analysis
        IF NEW.Phone_Number_10 IS NOT NULL AND NEW.Phone_Number_10 != '' THEN
            INSERT INTO Other_Persons_Analysis 
                (Company_Name, Practice_Head, Partner, Invite_Status, numInvitees, 
                 Response, Sector, numRegistrations, Others, Designation_8, 
                 Email_ID_9, Phone_Number_10, Location_12, Response_13)
            VALUES 
                (NEW.Client_Name, NEW.Practice_Head, NEW.Partner, NEW.Invite_Status, 
                 NEW.numInvitees, NEW.Response, NEW.Sector, NEW.numRegistrations, 
                 NEW.Others, NEW.Designation_8, NEW.Email_ID_9, NEW.Phone_Number_10, 
                 NEW.Location_12, NEW.Response_13)
            ON DUPLICATE KEY UPDATE
                Company_Name = NEW.Client_Name,
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
                Response_13 = NEW.Response_13,
                Last_Updated = CURRENT_TIMESTAMP;
        END IF;
    END
    """
    
    # =====================================================================
    # TRIGGER 2: UPDATE - Comprehensive update for ALL columns
    # =====================================================================
    update_trigger = """
    CREATE TRIGGER after_master_update_analysis
    AFTER UPDATE ON tax_summit_master_data
    FOR EACH ROW
    BEGIN
        -- Update Tax_Persons_Analysis
        -- Updates ALL fields when ANY field changes in master
        IF NEW.Phone_Number IS NOT NULL AND NEW.Phone_Number != '' THEN
            -- If phone number changed, update old record and insert/update new
            IF OLD.Phone_Number != NEW.Phone_Number THEN
                -- Delete old phone number entry if it exists
                DELETE FROM Tax_Persons_Analysis 
                WHERE Phone_Number = OLD.Phone_Number 
                  AND Client_Name = OLD.Client_Name;
                
                -- Insert new entry
                INSERT INTO Tax_Persons_Analysis 
                    (Client_Name, Practice_Head, Partner, Invite_Status, numInvitees, 
                     Response, Sector, numRegistrations, Tax_Contact, Designation, 
                     Email_ID, Phone_Number, Location, Response_1)
                VALUES 
                    (NEW.Client_Name, NEW.Practice_Head, NEW.Partner, NEW.Invite_Status, 
                     NEW.numInvitees, NEW.Response, NEW.Sector, NEW.numRegistrations, 
                     NEW.Tax_Contact, NEW.Designation, NEW.Email_ID, NEW.Phone_Number, 
                     NEW.Location, NEW.Response_1)
                ON DUPLICATE KEY UPDATE
                    Client_Name = NEW.Client_Name,
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
                    Response_1 = NEW.Response_1,
                    Last_Updated = CURRENT_TIMESTAMP;
            ELSE
                -- Phone number same, just update all other fields
                UPDATE Tax_Persons_Analysis 
                SET 
                    Client_Name = NEW.Client_Name,
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
                    Response_1 = NEW.Response_1,
                    Last_Updated = CURRENT_TIMESTAMP
                WHERE Phone_Number = NEW.Phone_Number;
            END IF;
        ELSE
            -- Phone number is now NULL/empty, delete from analysis
            IF OLD.Phone_Number IS NOT NULL AND OLD.Phone_Number != '' THEN
                DELETE FROM Tax_Persons_Analysis 
                WHERE Phone_Number = OLD.Phone_Number 
                  AND Client_Name = OLD.Client_Name;
            END IF;
        END IF;
        
        -- Update CFO_Persons_Analysis (same logic)
        IF NEW.Phone_Number_4 IS NOT NULL AND NEW.Phone_Number_4 != '' THEN
            IF OLD.Phone_Number_4 != NEW.Phone_Number_4 THEN
                DELETE FROM CFO_Persons_Analysis 
                WHERE Phone_Number_4 = OLD.Phone_Number_4 
                  AND Company_Name = OLD.Client_Name;
                
                INSERT INTO CFO_Persons_Analysis 
                    (Company_Name, Practice_Head, Partner, Invite_Status, numInvitees, 
                     Response, Sector, numRegistrations, CFO_Name, Designation_2, 
                     Email_ID_3, Phone_Number_4, Location_6, Response_7)
                VALUES 
                    (NEW.Client_Name, NEW.Practice_Head, NEW.Partner, NEW.Invite_Status, 
                     NEW.numInvitees, NEW.Response, NEW.Sector, NEW.numRegistrations, 
                     NEW.CFO_Name, NEW.Designation_2, NEW.Email_ID_3, NEW.Phone_Number_4, 
                     NEW.Location_6, NEW.Response_7)
                ON DUPLICATE KEY UPDATE
                    Company_Name = NEW.Client_Name,
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
                    Response_7 = NEW.Response_7,
                    Last_Updated = CURRENT_TIMESTAMP;
            ELSE
                UPDATE CFO_Persons_Analysis 
                SET 
                    Company_Name = NEW.Client_Name,
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
                    Response_7 = NEW.Response_7,
                    Last_Updated = CURRENT_TIMESTAMP
                WHERE Phone_Number_4 = NEW.Phone_Number_4;
            END IF;
        ELSE
            IF OLD.Phone_Number_4 IS NOT NULL AND OLD.Phone_Number_4 != '' THEN
                DELETE FROM CFO_Persons_Analysis 
                WHERE Phone_Number_4 = OLD.Phone_Number_4 
                  AND Company_Name = OLD.Client_Name;
            END IF;
        END IF;
        
        -- Update Other_Persons_Analysis (same logic)
        IF NEW.Phone_Number_10 IS NOT NULL AND NEW.Phone_Number_10 != '' THEN
            IF OLD.Phone_Number_10 != NEW.Phone_Number_10 THEN
                DELETE FROM Other_Persons_Analysis 
                WHERE Phone_Number_10 = OLD.Phone_Number_10 
                  AND Company_Name = OLD.Client_Name;
                
                INSERT INTO Other_Persons_Analysis 
                    (Company_Name, Practice_Head, Partner, Invite_Status, numInvitees, 
                     Response, Sector, numRegistrations, Others, Designation_8, 
                     Email_ID_9, Phone_Number_10, Location_12, Response_13)
                VALUES 
                    (NEW.Client_Name, NEW.Practice_Head, NEW.Partner, NEW.Invite_Status, 
                     NEW.numInvitees, NEW.Response, NEW.Sector, NEW.numRegistrations, 
                     NEW.Others, NEW.Designation_8, NEW.Email_ID_9, NEW.Phone_Number_10, 
                     NEW.Location_12, NEW.Response_13)
                ON DUPLICATE KEY UPDATE
                    Company_Name = NEW.Client_Name,
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
                    Response_13 = NEW.Response_13,
                    Last_Updated = CURRENT_TIMESTAMP;
            ELSE
                UPDATE Other_Persons_Analysis 
                SET 
                    Company_Name = NEW.Client_Name,
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
                    Response_13 = NEW.Response_13,
                    Last_Updated = CURRENT_TIMESTAMP
                WHERE Phone_Number_10 = NEW.Phone_Number_10;
            END IF;
        ELSE
            IF OLD.Phone_Number_10 IS NOT NULL AND OLD.Phone_Number_10 != '' THEN
                DELETE FROM Other_Persons_Analysis 
                WHERE Phone_Number_10 = OLD.Phone_Number_10 
                  AND Company_Name = OLD.Client_Name;
            END IF;
        END IF;
    END
    """
    
    # =====================================================================
    # TRIGGER 3: DELETE - Remove from analysis tables when deleted from master
    # =====================================================================
    delete_trigger = """
    CREATE TRIGGER after_master_delete_analysis
    AFTER DELETE ON tax_summit_master_data
    FOR EACH ROW
    BEGIN
        -- Delete from Tax_Persons_Analysis
        IF OLD.Phone_Number IS NOT NULL AND OLD.Phone_Number != '' THEN
            DELETE FROM Tax_Persons_Analysis 
            WHERE Phone_Number = OLD.Phone_Number 
              AND Client_Name = OLD.Client_Name;
        END IF;
        
        -- Delete from CFO_Persons_Analysis
        IF OLD.Phone_Number_4 IS NOT NULL AND OLD.Phone_Number_4 != '' THEN
            DELETE FROM CFO_Persons_Analysis 
            WHERE Phone_Number_4 = OLD.Phone_Number_4 
              AND Company_Name = OLD.Client_Name;
        END IF;
        
        -- Delete from Other_Persons_Analysis
        IF OLD.Phone_Number_10 IS NOT NULL AND OLD.Phone_Number_10 != '' THEN
            DELETE FROM Other_Persons_Analysis 
            WHERE Phone_Number_10 = OLD.Phone_Number_10 
              AND Company_Name = OLD.Client_Name;
        END IF;
    END
    """
    
    # Execute trigger creation
    try:
        cursor.execute(insert_trigger)
        print("  ✓ Created: after_master_insert_analysis")
        
        cursor.execute(update_trigger)
        print("  ✓ Created: after_master_update_analysis")
        
        cursor.execute(delete_trigger)
        print("  ✓ Created: after_master_delete_analysis")
        
        connection.commit()
        print("\n✅ All triggers created successfully!")
        
    except Error as e:
        print(f"\n❌ Error creating triggers: {e}")
        connection.rollback()
        return False
    finally:
        cursor.close()
    
    return True

def test_trigger_functionality(connection):
    """Test the triggers with a sample update"""
    cursor = connection.cursor(dictionary=True)
    
    print("\n[Step 3] Testing trigger functionality...")
    
    try:
        # Get a sample record
        cursor.execute("""
            SELECT Client_Name, Phone_Number, Practice_Head 
            FROM tax_summit_master_data 
            WHERE Phone_Number IS NOT NULL AND Phone_Number != ''
            LIMIT 1
        """)
        sample = cursor.fetchone()
        
        if not sample:
            print("  ⚠️  No sample data to test")
            return
        
        client = sample['Client_Name']
        phone = sample['Phone_Number']
        old_ph = sample['Practice_Head']
        
        print(f"  Testing with: {client} ({phone})")
        print(f"  Current Practice_Head: {old_ph}")
        
        # Update Practice_Head
        test_value = f"TEST_{old_ph}"
        cursor.execute("""
            UPDATE tax_summit_master_data 
            SET Practice_Head = %s 
            WHERE Client_Name = %s
        """, (test_value, client))
        
        # Check if it updated in analysis table
        cursor.execute("""
            SELECT Practice_Head 
            FROM Tax_Persons_Analysis 
            WHERE Phone_Number = %s
        """, (phone,))
        result = cursor.fetchone()
        
        if result and result['Practice_Head'] == test_value:
            print(f"  ✅ TEST PASSED! Analysis table updated correctly")
            print(f"     New Practice_Head in analysis: {result['Practice_Head']}")
        else:
            print(f"  ❌ TEST FAILED! Analysis table not updated")
            if result:
                print(f"     Expected: {test_value}")
                print(f"     Got: {result['Practice_Head']}")
        
        # Restore original value
        cursor.execute("""
            UPDATE tax_summit_master_data 
            SET Practice_Head = %s 
            WHERE Client_Name = %s
        """, (old_ph, client))
        
        connection.commit()
        print(f"  ✓ Test completed, original value restored")
        
    except Error as e:
        print(f"  ❌ Test error: {e}")
        connection.rollback()
    finally:
        cursor.close()

def verify_sync_status(connection):
    """Verify current sync status"""
    cursor = connection.cursor(dictionary=True)
    
    print("\n[Step 4] Verifying sync status...")
    
    try:
        # Check counts
        cursor.execute("SELECT COUNT(*) as c FROM tax_summit_master_data WHERE Phone_Number IS NOT NULL AND Phone_Number != ''")
        master_tax = cursor.fetchone()['c']
        
        cursor.execute("SELECT COUNT(*) as c FROM Tax_Persons_Analysis")
        analysis_tax = cursor.fetchone()['c']
        
        cursor.execute("SELECT COUNT(*) as c FROM tax_summit_master_data WHERE Phone_Number_4 IS NOT NULL AND Phone_Number_4 != ''")
        master_cfo = cursor.fetchone()['c']
        
        cursor.execute("SELECT COUNT(*) as c FROM CFO_Persons_Analysis")
        analysis_cfo = cursor.fetchone()['c']
        
        cursor.execute("SELECT COUNT(*) as c FROM tax_summit_master_data WHERE Phone_Number_10 IS NOT NULL AND Phone_Number_10 != ''")
        master_other = cursor.fetchone()['c']
        
        cursor.execute("SELECT COUNT(*) as c FROM Other_Persons_Analysis")
        analysis_other = cursor.fetchone()['c']
        
        print("\n  Master → Analysis:")
        print(f"    Tax:   {master_tax} → {analysis_tax}   {'✅' if master_tax == analysis_tax else '⚠️'}")
        print(f"    CFO:   {master_cfo} → {analysis_cfo}   {'✅' if master_cfo == analysis_cfo else '⚠️'}")
        print(f"    Other: {master_other} → {analysis_other}   {'✅' if master_other == analysis_other else '⚠️'}")
        
    except Error as e:
        print(f"  ❌ Verification error: {e}")
    finally:
        cursor.close()

def main():
    print("\n" + "="*70)
    print("  🔧 ENHANCED ANALYSIS TABLE TRIGGERS")
    print("="*70)
    print("\n  This will create triggers that sync ALL changes from master")
    print("  to analysis tables, including:")
    print("    • Any column updates (Practice_Head, Partner, Response, etc.)")
    print("    • Phone number changes (handles old/new properly)")
    print("    • Deletions (cascading to analysis tables)")
    print("="*70 + "\n")
    
    connection = connect_to_mysql()
    if not connection:
        return
    
    try:
        # Drop old triggers
        drop_existing_triggers(connection)
        
        # Create new enhanced triggers
        if not create_enhanced_triggers(connection):
            print("\n❌ Failed to create triggers")
            return
        
        # Test functionality
        test_trigger_functionality(connection)
        
        # Verify sync
        verify_sync_status(connection)
        
        print("\n" + "="*70)
        print("  ✅ SETUP COMPLETE!")
        print("="*70)
        print("\n  Your triggers now handle:")
        print("    ✓ ALL column updates (not just phone)")
        print("    ✓ Phone number changes (properly deletes old, inserts new)")
        print("    ✓ NULL phone numbers (removes from analysis)")
        print("    ✓ Row deletions (cascading delete)")
        print("    ✓ Timestamps (Last_Updated field)")
        print("\n  Try it out:")
        print("    1. Update any field in tax_summit_master_data")
        print("    2. Check the corresponding analysis table")
        print("    3. The change will be reflected automatically!")
        print("="*70 + "\n")
        
    finally:
        if connection.is_connected():
            connection.close()
            print("✓ Connection closed\n")

if __name__ == "__main__":
    main()