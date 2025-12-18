import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv

load_dotenv()

def connect_railway():
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

def drop_all_tables():
    """Drop all existing tables"""
    conn = connect_railway()
    if not conn:
        return
    
    cursor = conn.cursor()
    
    try:
        print("\n🔍 Finding all tables in Railway database...")
        cursor.execute("SHOW TABLES")
        tables = [row[0] for row in cursor.fetchall()]
        
        if not tables:
            print("✓ No tables found")
            return
        
        print(f"📋 Found {len(tables)} tables:")
        for table in tables:
            print(f"   • {table}")
        
        print("\n🗑️  Dropping all tables...")
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
        
        for table in tables:
            try:
                cursor.execute(f"DROP TABLE IF EXISTS `{table}`")
                print(f"   ✓ Dropped: {table}")
            except Error as e:
                print(f"   ✗ Failed to drop {table}: {e}")
        
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
        conn.commit()
        
        print("\n✅ All tables dropped successfully!")
        
        # Verify
        cursor.execute("SHOW TABLES")
        remaining = cursor.fetchall()
        if not remaining:
            print("✓ Verified: Railway database is now empty")
        else:
            print(f"⚠️  Warning: {len(remaining)} tables still remain")
        
    except Error as e:
        print(f"✗ Error: {e}")
        conn.rollback()
    finally:
        cursor.close()
        if conn.is_connected():
            conn.close()
            print("\n✓ Connection closed")

if __name__ == "__main__":
    import sys
    
    print("\n" + "="*70)
    print("  🗑️  DROP ALL RAILWAY TABLES")
    print("="*70)
    print("\n⚠️  WARNING: This will delete ALL tables in Railway database!")
    
    if '--yes' not in sys.argv:
        response = input("\nType 'yes' to continue: ")
        if response.lower() != 'yes':
            print("Cancelled.")
            sys.exit(0)
    
    drop_all_tables()