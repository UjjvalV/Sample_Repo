from django.core.management.base import BaseCommand
from django.db import connection
import os
import time

class Command(BaseCommand):
    help = 'Fix SQLite database lock issues and optimize database settings'

    def add_arguments(self, parser):
        parser.add_argument(
            '--check',
            action='store_true',
            help='Check database status without making changes',
        )

    def handle(self, *args, **options):
        check_only = options['check']
        
        self.stdout.write(self.style.SUCCESS('=== SQLite Database Lock Fix ==='))
        
        # Check database file permissions
        db_path = 'attendance/db.sqlite3'
        if os.path.exists(db_path):
            self.stdout.write(f"Database file exists: {db_path}")
            
            # Check file permissions
            import stat
            file_stat = os.stat(db_path)
            permissions = stat.filemode(file_stat.st_mode)
            self.stdout.write(f"Database file permissions: {permissions}")
            
            # Check if file is writable
            if os.access(db_path, os.W_OK):
                self.stdout.write(self.style.SUCCESS("✓ Database file is writable"))
            else:
                self.stdout.write(self.style.ERROR("✗ Database file is not writable"))
        else:
            self.stdout.write(self.style.WARNING(f"Database file not found: {db_path}"))
        
        if check_only:
            self.stdout.write(self.style.SUCCESS("Check completed (no changes made)"))
            return
        
        # Test database connection
        self.stdout.write("\nTesting database connection...")
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                self.stdout.write(self.style.SUCCESS("✓ Database connection successful"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ Database connection failed: {e}"))
            return
        
        # Apply SQLite optimizations
        self.stdout.write("\nApplying SQLite optimizations...")
        try:
            with connection.cursor() as cursor:
                # Enable WAL mode for better concurrency
                cursor.execute("PRAGMA journal_mode=WAL;")
                journal_mode = cursor.fetchone()[0]
                self.stdout.write(f"✓ Journal mode set to: {journal_mode}")
                
                # Set busy timeout
                cursor.execute("PRAGMA busy_timeout=30000;")  # 30 seconds
                self.stdout.write("✓ Busy timeout set to 30 seconds")
                
                # Optimize database
                cursor.execute("PRAGMA optimize;")
                self.stdout.write("✓ Database optimized")
                
                # Check current settings
                cursor.execute("PRAGMA journal_mode;")
                journal_mode = cursor.fetchone()[0]
                
                cursor.execute("PRAGMA busy_timeout;")
                busy_timeout = cursor.fetchone()[0]
                
                cursor.execute("PRAGMA synchronous;")
                synchronous = cursor.fetchone()[0]
                
                self.stdout.write("\nCurrent SQLite settings:")
                self.stdout.write(f"  Journal mode: {journal_mode}")
                self.stdout.write(f"  Busy timeout: {busy_timeout}")
                self.stdout.write(f"  Synchronous: {synchronous}")
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ Error applying optimizations: {e}"))
            return
        
        # Check for WAL files
        wal_file = db_path + '-wal'
        shm_file = db_path + '-shm'
        
        if os.path.exists(wal_file):
            self.stdout.write(f"✓ WAL file exists: {wal_file}")
        if os.path.exists(shm_file):
            self.stdout.write(f"✓ Shared memory file exists: {shm_file}")
        
        self.stdout.write(self.style.SUCCESS("\n✓ Database lock fixes applied successfully!"))
        
        # Provide recommendations
        self.stdout.write("\n" + "="*50)
        self.stdout.write("RECOMMENDATIONS:")
        self.stdout.write("="*50)
        self.stdout.write("1. If you're running multiple Django instances, consider using PostgreSQL")
        self.stdout.write("2. Avoid long-running transactions")
        self.stdout.write("3. Close database connections properly in your code")
        self.stdout.write("4. Use connection pooling if needed")
        self.stdout.write("5. Consider running 'python manage.py optimize_db' regularly")
        
        self.stdout.write("\n" + "="*50)
        self.stdout.write("TROUBLESHOOTING STEPS:")
        self.stdout.write("="*50)
        self.stdout.write("1. Stop all Django development servers")
        self.stdout.write("2. Check for any database browser tools accessing the file")
        self.stdout.write("3. Restart your Django development server")
        self.stdout.write("4. Try the signup process again")
