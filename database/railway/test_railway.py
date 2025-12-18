import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

print("\n" + "="*70)
print("🧪 TESTING RAILWAY DATABASE CONNECTION")
print("="*70 + "\n")

config = {
    'host': os.getenv("RAILWAY_DB_HOST"),
    'user': os.getenv("RAILWAY_DB_USER"),
    'password': os.getenv("RAILWAY_DB_PASS"),
    'database': os.getenv("RAILWAY_DB_NAME"),
    'port': int(os.getenv("RAILWAY_DB_PORT", 3306))
}

print("📋 Configuration:")
print(f"  Host: {config['host']}")
print(f"  Port: {config['port']}")
print(f"  User: {config['user']}")
print(f"  Database: {config['database']}")
print(f"  Password: {'*' * len(str(config['password']))}\n")

try:
    print("🔌 Attempting to connect...")
    connection = mysql.connector.connect(**config)
    
    if connection.is_connected():
        print("✅ SUCCESS! Connected to Railway database\n")
        
        cursor = connection.cursor()
        
        # Check tables
        print("📊 Checking tables...")
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        
        if tables:
            print(f"✓ Found {len(tables)} tables:\n")
            for table in tables:
                # Get row count for each table
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM `{table[0]}`")
                    count = cursor.fetchone()[0]
                    print(f"  📁 {table[0]}: {count} rows")
                except:
                    print(f"  📁 {table[0]}: (unable to count)")
        else:
            print("⚠️  No tables found in Railway database!")
            print("   You need to set up the database schema first.")
        
        cursor.close()
        connection.close()
        print("\n✓ Connection closed successfully")
        print("\n" + "="*70)
        print("✅ Railway database is ready!")
        print("="*70)
        
except mysql.connector.Error as e:
    print(f"\n❌ FAILED to connect!")
    print(f"\n🔍 Error Details:")
    print(f"  Error Code: {e.errno}")
    print(f"  Error Message: {e.msg}")
    print(f"  SQL State: {e.sqlstate}")
    
    print(f"\n💡 Common Solutions:")
    print(f"  1. Check that Railway MySQL service is running")
    print(f"  2. Verify credentials in Railway dashboard > MySQL > Variables")
    print(f"  3. Make sure your IP is not blocked (Railway should allow all IPs)")
    print(f"  4. Try regenerating the Railway database password")
    
except Exception as e:
    print(f"\n❌ Unexpected error: {e}")