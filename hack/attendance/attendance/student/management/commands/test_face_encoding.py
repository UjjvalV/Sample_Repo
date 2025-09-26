"""
Management command to test face encoding storage and retrieval functionality.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
import json
import numpy as np

User = get_user_model()

class Command(BaseCommand):
    help = 'Test face encoding storage and retrieval functionality'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            help='Username to test with',
            default='testuser'
        )

    def handle(self, *args, **options):
        username = options['username']
        
        self.stdout.write(f'Testing face encoding for user: {username}')
        
        # Create a test face encoding (simplified version)
        test_encoding = self.create_test_face_encoding()
        
        try:
            # Try to get existing user
            user = User.objects.get(username=username)
            self.stdout.write(f'Found existing user: {user.username}')
            
            # Check if user has face encoding
            if user.face_encoding:
                self.stdout.write('User already has face encoding stored')
                stored_encoding = json.loads(user.face_encoding)
                self.stdout.write(f'Stored encoding length: {len(stored_encoding)}')
                
                # Test face comparison
                similarity = self.compare_encodings(test_encoding, stored_encoding)
                self.stdout.write(f'Similarity with test encoding: {similarity:.4f}')
            else:
                self.stdout.write('User does not have face encoding stored')
                
                # Store test encoding
                user.face_encoding = json.dumps(test_encoding)
                user.save()
                self.stdout.write('Test face encoding stored successfully')
                
        except User.DoesNotExist:
            self.stdout.write(f'User {username} does not exist')
            self.stdout.write('Please create a user first through the signup process')
        
        self.stdout.write(self.style.SUCCESS('Face encoding test completed'))

    def create_test_face_encoding(self):
        """Create a test face encoding for testing purposes"""
        # Create a simple test encoding with 10000 features (100x100 image)
        # This simulates the encoding that would be generated from a face image
        np.random.seed(42)  # For reproducible results
        encoding = np.random.random(10000).tolist()
        
        # Add some statistical features
        mean = np.mean(encoding)
        variance = np.var(encoding)
        std = np.std(encoding)
        encoding.extend([mean, variance, std])
        
        # Add histogram features (32 bins)
        histogram = np.histogram(encoding[:10000], bins=32, range=(0, 1))[0]
        histogram = histogram / np.sum(histogram)  # Normalize
        encoding.extend(histogram.tolist())
        
        return encoding

    def compare_encodings(self, encoding1, encoding2):
        """Compare two face encodings using cosine similarity"""
        try:
            # Convert to numpy arrays
            arr1 = np.array(encoding1)
            arr2 = np.array(encoding2)
            
            # Ensure both arrays have the same length
            min_length = min(len(arr1), len(arr2))
            arr1 = arr1[:min_length]
            arr2 = arr2[:min_length]
            
            # Calculate cosine similarity
            dot_product = np.dot(arr1, arr2)
            norm1 = np.linalg.norm(arr1)
            norm2 = np.linalg.norm(arr2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            similarity = dot_product / (norm1 * norm2)
            return similarity
            
        except Exception as e:
            self.stdout.write(f'Error comparing encodings: {e}')
            return 0.0
