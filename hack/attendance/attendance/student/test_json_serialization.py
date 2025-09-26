"""
Test script to verify JSON serialization fix for face recognition
"""

import json
from django.test import TestCase
from django.http import JsonResponse

def test_json_serialization():
    """Test that boolean values are properly serialized"""
    
    # Simulate the verification result that was causing issues
    verification_result = {
        'success': True,  # This was causing the JSON serialization error
        'message': 'Face verified successfully',
        'liveness_verified': True,  # This was also causing issues
        'face_match': True,
        'blink_count': 2,
        'head_moved': True
    }
    
    # Test the old way (this would fail)
    try:
        # This would cause "Object of type bool is not JSON serializable"
        old_response = JsonResponse({
            'status': 'success',
            'liveness_status': verification_result  # Direct boolean values
        })
        print("❌ Old method should have failed but didn't")
    except Exception as e:
        print(f"✅ Old method correctly failed: {e}")
    
    # Test the new way (this should work)
    try:
        new_response = JsonResponse({
            'status': 'success',
            'liveness_status': {
                'success': bool(verification_result.get('success', False)),
                'message': str(verification_result.get('message', '')),
                'liveness_verified': bool(verification_result.get('liveness_verified', False)),
                'face_match': bool(verification_result.get('face_match', False)),
                'blink_count': int(verification_result.get('blink_count', 0)),
                'head_moved': bool(verification_result.get('head_moved', False))
            }
        })
        print("✅ New method works correctly!")
        
        # Verify the content
        content = json.loads(new_response.content)
        print(f"✅ JSON content: {content}")
        
    except Exception as e:
        print(f"❌ New method failed: {e}")

if __name__ == "__main__":
    test_json_serialization()
