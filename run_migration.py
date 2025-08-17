#!/usr/bin/env python3
"""
Database migration script for Discord Rating Bot Enhanced Features
Runs the migration to add achievements, tournaments, and security tables
"""

import asyncio
import asyncpg
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def run_migration():
    """Run the enhanced features migration"""
    
    # Get database connection details
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL not found in environment variables")
        sys.exit(1)
    
    try:
        # Parse connection string
        if database_url.startswith("postgresql+asyncpg://"):
            database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
        
        # Connect to database
        print("🔌 Connecting to database...")
        conn = await asyncpg.connect(database_url)
        
        print("✅ Connected to database successfully")
        
        # Read migration file
        migration_file = "database/005_enhanced_features.sql"
        try:
            with open(migration_file, 'r', encoding='utf-8') as f:
                migration_sql = f.read()
        except FileNotFoundError:
            print(f"❌ Migration file not found: {migration_file}")
            sys.exit(1)
        
        print(f"📖 Reading migration file: {migration_file}")
        
        # Split SQL into individual statements
        statements = []
        current_statement = ""
        
        for line in migration_sql.split('\n'):
            line = line.strip()
            
            # Skip comments and empty lines
            if line.startswith('--') or not line:
                continue
            
            current_statement += line + " "
            
            # Check if statement ends with semicolon
            if line.endswith(';'):
                statements.append(current_statement.strip())
                current_statement = ""
        
        # Add any remaining statement
        if current_statement.strip():
            statements.append(current_statement.strip())
        
        print(f"📝 Found {len(statements)} SQL statements to execute")
        
        # Execute migration statements
        print("🚀 Starting migration...")
        
        for i, statement in enumerate(statements, 1):
            try:
                print(f"📋 Executing statement {i}/{len(statements)}...")
                
                # Skip certain statements that might cause issues
                if "CREATE EXTENSION" in statement and "uuid-ossp" in statement:
                    print("⏭️  Skipping UUID extension (may already exist)")
                    continue
                
                await conn.execute(statement)
                print(f"✅ Statement {i} executed successfully")
                
            except Exception as e:
                # Check if it's a "already exists" error
                if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                    print(f"⚠️  Statement {i} skipped (already exists): {str(e)[:100]}...")
                else:
                    print(f"❌ Error executing statement {i}: {e}")
                    print(f"Statement: {statement[:200]}...")
                    
                    # Ask user if they want to continue
                    response = input("\n❓ Continue with migration? (y/n): ").lower()
                    if response != 'y':
                        print("🛑 Migration aborted by user")
                        break
        
        print("🎉 Migration completed!")
        
        # Verify tables were created
        print("\n🔍 Verifying migration...")
        
        # Check achievements table
        try:
            result = await conn.fetchval("SELECT COUNT(*) FROM achievements")
            print(f"✅ Achievements table: {result} records")
        except Exception as e:
            print(f"❌ Achievements table check failed: {e}")
        
        # Check tournaments table
        try:
            result = await conn.fetchval("SELECT COUNT(*) FROM tournaments")
            print(f"✅ Tournaments table: {result} records")
        except Exception as e:
            print(f"❌ Tournaments table check failed: {e}")
        
        # Check security tables
        try:
            result = await conn.fetchval("SELECT COUNT(*) FROM security_events")
            print(f"✅ Security events table: {result} records")
        except Exception as e:
            print(f"❌ Security events table check failed: {e}")
        
        # Check views
        try:
            result = await conn.fetchval("SELECT COUNT(*) FROM tournament_overview")
            print(f"✅ Tournament overview view: {result} records")
        except Exception as e:
            print(f"❌ Tournament overview view check failed: {e}")
        
        print("\n🎯 Migration verification completed!")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        sys.exit(1)
    
    finally:
        # Close connection
        if 'conn' in locals():
            await conn.close()
            print("🔌 Database connection closed")

async def check_database_connection():
    """Check if database is accessible"""
    try:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            print("❌ DATABASE_URL not found in environment variables")
            return False
        
        if database_url.startswith("postgresql+asyncpg://"):
            database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
        
        conn = await asyncpg.connect(database_url)
        await conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

async def main():
    """Main function"""
    print("🚀 Discord Rating Bot - Enhanced Features Migration")
    print("=" * 50)
    
    # Check database connection
    print("🔌 Checking database connection...")
    if not await check_database_connection():
        print("❌ Cannot proceed without database connection")
        sys.exit(1)
    
    print("✅ Database connection verified")
    
    # Confirm migration
    print("\n⚠️  This migration will:")
    print("   • Create achievements system tables")
    print("   • Create tournament system tables")
    print("   • Create security system tables")
    print("   • Add indexes and functions")
    print("   • Create database views")
    
    response = input("\n❓ Proceed with migration? (y/n): ").lower()
    if response != 'y':
        print("🛑 Migration cancelled by user")
        sys.exit(0)
    
    # Run migration
    await run_migration()
    
    print("\n🎉 Migration completed successfully!")
    print("🚀 You can now start the bot with enhanced features!")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Migration interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)