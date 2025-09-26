"""
Test script for the advanced face recognition system
"""

import os
import sys
import django

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'attendance.settings')
django.setup()

from .face_recognition_advanced import face_recognition_advanced
import numpy as np

def test_face_recognition():
    """Test the face recognition system"""
    print("Testing Advanced Face Recognition System...")
    
    # Test 1: Create a dummy face encoding
    dummy_encoding = np.random.rand(1000).tolist()  # Simulate a face encoding
    dummy_encoding_json = str(dummy_encoding)
    
    # Test 2: Create a dummy image data (base64 encoded)
    dummy_image_data = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
    
    # Test 3: Test face verification
    user_id = "test_user_123"
    result = face_recognition_advanced.verify_face_with_liveness(
        user_id, 
        dummy_encoding_json, 
        dummy_image_data
    )
    
    print(f"Face verification result: {result}")
    
    # Test 4: Test liveness status
    liveness_status = face_recognition_advanced.get_liveness_status(user_id)
    print(f"Liveness status: {liveness_status}")
    
    # Test 5: Test reset
    face_recognition_advanced.reset_user_liveness(user_id)
    print("Liveness state reset successfully")
    
    print("All tests completed!")

if __name__ == "__main__":
    test_face_recognition()
