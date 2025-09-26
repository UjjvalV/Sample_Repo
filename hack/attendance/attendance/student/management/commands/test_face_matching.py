"""
Management command to test face matching algorithm
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from student.models import User
import json
import numpy as np

class Command(BaseCommand):
    help = 'Test face matching algorithm'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user-id',
            type=int,
            help='Test face matching for specific user ID',
        )

    def handle(self, *args, **options):
        user_id = options.get('user_id')
        
        if user_id:
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'User with ID {user_id} not found.')
                )
                return
            users = [user]
        else:
            users = User.objects.filter(face_encoding__isnull=False).exclude(face_encoding='')
        
        if not users.exists():
            self.stdout.write(
                self.style.WARNING('No users with face encodings found.')
            )
            return
        
        self.stdout.write(f'Testing face matching for {users.count()} users:')
        
        for user in users:
            self.stdout.write(f'\n--- User: {user.username} (ID: {user.id}) ---')
            
            if not user.face_encoding:
                self.stdout.write('  No face encoding found')
                continue
            
            try:
                # Parse the stored encoding
                stored_encoding = json.loads(user.face_encoding)
                self.stdout.write(f'  Stored encoding length: {len(stored_encoding)}')
                self.stdout.write(f'  Stored encoding type: {type(stored_encoding)}')
                
                # Show first few values
                if len(stored_encoding) > 0:
                    self.stdout.write(f'  First 5 values: {stored_encoding[:5]}')
                    self.stdout.write(f'  Last 5 values: {stored_encoding[-5:]}')
                    
                    # Calculate basic statistics
                    mean_val = np.mean(stored_encoding)
                    std_val = np.std(stored_encoding)
                    min_val = np.min(stored_encoding)
                    max_val = np.max(stored_encoding)
                    
                    self.stdout.write(f'  Mean: {mean_val:.4f}')
                    self.stdout.write(f'  Std: {std_val:.4f}')
                    self.stdout.write(f'  Min: {min_val:.4f}')
                    self.stdout.write(f'  Max: {max_val:.4f}')
                
            except Exception as e:
                self.stdout.write(f'  Error parsing encoding: {e}')
        
        self.stdout.write(
            self.style.SUCCESS('\nFace encoding analysis complete!')
        )
