import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

class MigrationManager:
    def __init__(self, use_railway=False):
        self.use_railway = use_railway
        self.connection = self.get_connection()
        
    def get_connection(self):
        """Get database connection using same pattern as your app"""
        try:
            if self.use_railway:
                # Use RAILWAY_ prefixed env vars or fall back to regular ones
                host = os.getenv("RAILWAY_DB_HOST", os.getenv("DB_HOST"))
                user = os.getenv("RAILWAY_DB_USER", os.getenv("DB_USER"))
                password = os.getenv("RAILWAY_DB_PASS", os.getenv("DB_PASS"))
                database = os.getenv("RAILWAY_DB_NAME", os.getenv("DB_NAME"))
                port = int(os.getenv("RAILWAY_DB_PORT", os.getenv("DB_PORT", 3306)))
            else:
                host = os.getenv("DB_HOST")
                user = os.getenv("DB_USER")
                password = os.getenv("DB_PASS")
                database = os.getenv("DB_NAME")
                port = int(os.getenv("DB_PORT", 3306))
            
            connection = mysql.connector.connect(
                host=host,
                user=user,
                password=password,
                database=database,
                port=port
            )
            print(f"✓ Connected to {'Railway' if self.use_railway else 'Local'} database")
            print(f"  Host: {host}")
            print(f"  Database: {database}")
            return connection
        except Error as e:
            print(f"✗ Connection failed: {e}")
            return None
    
    def create_migrations_table(self):
        """Create a table to track applied migrations"""
        if not self.connection:
            print("✗ No database connection")
            return False
            
        cursor = self.connection.cursor()
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    migration_name VARCHAR(255) UNIQUE NOT NULL,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_migration_name (migration_name)
                )
            """)
            self.connection.commit()
            print("✓ Migrations tracking table ready")
            return True
        except Error as e:
            print(f"✗ Failed to create migrations table: {e}")
            return False
        finally:
            cursor.close()
    
    def get_applied_migrations(self):
        """Get list of already applied migrations"""
        cursor = self.connection.cursor()
        try:
            cursor.execute("SELECT migration_name FROM schema_migrations ORDER BY id")
            applied = [row[0] for row in cursor.fetchall()]
            return applied
        except Error as e:
            print(f"✗ Failed to get applied migrations: {e}")
            return []
        finally:
            cursor.close()
    
    def apply_migration(self, migration_name, sql_statements):
        """Apply a migration"""
        cursor = self.connection.cursor()
        try:
            print(f"  ▶ Executing {len(sql_statements)} SQL statement(s)...")
            
            # Execute each SQL statement
            for idx, sql in enumerate(sql_statements, 1):
                sql = sql.strip()
                if sql:  # Skip empty statements
                    print(f"    [{idx}/{len(sql_statements)}] Executing...")
                    cursor.execute(sql)
            
            # Record migration as applied
            cursor.execute(
                "INSERT INTO schema_migrations (migration_name) VALUES (%s)",
                (migration_name,)
            )
            
            self.connection.commit()
            print(f"✓ Applied migration: {migration_name}")
            return True
            
        except Error as e:
            self.connection.rollback()
            print(f"✗ Migration failed: {migration_name}")
            print(f"  Error: {e}")
            return False
        finally:
            cursor.close()
    
    def run_migrations(self, migrations):
        """Run all pending migrations"""
        if not self.connection:
            print("✗ Cannot run migrations without database connection")
            return False
            
        print("\n" + "="*60)
        print("📋 Preparing to run migrations...")
        print("="*60 + "\n")
        
        # Create migrations table if it doesn't exist
        if not self.create_migrations_table():
            return False
        
        # Get already applied migrations
        applied = self.get_applied_migrations()
        print(f"ℹ  Already applied: {len(applied)} migration(s)")
        
        # Find pending migrations
        pending = [m for m in migrations if m['name'] not in applied]
        
        if not pending:
            print("\n✓ All migrations are up to date!")
            print("  No pending migrations to apply.")
            return True
        
        print(f"\n📝 Found {len(pending)} pending migration(s):\n")
        for m in pending:
            print(f"  • {m['name']}")
        
        print("\n" + "-"*60 + "\n")
        
        # Apply each pending migration
        success_count = 0
        for migration in pending:
            print(f"▶ Running: {migration['name']}")
            success = self.apply_migration(migration['name'], migration['up'])
            if success:
                success_count += 1
            else:
                print("\n⚠  Migration stopped due to error")
                print("  Fix the error and run migrations again.")
                return False
            print()
        
        print("="*60)
        print(f"✅ Successfully applied {success_count} migration(s)!")
        print("="*60)
        return True
    
    def rollback_last_migration(self, migrations):
        """Rollback the last applied migration"""
        if not self.connection:
            print("✗ Cannot rollback without database connection")
            return False
            
        applied = self.get_applied_migrations()
        if not applied:
            print("ℹ  No migrations to rollback")
            return True
        
        last_migration_name = applied[-1]
        
        # Find the migration in our list
        migration = next((m for m in migrations if m['name'] == last_migration_name), None)
        
        if not migration:
            print(f"✗ Migration '{last_migration_name}' not found in migration list")
            return False
        
        if 'down' not in migration or not migration['down']:
            print(f"✗ No rollback defined for migration '{last_migration_name}'")
            return False
        
        cursor = self.connection.cursor()
        try:
            print(f"▶ Rolling back: {last_migration_name}")
            
            # Execute rollback statements
            for sql in migration['down']:
                if sql.strip():
                    cursor.execute(sql)
            
            # Remove from migrations table
            cursor.execute(
                "DELETE FROM schema_migrations WHERE migration_name = %s",
                (last_migration_name,)
            )
            
            self.connection.commit()
            print(f"✓ Rolled back migration: {last_migration_name}")
            return True
            
        except Error as e:
            self.connection.rollback()
            print(f"✗ Rollback failed: {e}")
            return False
        finally:
            cursor.close()
    
    def close(self):
        """Close database connection"""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            print("\n✓ Database connection closed")