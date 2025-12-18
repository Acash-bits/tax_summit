import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

def connect_to_db(db_type):
    """Connect to local or railway database"""
    try:
        if db_type == 'local':
            config = {
                'host': os.getenv("DB_HOST"),
                'user': os.getenv("DB_USER"),
                'password': os.getenv("DB_PASS"),
                'database': os.getenv("DB_NAME"),
                'port': int(os.getenv("DB_PORT", 3306))
            }
        else:
            config = {
                'host': os.getenv("RAILWAY_DB_HOST"),
                'user': os.getenv("RAILWAY_DB_USER"),
                'password': os.getenv("RAILWAY_DB_PASS"),
                'database': os.getenv("RAILWAY_DB_NAME"),
                'port': int(os.getenv("RAILWAY_DB_PORT", 3306))
            }
        
        connection = mysql.connector.connect(**config)
        if connection.is_connected():
            print(f"   ✓ Connected to {db_type.upper()} database")
            return connection
    except Error as e:
        print(f"   ✗ Error connecting to {db_type}: {e}")
        return None

def get_columns(connection, table_name):
    """Get list of columns in a table"""
    cursor = connection.cursor()
    try:
        cursor.execute(f"SHOW COLUMNS FROM `{table_name}`")
        columns = [row[0] for row in cursor.fetchall()]
        return set(columns)
    except Error:
        return set()
    finally:
        cursor.close()

def sync_table(local_conn, railway_conn, local_table, railway_table):
    """Sync a single table from local to railway"""
    print(f"\n▶ Syncing: {local_table} → {railway_table}")
    
    # Get columns from both
    local_cols = get_columns(local_conn, local_table)
    railway_cols = get_columns(railway_conn, railway_table)
    
    if not railway_cols:
        print(f"   ✗ Railway table '{railway_table}' doesn't exist!")
        return False
    
    if not local_cols:
        print(f"   ✗ Local table '{local_table}' doesn't exist!")
        return False
    
    # Find common columns (exclude id)
    common_cols = (local_cols & railway_cols) - {'id'}
    
    if not common_cols:
        print(f"   ⚠️  No common columns!")
        print(f"      Local has: {sorted(list(local_cols)[:5])}...")
        print(f"      Railway has: {sorted(list(railway_cols)[:5])}...")
        return False
    
    print(f"   📊 Syncing {len(common_cols)} common columns")
    
    local_cursor = local_conn.cursor(dictionary=True)
    railway_cursor = railway_conn.cursor()
    
    try:
        # Get data from local
        cols_list = list(common_cols)
        cols_str = ', '.join([f"`{col}`" for col in cols_list])
        
        local_cursor.execute(f"SELECT {cols_str} FROM `{local_table}`")
        rows = local_cursor.fetchall()
        
        if not rows:
            print(f"   ℹ No data in local table")
            return True
        
        print(f"   📊 Found {len(rows)} rows in local")
        
        # Clear Railway table
        print(f"   🗑️ Clearing Railway table...")
        railway_cursor.execute(f"DELETE FROM `{railway_table}`")
        print(f"   ✓ Deleted {railway_cursor.rowcount} rows")
        
        # Insert data
        placeholders = ', '.join(['%s'] * len(cols_list))
        insert_cols = ', '.join([f"`{col}`" for col in cols_list])
        insert_query = f"INSERT INTO `{railway_table}` ({insert_cols}) VALUES ({placeholders})"
        
        batch_size = 100
        total = 0
        
        for i in range(0, len(rows), batch_size):
            batch = rows[i:i + batch_size]
            values = [tuple(row[col] for col in cols_list) for row in batch]
            railway_cursor.executemany(insert_query, values)
            total += len(values)
            if total % 500 == 0 or i + batch_size >= len(rows):
                print(f"   📝 Inserted {total}/{len(rows)} rows...")
        
        railway_conn.commit()
        
        # Verify
        railway_cursor.execute(f"SELECT COUNT(*) FROM `{railway_table}`")
        count = railway_cursor.fetchone()[0]
        print(f"   ✅ Success! Railway now has {count} rows")
        
        return True
        
    except Error as e:
        print(f"   ✗ Error: {e}")
        railway_conn.rollback()
        return False
    finally:
        local_cursor.close()
        railway_cursor.close()

def main():
    print("\n" + "="*70)
    print("  🚂 SYNC LOCAL → RAILWAY (CASE-INSENSITIVE)")
    print("="*70)
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70 + "\n")
    
    # Table mappings (local name → railway lowercase name)
    tables = [
        ('tax_summit_master_data', 'tax_summit_master_data'),
        ('Tax_Persons_details', 'tax_persons_details'),
        ('CFO_Persons_details', 'cfo_persons_details'),
        ('Other_Persons_Details', 'other_persons_details'),
        ('Tax_Persons_Analysis', 'tax_persons_analysis'),
        ('CFO_Persons_Analysis', 'cfo_persons_analysis'),
        ('Other_Persons_Analysis', 'other_persons_analysis'),
    ]
    
    # Connect
    print("🔌 Connecting to databases...\n")
    local_conn = connect_to_db('local')
    railway_conn = connect_to_db('railway')
    
    if not local_conn or not railway_conn:
        print("\n❌ Connection failed!")
        return
    
    print("\n📋 Starting sync...\n")
    
    success = 0
    failed = []
    
    for local_table, railway_table in tables:
        if sync_table(local_conn, railway_conn, local_table, railway_table):
            success += 1
        else:
            failed.append(local_table)
    
    # Close connections
    if local_conn.is_connected():
        local_conn.close()
    if railway_conn.is_connected():
        railway_conn.close()
    
    # Summary
    print("\n" + "="*70)
    if failed:
        print(f"⚠️  Partial Success: {success}/{len(tables)} tables synced")
        print(f"   Failed: {', '.join(failed)}")
    else:
        print(f"✅ Complete Success! {success}/{len(tables)} tables synced")
    print("="*70)
    
    print("\n📝 Next step:")
    print("  Run: python test_railway.py")
    print()

if __name__ == "__main__":
    main()