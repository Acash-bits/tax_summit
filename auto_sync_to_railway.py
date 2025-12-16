import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv
import time
from datetime import datetime
import hashlib
import json

load_dotenv()

class DatabaseSyncer:
    def __init__(self):
        self.local_conn = self.connect_to_db('local')
        self.railway_conn = self.connect_to_db('railway')
        self.tables_to_sync = [
            'tax_summit_master_data',
            'Tax_Persons_details',
            'CFO_Persons_details',
            'Other_Persons_Details',
            'Tax_Persons_Analysis',
            'CFO_Persons_Analysis',
            'Other_Persons_Analysis'
        ]
        self.state_file = 'sync_state.json'
        
    def connect_to_db(self, env_type):
        """Connect to local or railway database"""
        try:
            if env_type == 'local':
                config = {
                    'host': os.getenv("DB_HOST"),
                    'user': os.getenv("DB_USER"),
                    'password': os.getenv("DB_PASS"),
                    'database': os.getenv("DB_NAME"),
                    'port': int(os.getenv("DB_PORT", 3306))
                }
            else:  # railway
                config = {
                    'host': os.getenv("RAILWAY_DB_HOST", os.getenv("DB_HOST")),
                    'user': os.getenv("RAILWAY_DB_USER", os.getenv("DB_USER")),
                    'password': os.getenv("RAILWAY_DB_PASS", os.getenv("DB_PASS")),
                    'database': os.getenv("RAILWAY_DB_NAME", os.getenv("DB_NAME")),
                    'port': int(os.getenv("RAILWAY_DB_PORT", os.getenv("DB_PORT", 11949)))
                }
            
            connection = mysql.connector.connect(**config)
            print(f"✓ Connected to {env_type.upper()} database")
            return connection
        except Error as e:
            print(f"✗ Error connecting to {env_type} database: {e}")
            return None
    
    def get_table_hash(self, connection, table_name,):
        """Get a hash representing the current state of a table"""
        cursor = connection.cursor()
        try:
            # Get row count and last modified time
            cursor.execute(f"SELECT COUNT(*) FROM `{table_name}`")
            count = cursor.fetchone()[0]
            
            # Get checksum of all data (simplified version)
            cursor.execute(f"SELECT * FROM `{table_name}` ORDER BY id")
            rows = cursor.fetchall()
            
            # Create hash from data
            data_str = json.dumps(rows, default=str, sort_keys=True)
            table_hash = hashlib.md5(data_str.encode()).hexdigest()
            
            return {'count': count, 'hash': table_hash}
        except Error as e:
            print(f"Error getting hash for {table_name}: {e}")
            return None
        finally:
            cursor.close()
    
    def load_sync_state(self):
        """Load last sync state from file"""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    return json.load(f)
        except:
            pass
        return {}
    
    def save_sync_state(self, state):
        """Save current sync state to file"""
        with open(self.state_file, 'w') as f:
            json.dump(state, f, indent=2)
    
    def sync_table(self, table_name):
        """Sync a single table from local to railway"""
        if not self.local_conn or not self.railway_conn:
            print(f"✗ Cannot sync {table_name} - missing connection")
            return False
        
        print(f"\n▶ Syncing table: {table_name}")
        
        local_cursor = self.local_conn.cursor(dictionary=True)
        railway_cursor = self.railway_conn.cursor()
        
        try:
            # Get all data from local
            local_cursor.execute(f"SELECT * FROM `{table_name}`")
            local_rows = local_cursor.fetchall()
            
            if not local_rows:
                print(f"  ℹ No data in local {table_name}")
                return True
            
            # Get columns
            columns = list(local_rows[0].keys())
            columns_without_id = [col for col in columns if col != 'id']
            
            # Clear railway table (be careful!)
            railway_cursor.execute(f"DELETE FROM `{table_name}`")
            
            # Insert all local data to railway
            placeholders = ', '.join(['%s'] * len(columns_without_id))
            cols_str = ', '.join([f"`{col}`" for col in columns_without_id])
            
            insert_query = f"INSERT INTO `{table_name}` ({cols_str}) VALUES ({placeholders})"
            
            rows_to_insert = []
            for row in local_rows:
                row_data = tuple(row[col] for col in columns_without_id)
                rows_to_insert.append(row_data)
            
            railway_cursor.executemany(insert_query, rows_to_insert)
            self.railway_conn.commit()
            
            print(f"  ✓ Synced {len(local_rows)} rows to Railway")
            return True
            
        except Error as e:
            print(f"  ✗ Error syncing {table_name}: {e}")
            self.railway_conn.rollback()
            return False
        finally:
            local_cursor.close()
            railway_cursor.close()
    
    def check_and_sync(self):
        """Check for changes and sync if needed"""
        print("\n" + "="*70)
        print(f"  CHECKING FOR CHANGES - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)
        
        if not self.local_conn or not self.railway_conn:
            print("✗ Database connections not available")
            return
        
        previous_state = self.load_sync_state()
        current_state = {}
        tables_changed = []
        
        for table in self.tables_to_sync:
            local_hash = self.get_table_hash(self.local_conn, table)
            
            if local_hash:
                current_state[table] = local_hash
                
                # Check if changed
                if table not in previous_state or previous_state[table] != local_hash:
                    tables_changed.append(table)
                    print(f"📝 Change detected in: {table}")
        
        if tables_changed:
            print(f"\n🔄 Syncing {len(tables_changed)} changed table(s)...")
            
            for table in tables_changed:
                success = self.sync_table(table)
                if not success:
                    print(f"⚠️  Failed to sync {table}")
            
            # Save new state
            self.save_sync_state(current_state)
            print("\n✅ Sync complete!")
        else:
            print("\n✓ No changes detected - databases are in sync")
    
    def run_continuous(self, interval_seconds=300):
        """Run sync continuously at specified interval"""
        print("\n" + "="*70)
        print("  🚀 AUTO-SYNC TO RAILWAY - STARTED")
        print("="*70)
        print(f"  Monitoring interval: {interval_seconds} seconds ({interval_seconds/60} minutes)")
        print(f"  Tables being monitored: {len(self.tables_to_sync)}")
        print("  Press Ctrl+C to stop")
        print("="*70)
        
        try:
            while True:
                self.check_and_sync()
                print(f"\n⏰ Next check in {interval_seconds} seconds...")
                time.sleep(interval_seconds)
        except KeyboardInterrupt:
            print("\n\n⚠️  Sync service stopped by user")
        finally:
            self.close()
    
    def close(self):
        """Close database connections"""
        if self.local_conn and self.local_conn.is_connected():
            self.local_conn.close()
        if self.railway_conn and self.railway_conn.is_connected():
            self.railway_conn.close()
        print("✓ Database connections closed")


if __name__ == "__main__":
    import sys
    
    syncer = DatabaseSyncer()
    
    if '--once' in sys.argv:
        # Run sync once and exit
        syncer.check_and_sync()
        syncer.close()
    else:
        # Run continuously (default: every 5 minutes)
        interval = int(sys.argv[1]) if len(sys.argv) > 1 else 300
        syncer.run_continuous(interval_seconds=interval)