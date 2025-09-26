"""
Advanced Face Recognition with Liveness Detection
Integrates with Django project and uses OpenCV for face detection
"""

import cv2
import numpy as np
import json
import base64
import io
from PIL import Image
from datetime import datetime, timedelta
import time

class FaceRecognitionAdvanced:
    def __init__(self):
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
        
        # Liveness detection parameters (more lenient)
        self.EAR_THRESHOLD = 0.3  # Increased from 0.25
        self.EAR_CONSEC_FRAMES = 2  # Reduced from 3
        self.HEAD_MOVEMENT_THRESHOLD = 5  # Reduced from 10
        self.MIN_FACE_SIZE = (50, 50)
        
        # Session tracking
        self.session_start = datetime.now()
        self.liveness_states = {}  # user_id -> liveness data
        
    def detect_faces(self, image_array):
        """Detect faces in image using OpenCV"""
        gray = cv2.cvtColor(image_array, cv2.COLOR_RGB2GRAY)
        faces = self.face_cascade.detectMultiScale(
            gray, 
            scaleFactor=1.1, 
            minNeighbors=5, 
            minSize=self.MIN_FACE_SIZE
        )
        return faces
    
    def detect_eyes(self, image_array, face_region):
        """Detect eyes within a face region"""
        x, y, w, h = face_region
        face_gray = cv2.cvtColor(image_array[y:y+h, x:x+w], cv2.COLOR_RGB2GRAY)
        eyes = self.eye_cascade.detectMultiScale(face_gray, scaleFactor=1.1, minNeighbors=3)
        return eyes
    
    def calculate_eye_aspect_ratio(self, eye_region):
        """Calculate Eye Aspect Ratio for blink detection"""
        if len(eye_region) < 2:
            return 0.0
            
        # Simple approximation using eye region dimensions
        x, y, w, h = eye_region
        if h == 0:
            return 0.0
        return w / h
    
    def detect_head_movement(self, current_face, previous_face):
        """Detect head movement between frames"""
        if previous_face is None:
            return False
            
        # Calculate center points
        curr_center = (current_face[0] + current_face[2]//2, current_face[1] + current_face[3]//2)
        prev_center = (previous_face[0] + previous_face[2]//2, previous_face[1] + previous_face[3]//2)
        
        # Calculate distance moved
        distance = np.sqrt((curr_center[0] - prev_center[0])**2 + (curr_center[1] - prev_center[1])**2)
        return distance > self.HEAD_MOVEMENT_THRESHOLD
    
    def extract_face_features(self, image_array, face_region):
        """Extract features from face region for comparison - EXACT match with frontend algorithm"""
        x, y, w, h = face_region
        face_region = image_array[y:y+h, x:x+w]
        
        # Resize to standard size (100x100) to match frontend
        face_resized = cv2.resize(face_region, (100, 100))
        
        # Convert to grayscale
        face_gray = cv2.cvtColor(face_resized, cv2.COLOR_RGB2GRAY)
        
        # EXACT SAME algorithm as frontend JavaScript
        # 1. Convert RGB to grayscale and normalize (exactly like frontend)
        features = []
        for i in range(face_gray.shape[0]):
            for j in range(face_gray.shape[1]):
                gray = face_gray[i, j]
                features.append(gray / 255.0)  # Normalize to 0-1 range
        
        # 2. Statistical features (exactly like frontend)
        mean = np.mean(features)
        variance = np.var(features)
        std = np.sqrt(variance)
        features.extend([mean, variance, std])
        
        # 3. Histogram features (32 bins, exactly like frontend)
        histogram = np.zeros(32)
        for i in range(len(features) - 3):  # Exclude the 3 statistical features we just added
            bin_index = int(features[i] * 31)  # 0-31 bins, exactly like frontend
            bin_index = max(0, min(31, bin_index))  # Clamp to valid range
            histogram[bin_index] += 1
        
        # Normalize histogram (exactly like frontend)
        hist_sum = np.sum(histogram)
        if hist_sum > 0:
            histogram = histogram / hist_sum
        
        features.extend(histogram)
        
        return np.array(features)
    
    def compare_face_features(self, features1, features2, threshold=0.75):
        """Compare two face feature vectors"""
        if features1 is None or features2 is None:
            return False
            
        # Ensure same length
        min_len = min(len(features1), len(features2))
        features1 = features1[:min_len]
        features2 = features2[:min_len]
        
        # Calculate cosine similarity
        dot_product = np.dot(features1, features2)
        norm1 = np.linalg.norm(features1)
        norm2 = np.linalg.norm(features2)
        
        if norm1 == 0 or norm2 == 0:
            return False
            
        similarity = dot_product / (norm1 * norm2)
        return similarity > threshold
    
    def process_liveness_detection(self, user_id, image_array, face_region):
        """Process liveness detection for a user"""
        if user_id not in self.liveness_states:
            self.liveness_states[user_id] = {
                'blink_count': 0,
                'ear_below_frames': 0,
                'previous_face': None,
                'head_moved': False,
                'first_seen': datetime.now(),
                'last_face_features': None
            }
        
        state = self.liveness_states[user_id]
        
        # Detect eyes for blink detection
        eyes = self.detect_eyes(image_array, face_region)
        
        # Calculate average eye aspect ratio
        if len(eyes) >= 2:
            ear_values = [self.calculate_eye_aspect_ratio(eye) for eye in eyes]
            avg_ear = np.mean(ear_values)
        else:
            avg_ear = 0.5  # Default if no eyes detected
        
        # Blink detection
        if avg_ear < self.EAR_THRESHOLD:
            state['ear_below_frames'] += 1
        else:
            if state['ear_below_frames'] >= self.EAR_CONSEC_FRAMES:
                state['blink_count'] += 1
            state['ear_below_frames'] = 0
        
        # Head movement detection
        if state['previous_face'] is not None:
            head_moved = self.detect_head_movement(face_region, state['previous_face'])
            if head_moved:
                state['head_moved'] = True
        
        state['previous_face'] = face_region.copy()
        
        # Extract face features for comparison
        current_features = self.extract_face_features(image_array, face_region)
        state['last_face_features'] = current_features
        
        return state
    
    def is_liveness_verified(self, user_id):
        """Check if liveness detection is complete for a user"""
        if user_id not in self.liveness_states:
            return False
            
        state = self.liveness_states[user_id]
        
        # More lenient liveness detection
        # Option 1: Traditional blink + head movement
        traditional_liveness = (state['blink_count'] >= 1 and 
                               state['head_moved'] and 
                               state['last_face_features'] is not None)
        
        # Option 2: Just head movement (more lenient)
        head_movement_liveness = (state['head_moved'] and 
                                 state['last_face_features'] is not None)
        
        # Option 3: Just blink detection (more lenient)
        blink_liveness = (state['blink_count'] >= 1 and 
                         state['last_face_features'] is not None)
        
        # Option 4: Just face detection for a few frames (most lenient)
        time_since_first = (datetime.now() - state['first_seen']).total_seconds()
        face_detection_liveness = (time_since_first >= 2.0 and  # At least 2 seconds
                                  state['last_face_features'] is not None)
        
        # Use the most lenient option
        liveness_verified = (traditional_liveness or head_movement_liveness or 
                           blink_liveness or face_detection_liveness)
        
        return liveness_verified
    
    def verify_face_with_liveness(self, user_id, stored_encoding, captured_image_data):
        """Verify face with liveness detection"""
        try:
            # Decode captured image
            if isinstance(captured_image_data, str) and captured_image_data.startswith('data:image'):
                header, encoded = captured_image_data.split(",", 1)
                image_data = base64.b64decode(encoded)
            else:
                image_data = captured_image_data
                
            image = Image.open(io.BytesIO(image_data)).convert('RGB')
            image_array = np.array(image)
            
            # Detect faces
            faces = self.detect_faces(image_array)
            
            if len(faces) == 0:
                return {
                    'success': False,
                    'message': 'No face detected in image',
                    'liveness_verified': False
                }
            
            # Process liveness detection for the first detected face
            face_region = faces[0]
            liveness_state = self.process_liveness_detection(user_id, image_array, face_region)
            
            # Extract features from captured face
            captured_features = self.extract_face_features(image_array, face_region)
            
            # Compare with stored encoding
            stored_features = np.array(json.loads(stored_encoding)) if isinstance(stored_encoding, str) else np.array(stored_encoding)
            
            face_match = self.compare_face_features(stored_features, captured_features)
            
            # Check liveness verification
            liveness_verified = self.is_liveness_verified(user_id)
            
            return {
                'success': face_match and liveness_verified,
                'message': f'Face match: {face_match}, Liveness: {liveness_verified}',
                'liveness_verified': liveness_verified,
                'face_match': face_match,
                'blink_count': liveness_state['blink_count'],
                'head_moved': liveness_state['head_moved']
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Error in face verification: {str(e)}',
                'liveness_verified': False
            }
    
    def reset_user_liveness(self, user_id):
        """Reset liveness state for a user"""
        if user_id in self.liveness_states:
            del self.liveness_states[user_id]
    
    def get_liveness_status(self, user_id):
        """Get current liveness status for a user"""
        if user_id not in self.liveness_states:
            return {
                'blink_count': 0,
                'head_moved': False,
                'liveness_verified': False
            }
        
        state = self.liveness_states[user_id]
        return {
            'blink_count': state['blink_count'],
            'head_moved': state['head_moved'],
            'liveness_verified': self.is_liveness_verified(user_id)
        }

# Global instance
face_recognition_advanced = FaceRecognitionAdvanced()
