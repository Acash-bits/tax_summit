#!/usr/bin/env python3
"""
Tax Summit Database Migration Tool
Usage:
  python migrate.py              # Run migrations locally
  python migrate.py --railway    # Run migrations on Railway
  python migrate.py --status     # Check migration status
  python migrate.py --rollback   # Rollback last migration
"""

import sys
import os
from dotenv import load_dotenv

# Add migrations directory to Python path
# Add migrations directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'migrations'))

# Import from migrations folder
from migrations.migration_manager import MigrationManager
from migrations.versions import MIGRATIONS

load_dotenv()

def print_header(use_railway):
    print("\n" + "="*60)
    print("🚀 TAX SUMMIT DATABASE MIGRATION TOOL")
    print("="*60)
    print(f"Target Environment: {'🌐 RAILWAY' if use_railway else '💻 LOCAL'}")
    print("="*60 + "\n")

def show_status(manager):
    """Show migration status"""
    if not manager.connection:
        print("❌ Cannot check status - no database connection")
        return
    
    manager.create_migrations_table()
    applied = manager.get_applied_migrations()
    
    print("\n📊 Migration Status")
    print("="*60)
    print(f"Total migrations defined: {len(MIGRATIONS)}")
    print(f"Applied migrations: {len(applied)}")
    print(f"Pending migrations: {len(MIGRATIONS) - len(applied)}")
    print("\n📝 Migration List:\n")
    
    for migration in MIGRATIONS:
        status = "✓ Applied" if migration['name'] in applied else "⏳ Pending"
        print(f"  {status} | {migration['name']}")
    
    print("="*60)

def main():
    # Parse command line arguments
    use_railway = '--railway' in sys.argv
    show_status_only = '--status' in sys.argv
    do_rollback = '--rollback' in sys.argv
    
    print_header(use_railway)
    
    # Create migration manager
    manager = MigrationManager(use_railway=use_railway)
    
    if not manager.connection:
        print("\n❌ FATAL: Failed to connect to database")
        print("   Please check your .env file and database credentials")
        sys.exit(1)
    
    try:
        if show_status_only:
            show_status(manager)
        elif do_rollback:
            print("🔄 Rolling back last migration...\n")
            manager.rollback_last_migration(MIGRATIONS)
        else:
            manager.run_migrations(MIGRATIONS)
    except KeyboardInterrupt:
        print("\n\n⚠️  Migration interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        manager.close()
    
    print("\n✨ Done!\n")

if __name__ == "__main__":
    if '--help' in sys.argv or '-h' in sys.argv:
        print(__doc__)
        sys.exit(0)
    main()