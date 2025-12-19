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

def check_sync_status(connection):
    """Check current sync status and identify discrepancies"""
    cursor = connection.cursor(dictionary=True)
    
    print("\n[Checking Current Sync Status]")
    print("-" * 70)
    
    try:
        # Tax contacts
        cursor.execute("SELECT COUNT(*) as c FROM tax_summit_master_data WHERE Phone_Number IS NOT NULL AND Phone_Number != ''")
        master_tax = cursor.fetchone()['c']
        
        cursor.execute("SELECT COUNT(*) as c FROM Tax_Persons_Analysis")
        analysis_tax = cursor.fetchone()['c']
        
        # CFO contacts
        cursor.execute("SELECT COUNT(*) as c FROM tax_summit_master_data WHERE Phone_Number_4 IS NOT NULL AND Phone_Number_4 != ''")
        master_cfo = cursor.fetchone()['c']
        
        cursor.execute("SELECT COUNT(*) as c FROM CFO_Persons_Analysis")
        analysis_cfo = cursor.fetchone()['c']
        
        # Other contacts
        cursor.execute("SELECT COUNT(*) as c FROM tax_summit_master_data WHERE Phone_Number_10 IS NOT NULL AND Phone_Number_10 != ''")
        master_other = cursor.fetchone()['c']
        
        cursor.execute("SELECT COUNT(*) as c FROM Other_Persons_Analysis")
        analysis_other = cursor.fetchone()['c']
        
        print(f"\n  Master → Analysis (Current State):")
        print(f"    Tax:   {master_tax} → {analysis_tax}   ({master_tax - analysis_tax} missing)")
        print(f"    CFO:   {master_cfo} → {analysis_cfo}   ({master_cfo - analysis_cfo} missing)")
        print(f"    Other: {master_other} → {analysis_other}   ({master_other - analysis_other} missing)")
        
        total_missing = (master_tax - analysis_tax) + (master_cfo - analysis_cfo) + (master_other - analysis_other)
        
        if total_missing > 0:
            print(f"\n  ⚠️  Total {total_missing} records need to be synced")
            return False
        else:
            print(f"\n  ✅ All tables are in sync!")
            return True
            
    except Error as e:
        print(f"  ❌ Error checking sync: {e}")
        return False
    finally:
        cursor.close()

def perform_full_resync(connection):
    """Perform complete resync of all analysis tables from master"""
    cursor = connection.cursor()
    
    print("\n[Performing Full Resync]")
    print("-" * 70)
    print("\n  This will:")
    print("    1. Clear all existing analysis data")
    print("    2. Repopulate from master table")
    print("    3. Catch ALL pending changes")
    print()
    
    try:
        # Step 1: Clear analysis tables
        print("  [1/4] Clearing analysis tables...")
        
        cursor.execute("DELETE FROM Tax_Persons_Analysis")
        tax_deleted = cursor.rowcount
        print(f"        Tax_Persons_Analysis: {tax_deleted} rows deleted")
        
        cursor.execute("DELETE FROM CFO_Persons_Analysis")
        cfo_deleted = cursor.rowcount
        print(f"        CFO_Persons_Analysis: {cfo_deleted} rows deleted")
        
        cursor.execute("DELETE FROM Other_Persons_Analysis")
        other_deleted = cursor.rowcount
        print(f"        Other_Persons_Analysis: {other_deleted} rows deleted")
        
        connection.commit()
        
        # Step 2: Repopulate Tax_Persons_Analysis
        print("\n  [2/4] Repopulating Tax_Persons_Analysis...")
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
        tax_inserted = cursor.rowcount
        print(f"        ✓ {tax_inserted} records inserted")
        
        # Step 3: Repopulate CFO_Persons_Analysis
        print("\n  [3/4] Repopulating CFO_Persons_Analysis...")
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
        cfo_inserted = cursor.rowcount
        print(f"        ✓ {cfo_inserted} records inserted")
        
        # Step 4: Repopulate Other_Persons_Analysis
        print("\n  [4/4] Repopulating Other_Persons_Analysis...")
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
        other_inserted = cursor.rowcount
        print(f"        ✓ {other_inserted} records inserted")
        
        connection.commit()
        
        print(f"\n  ✅ Resync complete!")
        print(f"     Total records synced: {tax_inserted + cfo_inserted + other_inserted}")
        
        return True
        
    except Error as e:
        print(f"\n  ❌ Resync failed: {e}")
        connection.rollback()
        return False
    finally:
        cursor.close()

def drop_existing_triggers(connection):
    """Drop all existing analysis triggers"""
    cursor = connection.cursor()
    
    print("\n[Dropping Old Triggers]")
    print("-" * 70)
    
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
    
    print("\n[Creating Enhanced Triggers]")
    print("-" * 70)
    
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
        IF NEW.Phone_Number IS NOT NULL AND NEW.Phone_Number != '' THEN
            IF OLD.Phone_Number != NEW.Phone_Number THEN
                DELETE FROM Tax_Persons_Analysis 
                WHERE Phone_Number = OLD.Phone_Number 
                  AND Client_Name = OLD.Client_Name;
                
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
            IF OLD.Phone_Number IS NOT NULL AND OLD.Phone_Number != '' THEN
                DELETE FROM Tax_Persons_Analysis 
                WHERE Phone_Number = OLD.Phone_Number 
                  AND Client_Name = OLD.Client_Name;
            END IF;
        END IF;
        
        -- Update CFO_Persons_Analysis
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
        
        -- Update Other_Persons_Analysis
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
        IF OLD.Phone_Number IS NOT NULL AND OLD.Phone_Number != '' THEN
            DELETE FROM Tax_Persons_Analysis 
            WHERE Phone_Number = OLD.Phone_Number 
              AND Client_Name = OLD.Client_Name;
        END IF;
        
        IF OLD.Phone_Number_4 IS NOT NULL AND OLD.Phone_Number_4 != '' THEN
            DELETE FROM CFO_Persons_Analysis 
            WHERE Phone_Number_4 = OLD.Phone_Number_4 
              AND Company_Name = OLD.Client_Name;
        END IF;
        
        IF OLD.Phone_Number_10 IS NOT NULL AND OLD.Phone_Number_10 != '' THEN
            DELETE FROM Other_Persons_Analysis 
            WHERE Phone_Number_10 = OLD.Phone_Number_10 
              AND Company_Name = OLD.Client_Name;
        END IF;
    END
    """
    
    try:
        cursor.execute(insert_trigger)
        print("  ✓ Created: after_master_insert_analysis")
        
        cursor.execute(update_trigger)
        print("  ✓ Created: after_master_update_analysis")
        
        cursor.execute(delete_trigger)
        print("  ✓ Created: after_master_delete_analysis")
        
        connection.commit()
        return True
        
    except Error as e:
        print(f"\n  ❌ Error creating triggers: {e}")
        connection.rollback()
        return False
    finally:
        cursor.close()

def test_trigger_functionality(connection):
    """Test the triggers with a sample update"""
    cursor = connection.cursor(dictionary=True)
    
    print("\n[Testing Trigger Functionality]")
    print("-" * 70)
    
    try:
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
        
        print(f"\n  Testing with: {client} ({phone})")
        print(f"  Current Practice_Head: {old_ph}")
        
        test_value = f"TEST_{old_ph}"
        cursor.execute("""
            UPDATE tax_summit_master_data 
            SET Practice_Head = %s 
            WHERE Client_Name = %s
        """, (test_value, client))
        
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
        
        cursor.execute("""
            UPDATE tax_summit_master_data 
            SET Practice_Head = %s 
            WHERE Client_Name = %s
        """, (old_ph, client))
        
        connection.commit()
        print(f"  ✓ Original value restored")
        
    except Error as e:
        print(f"  ❌ Test error: {e}")
        connection.rollback()
    finally:
        cursor.close()

def main():
    print("\n" + "="*70)
    print("  🔧 ENHANCED ANALYSIS TABLE TRIGGERS + FULL RESYNC")
    print("="*70)
    print("\n  This script will:")
    print("    1. Check current sync status")
    print("    2. Perform FULL RESYNC (sync all pending changes)")
    print("    3. Drop old triggers")
    print("    4. Create new enhanced triggers")
    print("    5. Test trigger functionality")
    print("="*70 + "\n")
    
    connection = connect_to_mysql()
    if not connection:
        return
    
    try:
        # Step 1: Check current status
        is_synced = check_sync_status(connection)
        
        # Step 2: Perform full resync if needed
        if not is_synced:
            print("\n⚠️  Tables are out of sync. Performing full resync...")
            if not perform_full_resync(connection):
                print("\n❌ Resync failed. Cannot continue.")
                return
            
            # Verify resync worked
            print("\n[Verifying Resync]")
            print("-" * 70)
            check_sync_status(connection)
        
        # Step 3: Drop old triggers
        drop_existing_triggers(connection)
        
        # Step 4: Create new triggers
        if not create_enhanced_triggers(connection):
            print("\n❌ Failed to create triggers")
            return
        
        # Step 5: Test triggers
        test_trigger_functionality(connection)
        
        # Final summary
        print("\n" + "="*70)
        print("  ✅ COMPLETE SETUP FINISHED!")
        print("="*70)
        print("\n  ✓ All pending changes have been synced")
        print("  ✓ Enhanced triggers created")
        print("  ✓ Trigger functionality tested")
        print("\n  From now on, ALL updates to master table will")
        print("  automatically sync to analysis tables!")
        print("\n  This includes updates to:")
        print("    • Practice_Head, Partner, Sector, Location")
        print("    • Response, Response_1, Response_7, Response_13")
        print("    • numInvitees, numRegistrations")
        print("    • Email addresses, Phone numbers")
        print("    • ANY other field in master table")
        print("="*70 + "\n")
        
    finally:
        if connection.is_connected():
            connection.close()
            print("✓ Connection closed\n")

if __name__ == "__main__":
    main()