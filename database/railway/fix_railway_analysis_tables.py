import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv

load_dotenv()

def connect_to_railway():
    """Connect to Railway database"""
    try:
        connection = mysql.connector.connect(
            host=os.getenv("RAILWAY_DB_HOST"),
            user=os.getenv("RAILWAY_DB_USER"),
            password=os.getenv("RAILWAY_DB_PASS"),
            database=os.getenv("RAILWAY_DB_NAME"),
            port=int(os.getenv("RAILWAY_DB_PORT", 3306))
        )
        if connection.is_connected():
            print("✓ Connected to Railway database")
            return connection
    except Error as e:
        print(f"✗ Error: {e}")
        return None

def remove_unique_constraints(connection):
    """Remove UNIQUE constraints from Phone_Number columns in analysis tables"""
    cursor = connection.cursor()
    
    print("\n" + "="*70)
    print("  🔧 REMOVING UNIQUE CONSTRAINTS FROM ANALYSIS TABLES")
    print("="*70 + "\n")
    
    tables = [
        ('tax_persons_analysis', 'Phone_Number'),
        ('cfo_persons_analysis', 'Phone_Number_4'),
        ('other_persons_analysis', 'Phone_Number_10')
    ]
    
    for table, phone_col in tables:
        print(f"[{table}] Checking indexes on {phone_col}...")
        
        try:
            # Show all indexes on this column
            cursor.execute(f"SHOW INDEX FROM {table} WHERE Column_name = '{phone_col}'")
            indexes = cursor.fetchall()
            
            if not indexes:
                print(f"    ℹ️  No indexes found")
                continue
            
            # Drop each index
            for index in indexes:
                index_name = index[2]  # Key_name is at position 2
                try:
                    cursor.execute(f"ALTER TABLE {table} DROP INDEX {index_name}")
                    print(f"    ✓ Dropped index: {index_name}")
                except Error as e:
                    if e.errno == 1091:  # Can't DROP; check that column/key exists
                        print(f"    ℹ️  Index {index_name} already removed")
                    else:
                        print(f"    ⚠️  Could not drop {index_name}: {e}")
            
            connection.commit()
            
        except Error as e:
            print(f"    ⚠️  Error: {e}")
    
    print("\n✅ UNIQUE constraints removed from all analysis tables!")
    cursor.close()

def add_composite_unique_constraints(connection):
    """Add composite UNIQUE constraints (Phone + Client_Name)"""
    cursor = connection.cursor()
    
    print("\n" + "="*70)
    print("  🔧 ADDING COMPOSITE UNIQUE CONSTRAINTS")
    print("="*70 + "\n")
    
    print("This allows same phone for different clients.\n")
    
    constraints = [
        ('tax_persons_analysis', 'Phone_Number', 'Client_Name'),
        ('cfo_persons_analysis', 'Phone_Number_4', 'Company_Name'),
        ('other_persons_analysis', 'Phone_Number_10', 'Company_Name')
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
            elif e.errno == 1062:  # Duplicate entry
                print(f"    ⚠️  Cannot add: Duplicate data exists")
                print(f"       This is fine - we'll handle duplicates during sync")
            else:
                print(f"    ⚠️  Error: {e}")
    
    cursor.close()

def main():
    print("\n" + "="*70)
    print("  🔧 FIX RAILWAY ANALYSIS TABLES FOR DUPLICATE PHONES")
    print("="*70)
    
    connection = connect_to_railway()
    if not connection:
        return
    
    try:
        # Step 1: Remove UNIQUE constraints
        remove_unique_constraints(connection)
        
        # Step 2: Add composite constraints (optional)
        add_composite_unique_constraints(connection)
        
        print("\n" + "="*70)
        print("  ✅ FIX COMPLETE!")
        print("="*70)
        print("\n📝 Now run:")
        print("   python sync_to_railway_final.py")
        print("\n💡 This will allow duplicate phone numbers across different clients.")
        print("="*70 + "\n")
        
    finally:
        if connection.is_connected():
            connection.close()
            print("✓ Connection closed\n")

if __name__ == "__main__":
    main()