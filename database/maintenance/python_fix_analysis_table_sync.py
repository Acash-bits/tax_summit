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

def check_current_state(connection):
    """Check current sync state across all tables"""
    cursor = connection.cursor(dictionary=True)
    
    print("\n" + "="*70)
    print("  📊 CURRENT SYNC STATE")
    print("="*70 + "\n")
    
    # Master table counts
    cursor.execute("SELECT COUNT(*) as total FROM tax_summit_master_data WHERE Phone_Number IS NOT NULL AND Phone_Number != ''")
    master_tax = cursor.fetchone()['total']
    
    cursor.execute("SELECT COUNT(*) as total FROM tax_summit_master_data WHERE Phone_Number_4 IS NOT NULL AND Phone_Number_4 != ''")
    master_cfo = cursor.fetchone()['total']
    
    cursor.execute("SELECT COUNT(*) as total FROM tax_summit_master_data WHERE Phone_Number_10 IS NOT NULL AND Phone_Number_10 != ''")
    master_other = cursor.fetchone()['total']
    
    # Analysis table counts
    try:
        cursor.execute("SELECT COUNT(*) as total FROM Tax_Persons_Analysis")
        analysis_tax = cursor.fetchone()['total']
    except:
        cursor.execute("SELECT COUNT(*) as total FROM tax_persons_analysis")
        analysis_tax = cursor.fetchone()['total']
    
    try:
        cursor.execute("SELECT COUNT(*) as total FROM CFO_Persons_Analysis")
        analysis_cfo = cursor.fetchone()['total']
    except:
        cursor.execute("SELECT COUNT(*) as total FROM cfo_persons_analysis")
        analysis_cfo = cursor.fetchone()['total']
    
    try:
        cursor.execute("SELECT COUNT(*) as total FROM Other_Persons_Analysis")
        analysis_other = cursor.fetchone()['total']
    except:
        cursor.execute("SELECT COUNT(*) as total FROM other_persons_analysis")
        analysis_other = cursor.fetchone()['total']
    
    print("Master Table (with valid phones):")
    print(f"  Tax Contacts:   {master_tax}")
    print(f"  CFO Contacts:   {master_cfo}")
    print(f"  Other Contacts: {master_other}")
    print(f"  TOTAL:          {master_tax + master_cfo + master_other}")
    
    print("\nAnalysis Tables (used by Dashboard):")
    print(f"  Tax_Persons_Analysis:   {analysis_tax}")
    print(f"  CFO_Persons_Analysis:   {analysis_cfo}")
    print(f"  Other_Persons_Analysis: {analysis_other}")
    print(f"  TOTAL:                  {analysis_tax + analysis_cfo + analysis_other}")
    
    print("\nDiscrepancies:")
    print(f"  Tax:   {master_tax - analysis_tax} missing")
    print(f"  CFO:   {master_cfo - analysis_cfo} missing")
    print(f"  Other: {master_other - analysis_other} missing")
    
    cursor.close()
    return (master_tax - analysis_tax, master_cfo - analysis_cfo, master_other - analysis_other)

def drop_and_recreate_triggers(connection):
    """Drop old triggers and create new comprehensive ones"""
    cursor = connection.cursor()
    
    print("\n" + "="*70)
    print("  🔧 UPDATING TRIGGERS")
    print("="*70 + "\n")
    
    # Drop all existing triggers
    print("[1] Dropping old triggers...")
    drop_triggers = [
        "DROP TRIGGER IF EXISTS after_master_insert_analysis",
        "DROP TRIGGER IF EXISTS after_master_update_analysis",
        "DROP TRIGGER IF EXISTS after_master_delete_analysis",
    ]
    
    for drop_sql in drop_triggers:
        try:
            cursor.execute(drop_sql)
            print(f"    ✓ {drop_sql.split('IF EXISTS')[1].strip()}")
        except Error as e:
            print(f"    ⚠ {e}")
    
    # Create new comprehensive triggers
    print("\n[2] Creating new triggers with full sync logic...")
    
    # INSERT trigger
    insert_trigger = """
    CREATE TRIGGER after_master_insert_analysis
    AFTER INSERT ON tax_summit_master_data
    FOR EACH ROW
    BEGIN
        -- Tax_Persons_Analysis
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
        
        -- CFO_Persons_Analysis
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
        
        -- Other_Persons_Analysis
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
    
    # UPDATE trigger - updates ALL fields when master changes
    update_trigger = """
    CREATE TRIGGER after_master_update_analysis
    AFTER UPDATE ON tax_summit_master_data
    FOR EACH ROW
    BEGIN
        -- Update Tax_Persons_Analysis
        IF NEW.Phone_Number IS NOT NULL AND NEW.Phone_Number != '' THEN
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
                Response_1 = NEW.Response_1
            WHERE Phone_Number = NEW.Phone_Number;
        END IF;
        
        -- Update CFO_Persons_Analysis
        IF NEW.Phone_Number_4 IS NOT NULL AND NEW.Phone_Number_4 != '' THEN
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
                Response_7 = NEW.Response_7
            WHERE Phone_Number_4 = NEW.Phone_Number_4;
        END IF;
        
        -- Update Other_Persons_Analysis
        IF NEW.Phone_Number_10 IS NOT NULL AND NEW.Phone_Number_10 != '' THEN
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
                Response_13 = NEW.Response_13
            WHERE Phone_Number_10 = NEW.Phone_Number_10;
        END IF;
    END
    """
    
    # DELETE trigger - removes from analysis when deleted from master
    delete_trigger = """
    CREATE TRIGGER after_master_delete_analysis
    AFTER DELETE ON tax_summit_master_data
    FOR EACH ROW
    BEGIN
        -- Delete from Tax_Persons_Analysis
        DELETE FROM Tax_Persons_Analysis WHERE Phone_Number = OLD.Phone_Number;
        
        -- Delete from CFO_Persons_Analysis
        DELETE FROM CFO_Persons_Analysis WHERE Phone_Number_4 = OLD.Phone_Number_4;
        
        -- Delete from Other_Persons_Analysis
        DELETE FROM Other_Persons_Analysis WHERE Phone_Number_10 = OLD.Phone_Number_10;
    END
    """
    
    try:
        cursor.execute(insert_trigger)
        print("    ✓ INSERT trigger created")
        
        cursor.execute(update_trigger)
        print("    ✓ UPDATE trigger created")
        
        cursor.execute(delete_trigger)
        print("    ✓ DELETE trigger created")
        
        connection.commit()
        print("\n✅ All triggers updated successfully!")
        
    except Error as e:
        print(f"\n❌ Error creating triggers: {e}")
        connection.rollback()
        return False
    finally:
        cursor.close()
    
    return True

def full_resync_analysis_tables(connection):
    """Completely resync analysis tables from master"""
    cursor = connection.cursor()
    
    print("\n" + "="*70)
    print("  🔄 FULL RESYNC OF ANALYSIS TABLES")
    print("="*70 + "\n")
    
    print("[1] Clearing existing analysis data...")
    
    # Clear all analysis tables
    try:
        cursor.execute("DELETE FROM Tax_Persons_Analysis")
        tax_deleted = cursor.rowcount
        print(f"    ✓ Cleared Tax_Persons_Analysis: {tax_deleted} rows")
    except:
        cursor.execute("DELETE FROM tax_persons_analysis")
        tax_deleted = cursor.rowcount
        print(f"    ✓ Cleared tax_persons_analysis: {tax_deleted} rows")
    
    try:
        cursor.execute("DELETE FROM CFO_Persons_Analysis")
        cfo_deleted = cursor.rowcount
        print(f"    ✓ Cleared CFO_Persons_Analysis: {cfo_deleted} rows")
    except:
        cursor.execute("DELETE FROM cfo_persons_analysis")
        cfo_deleted = cursor.rowcount
        print(f"    ✓ Cleared cfo_persons_analysis: {cfo_deleted} rows")
    
    try:
        cursor.execute("DELETE FROM Other_Persons_Analysis")
        other_deleted = cursor.rowcount
        print(f"    ✓ Cleared Other_Persons_Analysis: {other_deleted} rows")
    except:
        cursor.execute("DELETE FROM other_persons_analysis")
        other_deleted = cursor.rowcount
        print(f"    ✓ Cleared other_persons_analysis: {other_deleted} rows")
    
    connection.commit()
    
    print("\n[2] Repopulating from master table...")
    
    # Repopulate Tax_Persons_Analysis
    try:
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
        tax_added = cursor.rowcount
        print(f"    ✓ Tax_Persons_Analysis: {tax_added} rows added")
    except Exception as e:
        print(f"    ⚠ Tax_Persons_Analysis: {e}")
        tax_added = 0
    
    # Repopulate CFO_Persons_Analysis
    try:
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
        cfo_added = cursor.rowcount
        print(f"    ✓ CFO_Persons_Analysis: {cfo_added} rows added")
    except Exception as e:
        print(f"    ⚠ CFO_Persons_Analysis: {e}")
        cfo_added = 0
    
    # Repopulate Other_Persons_Analysis
    try:
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
        other_added = cursor.rowcount
        print(f"    ✓ Other_Persons_Analysis: {other_added} rows added")
    except Exception as e:
        print(f"    ⚠ Other_Persons_Analysis: {e}")
        other_added = 0
    
    connection.commit()
    
    print(f"\n✅ Resync complete!")
    print(f"   Total rows added: {tax_added + cfo_added + other_added}")
    
    cursor.close()

def verify_sync(connection):
    """Final verification of sync"""
    cursor = connection.cursor(dictionary=True)
    
    print("\n" + "="*70)
    print("  ✅ VERIFICATION")
    print("="*70 + "\n")
    
    # Count specific case: Response_1 = 'Registered'
    cursor.execute("""
        SELECT COUNT(*) as count 
        FROM tax_summit_master_data 
        WHERE (Response_1 = 'Registered' OR Response_1 = 'registered')
        AND Phone_Number IS NOT NULL AND Phone_Number != ''
    """)
    master_registered = cursor.fetchone()['count']
    
    try:
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM Tax_Persons_Analysis 
            WHERE Response_1 = 'Registered' OR Response_1 = 'registered'
        """)
        analysis_registered = cursor.fetchone()['count']
    except:
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM tax_persons_analysis 
            WHERE Response_1 = 'Registered' OR Response_1 = 'registered'
        """)
        analysis_registered = cursor.fetchone()['count']
    
    print("Registered Tax Contacts:")
    print(f"  Master table:   {master_registered}")
    print(f"  Analysis table: {analysis_registered}")
    
    if master_registered == analysis_registered:
        print(f"  ✅ PERFECT SYNC!")
    else:
        diff = master_registered - analysis_registered
        print(f"  ⚠️  Still {diff} missing")
        print(f"     (These likely have NULL/empty phone numbers)")
    
    # Overall counts
    print("\n" + "-"*70)
    
    cursor.execute("SELECT COUNT(*) as c FROM tax_summit_master_data WHERE Phone_Number IS NOT NULL AND Phone_Number != ''")
    m_tax = cursor.fetchone()['c']
    cursor.execute("SELECT COUNT(*) as c FROM tax_summit_master_data WHERE Phone_Number_4 IS NOT NULL AND Phone_Number_4 != ''")
    m_cfo = cursor.fetchone()['c']
    cursor.execute("SELECT COUNT(*) as c FROM tax_summit_master_data WHERE Phone_Number_10 IS NOT NULL AND Phone_Number_10 != ''")
    m_other = cursor.fetchone()['c']
    
    try:
        cursor.execute("SELECT COUNT(*) as c FROM Tax_Persons_Analysis")
        a_tax = cursor.fetchone()['c']
        cursor.execute("SELECT COUNT(*) as c FROM CFO_Persons_Analysis")
        a_cfo = cursor.fetchone()['c']
        cursor.execute("SELECT COUNT(*) as c FROM Other_Persons_Analysis")
        a_other = cursor.fetchone()['c']
    except:
        cursor.execute("SELECT COUNT(*) as c FROM tax_persons_analysis")
        a_tax = cursor.fetchone()['c']
        cursor.execute("SELECT COUNT(*) as c FROM cfo_persons_analysis")
        a_cfo = cursor.fetchone()['c']
        cursor.execute("SELECT COUNT(*) as c FROM other_persons_analysis")
        a_other = cursor.fetchone()['c']
    
    print("All Contacts Summary:")
    print(f"  Tax:   {m_tax} in master → {a_tax} in analysis")
    print(f"  CFO:   {m_cfo} in master → {a_cfo} in analysis")
    print(f"  Other: {m_other} in master → {a_other} in analysis")
    
    total_match = (m_tax == a_tax) and (m_cfo == a_cfo) and (m_other == a_other)
    
    if total_match:
        print(f"\n  🎉 ALL ANALYSIS TABLES FULLY SYNCED!")
    else:
        print(f"\n  ℹ️  Minor discrepancies exist (likely due to NULL phones)")
    
    cursor.close()

def main():
    print("\n" + "="*70)
    print("  🔧 ANALYSIS TABLE SYNC FIX")
    print("="*70)
    print("\n  This will:")
    print("  1. Check current sync state")
    print("  2. Update triggers for better sync")
    print("  3. Perform full resync of all analysis tables")
    print("  4. Verify the fix")
    print("="*70)
    
    connection = connect_to_mysql()
    if not connection:
        return
    
    try:
        # Step 1: Check current state
        discrepancies = check_current_state(connection)
        
        if all(d == 0 for d in discrepancies):
            print("\n✅ Everything is already in sync!")
            print("   No action needed.")
            return
        
        # Step 2: Ask for confirmation
        print("\n" + "="*70)
        print("⚠️  WARNING: This will:")
        print("   • Delete ALL data from analysis tables")
        print("   • Repopulate from master table")
        print("   • Update triggers")
        print("="*70)
        print("\nContinue? (yes/no): ", end='')
        
        response = input().strip().lower()
        
        if response not in ['yes', 'y']:
            print("\n❌ Cancelled. No changes made.")
            return
        
        # Step 3: Update triggers
        if not drop_and_recreate_triggers(connection):
            print("\n❌ Failed to update triggers. Stopping.")
            return
        
        # Step 4: Full resync
        full_resync_analysis_tables(connection)
        
        # Step 5: Verify
        verify_sync(connection)
        
        print("\n" + "="*70)
        print("  ✅ FIX COMPLETE!")
        print("="*70)
        print("\n📊 Your dashboard should now show correct data!")
        print("   Refresh your dashboard to see the changes.")
        print("\n💡 From now on, any changes to master table will")
        print("   automatically sync to analysis tables via triggers.")
        print("="*70 + "\n")
        
    finally:
        if connection.is_connected():
            connection.close()
            print("✓ MySQL connection closed\n")

if __name__ == "__main__":
    main()