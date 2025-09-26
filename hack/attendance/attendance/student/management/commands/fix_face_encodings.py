"""
Management command to fix corrupted face encodings
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from student.models import User
import json

class Command(BaseCommand):
    help = 'Fix corrupted face encodings by clearing invalid ones'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be fixed without actually fixing',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        users = User.objects.filter(face_encoding__isnull=False).exclude(face_encoding='')
        
        if not users.exists():
            self.stdout.write(
                self.style.WARNING('No users with face encodings found.')
            )
            return
        
        self.stdout.write(f'Checking {users.count()} users with face encodings:')
        
        fixed_count = 0
        for user in users:
            self.stdout.write(f'\n--- User: {user.username} (ID: {user.id}) ---')
            
            try:
                # Try to parse the stored encoding
                stored_encoding = json.loads(user.face_encoding)
                
                if isinstance(stored_encoding, list) and len(stored_encoding) > 0:
                    # Check if it's the correct length (10,035 for our algorithm)
                    if len(stored_encoding) == 10035:
                        self.stdout.write(f'  ✅ Valid encoding ({len(stored_encoding)} features)')
                    else:
                        self.stdout.write(f'  ⚠️  Wrong length: {len(stored_encoding)} (expected 10,035)')
                        if not dry_run:
                            user.face_encoding = None
                            user.save()
                            self.stdout.write(f'  🔧 Fixed: Cleared invalid encoding')
                            fixed_count += 1
                        else:
                            self.stdout.write(f'  🔧 Would fix: Clear invalid encoding')
                            fixed_count += 1
                else:
                    self.stdout.write(f'  ❌ Invalid format: {type(stored_encoding)}')
                    if not dry_run:
                        user.face_encoding = None
                        user.save()
                        self.stdout.write(f'  🔧 Fixed: Cleared invalid encoding')
                        fixed_count += 1
                    else:
                        self.stdout.write(f'  🔧 Would fix: Clear invalid encoding')
                        fixed_count += 1
                        
            except json.JSONDecodeError as e:
                self.stdout.write(f'  ❌ JSON parse error: {e}')
                if not dry_run:
                    user.face_encoding = None
                    user.save()
                    self.stdout.write(f'  🔧 Fixed: Cleared invalid encoding')
                    fixed_count += 1
                else:
                    self.stdout.write(f'  🔧 Would fix: Clear invalid encoding')
                    fixed_count += 1
            except Exception as e:
                self.stdout.write(f'  ❌ Other error: {e}')
                if not dry_run:
                    user.face_encoding = None
                    user.save()
                    self.stdout.write(f'  🔧 Fixed: Cleared invalid encoding')
                    fixed_count += 1
                else:
                    self.stdout.write(f'  🔧 Would fix: Clear invalid encoding')
                    fixed_count += 1
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(f'\nDRY RUN: Would fix {fixed_count} corrupted face encodings.')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'\nSuccessfully fixed {fixed_count} corrupted face encodings.')
            )
