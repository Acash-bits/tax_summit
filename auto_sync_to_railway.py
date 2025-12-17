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
        print("\n🔧 Initializing Database Syncer...")
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
                print(f"\n📍 LOCAL Connection Config:")
            else:  # railway
                config = {
                    'host': os.getenv("RAILWAY_DB_HOST", os.getenv("DB_HOST")),
                    'user': os.getenv("RAILWAY_DB_USER", os.getenv("DB_USER")),
                    'password': os.getenv("RAILWAY_DB_PASS", os.getenv("DB_PASS")),
                    'database': os.getenv("RAILWAY_DB_NAME", os.getenv("DB_NAME")),
                    'port': int(os.getenv("RAILWAY_DB_PORT", os.getenv("DB_PORT", 3306)))
                }
                print(f"\n🚂 RAILWAY Connection Config:")
            
            # Print config (hide password)
            print(f"   Host: {config['host']}")
            print(f"   Port: {config['port']}")
            print(f"   User: {config['user']}")
            print(f"   Database: {config['database']}")
            print(f"   Password: {'*' * len(str(config['password']))}")
            
            connection = mysql.connector.connect(**config)
            
            if connection.is_connected():
                print(f"   ✓ Connected to {env_type.upper()} database")
                
                # Test query
                cursor = connection.cursor()
                cursor.execute("SELECT COUNT(*) FROM tax_summit_master_data")
                count = cursor.fetchone()[0]
                print(f"   ℹ Master table has {count} records")
                cursor.close()
                
                return connection
            
        except Error as e:
            print(f"   ✗ Error connecting to {env_type} database: {e}")
            print(f"   Error Code: {e.errno}")
            print(f"   SQL State: {e.sqlstate}")
            return None
    
    def get_table_hash(self, connection, table_name):
        """Get a hash representing the current state of a table"""
        cursor = connection.cursor()
        try:
            # Get row count
            cursor.execute(f"SELECT COUNT(*) FROM `{table_name}`")
            count = cursor.fetchone()[0]
            
            # Get sample of data for hash (first 100 rows ordered by id)
            cursor.execute(f"SELECT * FROM `{table_name}` ORDER BY id LIMIT 100")
            rows = cursor.fetchall()
            
            # Create hash from data
            data_str = json.dumps(rows, default=str, sort_keys=True)
            table_hash = hashlib.md5(data_str.encode()).hexdigest()
            
            return {'count': count, 'hash': table_hash}
        except Error as e:
            print(f"   ⚠️ Error getting hash for {table_name}: {e}")
            return None
        finally:
            cursor.close()
    
    def load_sync_state(self):
        """Load last sync state from file"""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                    print(f"   📂 Loaded previous sync state ({len(state)} tables tracked)")
                    return state
        except Exception as e:
            print(f"   ⚠️ Could not load sync state: {e}")
        
        print("   📂 No previous sync state found (first run)")
        return {}
    
    def save_sync_state(self, state):
        """Save current sync state to file"""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
            print(f"   💾 Saved sync state to {self.state_file}")
        except Exception as e:
            print(f"   ⚠️ Could not save sync state: {e}")
    
    def sync_table(self, table_name):
        """Sync a single table from local to railway"""
        if not self.local_conn or not self.railway_conn:
            print(f"   ✗ Cannot sync {table_name} - missing connection")
            return False
        
        print(f"\n▶ Syncing table: {table_name}")
        
        local_cursor = self.local_conn.cursor(dictionary=True)
        railway_cursor = self.railway_conn.cursor()
        
        try:
            # Get all data from local
            local_cursor.execute(f"SELECT * FROM `{table_name}`")
            local_rows = local_cursor.fetchall()
            
            if not local_rows:
                print(f"   ℹ No data in local {table_name}")
                return True
            
            print(f"   📊 Found {len(local_rows)} rows in local database")
            
            # Get columns (exclude 'id' if it's auto-increment)
            columns = list(local_rows[0].keys())
            
            # Check if 'id' should be excluded (auto-increment primary key)
            try:
                railway_cursor.execute(f"SHOW COLUMNS FROM `{table_name}` LIKE 'id'")
                id_col_info = railway_cursor.fetchone()
                if id_col_info and 'auto_increment' in str(id_col_info).lower():
                    columns_without_id = [col for col in columns if col != 'id']
                    print(f"   🔑 Excluding auto-increment 'id' column")
                else:
                    columns_without_id = columns
            except:
                columns_without_id = [col for col in columns if col != 'id']
            
            # Clear railway table
            print(f"   🗑️ Clearing Railway table...")
            railway_cursor.execute(f"DELETE FROM `{table_name}`")
            deleted_count = railway_cursor.rowcount
            print(f"   ✓ Deleted {deleted_count} existing rows")
            
            # Prepare insert statement
            placeholders = ', '.join(['%s'] * len(columns_without_id))
            cols_str = ', '.join([f"`{col}`" for col in columns_without_id])
            insert_query = f"INSERT INTO `{table_name}` ({cols_str}) VALUES ({placeholders})"
            
            # Insert in batches
            batch_size = 100
            total_inserted = 0
            
            for i in range(0, len(local_rows), batch_size):
                batch = local_rows[i:i + batch_size]
                rows_to_insert = []
                
                for row in batch:
                    row_data = tuple(row[col] for col in columns_without_id)
                    rows_to_insert.append(row_data)
                
                railway_cursor.executemany(insert_query, rows_to_insert)
                total_inserted += len(rows_to_insert)
                
                if total_inserted % 500 == 0 or i + batch_size >= len(local_rows):
                    print(f"   📝 Inserted {total_inserted}/{len(local_rows)} rows...")
            
            self.railway_conn.commit()
            
            # Verify
            railway_cursor.execute(f"SELECT COUNT(*) FROM `{table_name}`")
            railway_count = railway_cursor.fetchone()[0]
            
            print(f"   ✓ Synced {total_inserted} rows to Railway")
            print(f"   ✓ Verification: Railway now has {railway_count} rows")
            
            return True
            
        except Error as e:
            print(f"   ✗ Error syncing {table_name}: {e}")
            print(f"   Error Code: {e.errno}")
            self.railway_conn.rollback()
            return False
        finally:
            local_cursor.close()
            railway_cursor.close()
    
    def check_and_sync(self, force=False):
        """Check for changes and sync if needed"""
        print("\n" + "="*70)
        print(f"  SYNC CHECK - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)
        
        if not self.local_conn or not self.railway_conn:
            print("✗ Database connections not available")
            return
        
        previous_state = self.load_sync_state()
        current_state = {}
        tables_changed = []
        
        print("\n📋 Checking for changes in each table...")
        
        for table in self.tables_to_sync:
            print(f"\n   Checking: {table}")
            
            local_hash = self.get_table_hash(self.local_conn, table)
            
            if local_hash:
                current_state[table] = local_hash
                print(f"   Local: {local_hash['count']} rows, hash: {local_hash['hash'][:8]}...")
                
                # Check if changed or force sync
                if force:
                    tables_changed.append(table)
                    print(f"   🔄 FORCED SYNC")
                elif table not in previous_state:
                    tables_changed.append(table)
                    print(f"   📝 NEW TABLE - needs sync")
                elif previous_state[table] != local_hash:
                    tables_changed.append(table)
                    prev_hash = previous_state[table]
                    print(f"   📝 CHANGED")
                    print(f"   Previous: {prev_hash['count']} rows, hash: {prev_hash['hash'][:8]}...")
                else:
                    print(f"   ✓ No changes")
        
        if tables_changed:
            print(f"\n🔄 Syncing {len(tables_changed)} table(s)...")
            print("="*70)
            
            success_count = 0
            for table in tables_changed:
                success = self.sync_table(table)
                if success:
                    success_count += 1
                else:
                    print(f"   ⚠️ Failed to sync {table}")
            
            # Save new state
            self.save_sync_state(current_state)
            
            print("\n" + "="*70)
            print(f"✅ Sync complete! {success_count}/{len(tables_changed)} tables synced")
            print("="*70)
        else:
            print("\n" + "="*70)
            print("✓ No changes detected - databases are in sync")
            print("="*70)
    
    def run_continuous(self, interval_seconds=300):
        """Run sync continuously at specified interval"""
        print("\n" + "="*70)
        print("  🚀 AUTO-SYNC TO RAILWAY - STARTED")
        print("="*70)
        print(f"  Monitoring interval: {interval_seconds} seconds ({interval_seconds/60:.1f} minutes)")
        print(f"  Tables being monitored: {len(self.tables_to_sync)}")
        print("  Press Ctrl+C to stop")
        print("="*70)
        
        try:
            iteration = 0
            while True:
                iteration += 1
                print(f"\n\n{'='*70}")
                print(f"  ITERATION #{iteration}")
                print(f"{'='*70}")
                
                self.check_and_sync()
                
                print(f"\n⏰ Next check in {interval_seconds} seconds...")
                print(f"   Next check at: {datetime.fromtimestamp(time.time() + interval_seconds).strftime('%Y-%m-%d %H:%M:%S')}")
                time.sleep(interval_seconds)
        except KeyboardInterrupt:
            print("\n\n⚠️  Sync service stopped by user")
        finally:
            self.close()
    
    def close(self):
        """Close database connections"""
        if self.local_conn and self.local_conn.is_connected():
            self.local_conn.close()
            print("   ✓ Local connection closed")
        if self.railway_conn and self.railway_conn.is_connected():
            self.railway_conn.close()
            print("   ✓ Railway connection closed")


if __name__ == "__main__":
    import sys
    
    print("\n" + "="*70)
    print("  🚂 RAILWAY DATABASE SYNC UTILITY")
    print("="*70)
    
    syncer = DatabaseSyncer()
    
    # Check if connections were established
    if not syncer.local_conn:
        print("\n❌ FAILED: Could not connect to LOCAL database")
        print("   Please check your .env file DB_HOST, DB_USER, DB_PASS, DB_NAME")
        sys.exit(1)
    
    if not syncer.railway_conn:
        print("\n❌ FAILED: Could not connect to RAILWAY database")
        print("   Please check your .env file:")
        print("   - RAILWAY_DB_HOST")
        print("   - RAILWAY_DB_USER")
        print("   - RAILWAY_DB_PASS")
        print("   - RAILWAY_DB_NAME")
        print("   - RAILWAY_DB_PORT")
        sys.exit(1)
    
    print("\n✅ Both connections established successfully!")
    
    if '--once' in sys.argv:
        # Run sync once and exit
        print("\n🔄 Running ONE-TIME sync...")
        force_sync = '--force' in sys.argv
        if force_sync:
            print("   (FORCE mode enabled - will sync all tables)")
        syncer.check_and_sync(force=force_sync)
        syncer.close()
    else:
        # Run continuously (default: every 5 minutes)
        interval = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 300
        syncer.run_continuous(interval_seconds=interval)