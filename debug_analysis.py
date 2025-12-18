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

def check_table_exists(cursor, table_name):
    """Check if table exists"""
    try:
        cursor.execute(f"SHOW TABLES LIKE '{table_name}'")
        result = cursor.fetchone()
        return result is not None
    except:
        return False

def get_table_structure(cursor, table_name):
    """Get table column structure"""
    try:
        cursor.execute(f"DESCRIBE {table_name}")
        columns = cursor.fetchall()
        return columns
    except Error as e:
        return None

def diagnose_insert_problem(connection):
    """Diagnose why insert is failing"""
    
    print("\n" + "="*70)
    print("  🔍 DIAGNOSING INSERT PROBLEM")
    print("="*70 + "\n")
    
    cursor = connection.cursor()
    
    # Step 1: Check if tables exist (case-sensitive)
    print("[1] Checking if tables exist...\n")
    
    tables_to_check = [
        'tax_summit_master_data',
        'Tax_Persons_Analysis',
        'tax_persons_analysis',
        'CFO_Persons_Analysis',
        'cfo_persons_analysis',
        'Other_Persons_Analysis',
        'other_persons_analysis'
    ]
    
    existing_tables = {}
    for table in tables_to_check:
        exists = check_table_exists(cursor, table)
        if exists:
            print(f"    ✓ {table} exists")
            existing_tables[table] = True
        else:
            print(f"    ✗ {table} NOT found")
            existing_tables[table] = False
    
    # Determine correct table names
    master_table = 'tax_summit_master_data'
    
    if existing_tables.get('Tax_Persons_Analysis'):
        tax_analysis = 'Tax_Persons_Analysis'
    elif existing_tables.get('tax_persons_analysis'):
        tax_analysis = 'tax_persons_analysis'
    else:
        print("\n❌ ERROR: No Tax analysis table found!")
        return
    
    print(f"\n    → Will use: {tax_analysis}")
    
    # Step 2: Check master table structure
    print(f"\n[2] Checking {master_table} structure...\n")
    
    master_cols = get_table_structure(cursor, master_table)
    if master_cols:
        master_col_names = [col[0] for col in master_cols]
        print(f"    Found {len(master_col_names)} columns:")
        
        # Check for required columns
        required_cols = [
            'Client_Name', 'Practice_Head', 'Partner', 'Invite_Status',
            'numInvitees', 'Response', 'Sector', 'numRegistrations',
            'Tax_Contact', 'Designation', 'Email_ID', 'Phone_Number',
            'Location', 'Response_1'
        ]
        
        missing_cols = []
        for col in required_cols:
            if col in master_col_names:
                print(f"      ✓ {col}")
            else:
                print(f"      ✗ {col} MISSING")
                missing_cols.append(col)
        
        if missing_cols:
            print(f"\n    ⚠️ WARNING: Missing columns in master: {missing_cols}")
            print(f"    Available columns: {master_col_names}")
    else:
        print(f"    ❌ Could not read {master_table} structure")
    
    # Step 3: Check analysis table structure
    print(f"\n[3] Checking {tax_analysis} structure...\n")
    
    analysis_cols = get_table_structure(cursor, tax_analysis)
    if analysis_cols:
        analysis_col_names = [col[0] for col in analysis_cols]
        print(f"    Found {len(analysis_col_names)} columns:")
        for col in analysis_cols[:10]:  # Show first 10
            print(f"      • {col[0]} ({col[1]})")
        if len(analysis_cols) > 10:
            print(f"      ... and {len(analysis_cols) - 10} more")
    else:
        print(f"    ❌ Could not read {tax_analysis} structure")
    
    # Step 4: Check data in master
    print(f"\n[4] Checking data in {master_table}...\n")
    
    cursor.execute(f"SELECT COUNT(*) FROM {master_table}")
    total_count = cursor.fetchone()[0]
    print(f"    Total rows: {total_count}")
    
    cursor.execute(f"SELECT COUNT(*) FROM {master_table} WHERE Phone_Number IS NOT NULL AND Phone_Number != ''")
    phone_count = cursor.fetchone()[0]
    print(f"    Rows with valid Phone_Number: {phone_count}")
    
    if phone_count == 0:
        print(f"\n    ❌ PROBLEM FOUND: No rows have valid Phone_Number!")
        print(f"       This is why nothing is being inserted.")
        
        # Show sample data
        cursor.execute(f"SELECT Client_Name, Phone_Number FROM {master_table} LIMIT 5")
        samples = cursor.fetchall()
        print(f"\n    Sample data:")
        for sample in samples:
            print(f"      Client: {sample[0]}, Phone: '{sample[1]}'")
        
        return
    
    # Step 5: Try manual insert with detailed error
    print(f"\n[5] Testing manual INSERT...\n")
    
    # Get one sample row
    cursor.execute(f"""
        SELECT Client_Name, Practice_Head, Partner, Invite_Status, numInvitees, Response,
               Sector, numRegistrations, Tax_Contact, Designation, Email_ID, Phone_Number,
               Location, Response_1
        FROM {master_table}
        WHERE Phone_Number IS NOT NULL AND Phone_Number != ''
        LIMIT 1
    """)
    
    sample = cursor.fetchone()
    if not sample:
        print("    ❌ No sample data found!")
        return
    
    print(f"    Sample row: {sample[0]} (Phone: {sample[11]})")
    
    # Try to insert this one row
    try:
        # Build column list from analysis table
        analysis_col_list = ', '.join([col[0] for col in analysis_cols if col[0] not in ['id', 'S_No', 'Data_Insert_Time', 'Last_Updated']])
        
        insert_query = f"""
            INSERT INTO {tax_analysis} 
                (Client_Name, Practice_Head, Partner, Invite_Status, numInvitees, Response,
                 Sector, numRegistrations, Tax_Contact, Designation, Email_ID, Phone_Number,
                 Location, Response_1)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        cursor.execute(insert_query, sample)
        connection.commit()
        
        print(f"    ✓ Test insert successful!")
        
        # Verify
        cursor.execute(f"SELECT COUNT(*) FROM {tax_analysis}")
        count_after = cursor.fetchone()[0]
        print(f"    ✓ {tax_analysis} now has {count_after} rows")
        
    except Error as e:
        print(f"    ❌ Insert failed!")
        print(f"       Error: {e}")
        print(f"       Error Code: {e.errno}")
        
        if e.errno == 1054:  # Unknown column
            print(f"\n    💡 DIAGNOSIS: Column name mismatch!")
            print(f"       The INSERT query uses columns that don't exist in {tax_analysis}")
            print(f"\n    Comparing columns...")
            
            insert_cols = ['Client_Name', 'Practice_Head', 'Partner', 'Invite_Status', 
                          'numInvitees', 'Response', 'Sector', 'numRegistrations', 
                          'Tax_Contact', 'Designation', 'Email_ID', 'Phone_Number', 
                          'Location', 'Response_1']
            
            for col in insert_cols:
                if col in analysis_col_names:
                    print(f"       ✓ {col}")
                else:
                    print(f"       ✗ {col} NOT IN {tax_analysis}")
            
            print(f"\n    Actual columns in {tax_analysis}:")
            for col in analysis_col_names:
                if col not in ['id', 'S_No', 'Data_Insert_Time', 'Last_Updated']:
                    print(f"       • {col}")
        
        elif e.errno == 1452:  # Foreign key constraint
            print(f"\n    💡 DIAGNOSIS: Foreign key constraint failed!")
            print(f"       Client_Name '{sample[0]}' might not exist in master table")
        
        elif e.errno == 1062:  # Duplicate entry
            print(f"\n    💡 DIAGNOSIS: Duplicate phone number!")
            print(f"       Phone '{sample[11]}' already exists in {tax_analysis}")
        
        else:
            print(f"\n    💡 Unknown error. Full details above.")
    
    # Step 6: Show what INSERT statement would look like
    print(f"\n[6] Recommended INSERT statement:\n")
    
    # Build correct column list
    available_insert_cols = []
    for col in ['Client_Name', 'Practice_Head', 'Partner', 'Invite_Status', 
                'numInvitees', 'Response', 'Sector', 'numRegistrations', 
                'Tax_Contact', 'Designation', 'Email_ID', 'Phone_Number', 
                'Location', 'Response_1']:
        if col in analysis_col_names:
            available_insert_cols.append(col)
    
    if available_insert_cols:
        print(f"    INSERT INTO {tax_analysis}")
        print(f"        ({', '.join(available_insert_cols)})")
        print(f"    SELECT")
        print(f"        {', '.join(available_insert_cols)}")
        print(f"    FROM {master_table}")
        print(f"    WHERE Phone_Number IS NOT NULL AND Phone_Number != ''")
    
    cursor.close()

def attempt_flexible_insert(connection):
    """Try to insert with column matching"""
    
    print("\n" + "="*70)
    print("  🔧 ATTEMPTING FLEXIBLE INSERT")
    print("="*70 + "\n")
    
    cursor = connection.cursor()
    
    # Detect correct table names
    if check_table_exists(cursor, 'Tax_Persons_Analysis'):
        tax_analysis = 'Tax_Persons_Analysis'
    elif check_table_exists(cursor, 'tax_persons_analysis'):
        tax_analysis = 'tax_persons_analysis'
    else:
        print("❌ No analysis table found!")
        return
    
    master_table = 'tax_summit_master_data'
    
    # Get columns from both tables
    cursor.execute(f"DESCRIBE {master_table}")
    master_cols = {col[0] for col in cursor.fetchall()}
    
    cursor.execute(f"DESCRIBE {tax_analysis}")
    analysis_cols = {col[0] for col in cursor.fetchall() if col[0] not in ['id', 'S_No', 'Data_Insert_Time', 'Last_Updated']}
    
    # Find matching columns
    matching_cols = master_cols & analysis_cols
    matching_cols.discard('id')
    
    if not matching_cols:
        print("❌ No matching columns found!")
        return
    
    print(f"Found {len(matching_cols)} matching columns:")
    for col in sorted(matching_cols):
        print(f"  • {col}")
    
    # Build INSERT query
    cols_str = ', '.join(matching_cols)
    
    insert_query = f"""
        INSERT INTO {tax_analysis} ({cols_str})
        SELECT {cols_str}
        FROM {master_table}
        WHERE Phone_Number IS NOT NULL AND Phone_Number != ''
    """
    
    print(f"\n[1] Clearing {tax_analysis}...")
    try:
        cursor.execute(f"DELETE FROM {tax_analysis}")
        deleted = cursor.rowcount
        print(f"    ✓ Deleted {deleted} rows")
    except Error as e:
        print(f"    ⚠️ {e}")
    
    print(f"\n[2] Inserting data...")
    try:
        cursor.execute(insert_query)
        inserted = cursor.rowcount
        connection.commit()
        print(f"    ✓ Successfully inserted {inserted} rows!")
        
        # Verify
        cursor.execute(f"SELECT COUNT(*) FROM {tax_analysis}")
        final_count = cursor.fetchone()[0]
        print(f"    ✓ {tax_analysis} now has {final_count} rows")
        
        return True
        
    except Error as e:
        print(f"    ❌ Insert failed: {e}")
        connection.rollback()
        return False
    finally:
        cursor.close()

def main():
    connection = connect_to_mysql()
    if not connection:
        return
    
    try:
        # First diagnose
        diagnose_insert_problem(connection)
        
        # Ask if they want to try flexible insert
        print("\n" + "="*70)
        print("Would you like to try a flexible insert? (yes/no): ", end='')
        response = input().strip().lower()
        
        if response in ['yes', 'y']:
            if attempt_flexible_insert(connection):
                print("\n✅ SUCCESS! Data inserted into analysis table!")
                print("   Check your dashboard - it should now show correct data.")
            else:
                print("\n❌ Flexible insert also failed.")
                print("   Please share the error messages above for further help.")
        
    finally:
        if connection.is_connected():
            connection.close()
            print("\n✓ Connection closed\n")

if __name__ == "__main__":
    main()