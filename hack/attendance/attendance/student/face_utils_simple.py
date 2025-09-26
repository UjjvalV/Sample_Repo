"""
Simplified face recognition utilities that work without OpenCV initially.
This module provides basic face detection and comparison using PIL and numpy.
"""

import base64
import json
import numpy as np
from PIL import Image
import io
from django.core.files.base import ContentFile


def detect_faces_simple(image_array):
    """
    Simple face detection using basic image analysis.
    This is a placeholder that will be replaced with OpenCV later.
    
    Args:
        image_array: Numpy array of the image
    
    Returns:
        list: List of face rectangles (x, y, w, h)
    """
    try:
        # For now, assume the entire image contains a face
        # This will be replaced with proper OpenCV face detection
        height, width = image_array.shape[:2]
        
        # Create a face rectangle that covers most of the image
        face_size = min(width, height) * 0.8
        x = int((width - face_size) / 2)
        y = int((height - face_size) / 2)
        w = int(face_size)
        h = int(face_size)
        
        return [(x, y, w, h)]
        
    except Exception as e:
        print(f"Error in simple face detection: {e}")
        return []


def extract_face_features_simple(image_array, face_rect):
    """
    Extract face features using the SAME algorithm as frontend JavaScript.
    
    Args:
        image_array: Numpy array of the image
        face_rect: Face rectangle (x, y, w, h)
    
    Returns:
        list: Face features as a list of numbers (10,035 features)
    """
    try:
        x, y, w, h = face_rect
        
        # Extract face region
        face_region = image_array[y:y+h, x:x+w]
        
        # Resize to standard size (100x100) to match frontend
        face_resized = np.array(Image.fromarray(face_region).resize((100, 100)))
        
        # Convert to grayscale if needed
        if len(face_resized.shape) == 3:
            face_gray = np.mean(face_resized, axis=2)
        else:
            face_gray = face_resized
        
        # Use EXACT SAME algorithm as frontend JavaScript
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
        
        return features
        
    except Exception as e:
        print(f"Error extracting face features: {e}")
        return None


def encode_face_from_base64(base64_data):
    """
    Encode a face from base64 image data using simple methods.
    
    Args:
        base64_data (str): Base64 encoded image data (with or without data URI prefix)
    
    Returns:
        list: Face encoding as a list of features, or None if no face found
    """
    try:
        # Remove data URI prefix if present
        if base64_data.startswith('data:image'):
            base64_data = base64_data.split(',', 1)[1]
        
        # Decode base64 to image
        image_bytes = base64.b64decode(base64_data)
        image = Image.open(io.BytesIO(image_bytes))
        
        # Convert PIL image to RGB if needed
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Convert to numpy array
        image_array = np.array(image)
        
        # Detect faces
        faces = detect_faces_simple(image_array)
        
        if len(faces) > 0:
            # Use the first face found
            face_rect = faces[0]
            face_features = extract_face_features_simple(image_array, face_rect)
            return face_features
        else:
            return None
            
    except Exception as e:
        print(f"Error encoding face from base64: {e}")
        return None


def encode_face_from_image_file(image_file):
    """
    Encode a face from an uploaded image file.
    
    Args:
        image_file: Django uploaded file object
    
    Returns:
        list: Face encoding as a list of features, or None if no face found
    """
    try:
        # Read the image file
        image = Image.open(image_file)
        
        # Convert PIL image to RGB if needed
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Convert to numpy array
        image_array = np.array(image)
        
        # Detect faces
        faces = detect_faces_simple(image_array)
        
        if len(faces) > 0:
            # Use the first face found
            face_rect = faces[0]
            face_features = extract_face_features_simple(image_array, face_rect)
            return face_features
        else:
            return None
            
    except Exception as e:
        print(f"Error encoding face from image file: {e}")
        return None


def compare_face_encodings(known_encoding, unknown_encoding, threshold=0.7):
    """
    Compare two face encodings using cosine similarity.
    
    Args:
        known_encoding: Known face encoding (list or JSON string)
        unknown_encoding: Unknown face encoding (list or JSON string)
        threshold (float): Similarity threshold (lower = more strict)
    
    Returns:
        bool: True if faces match, False otherwise
    """
    try:
        # Parse encodings if they are JSON strings
        if isinstance(known_encoding, str):
            known_encoding = json.loads(known_encoding)
        if isinstance(unknown_encoding, str):
            unknown_encoding = json.loads(unknown_encoding)
        
        # Convert to numpy arrays
        known_array = np.array(known_encoding)
        unknown_array = np.array(unknown_encoding)
        
        # Ensure both arrays have the same length
        min_length = min(len(known_array), len(unknown_array))
        known_array = known_array[:min_length]
        unknown_array = unknown_array[:min_length]
        
        # Calculate cosine similarity
        dot_product = np.dot(known_array, unknown_array)
        norm_known = np.linalg.norm(known_array)
        norm_unknown = np.linalg.norm(unknown_array)
        
        if norm_known == 0 or norm_unknown == 0:
            return False
        
        similarity = dot_product / (norm_known * norm_unknown)
        
        # Check if similarity is above threshold
        match = similarity > threshold
        
        print(f"Face similarity: {similarity:.4f}, Threshold: {threshold}, Match: {match}")
        return match
        
    except Exception as e:
        print(f"Error comparing face encodings: {e}")
        return False


def encode_face_from_canvas_data(canvas_data_url):
    """
    Encode a face from canvas data URL (used in frontend).
    
    Args:
        canvas_data_url (str): Canvas data URL (data:image/png;base64,...)
    
    Returns:
        list: Face encoding as a list of features, or None if no face found
    """
    try:
        # Extract base64 data from data URL
        if canvas_data_url.startswith('data:image'):
            base64_data = canvas_data_url.split(',', 1)[1]
        else:
            base64_data = canvas_data_url
        
        return encode_face_from_base64(base64_data)
        
    except Exception as e:
        print(f"Error encoding face from canvas data: {e}")
        return None


def validate_face_encoding(encoding):
    """
    Validate if a face encoding is properly formatted.
    
    Args:
        encoding: Face encoding to validate
    
    Returns:
        bool: True if valid, False otherwise
    """
    try:
        if isinstance(encoding, str):
            encoding = json.loads(encoding)
        
        if not isinstance(encoding, list):
            return False
        
        # Check if it has reasonable number of features
        if len(encoding) < 100:  # Minimum reasonable size
            return False
        
        # Check if all elements are numbers
        for element in encoding:
            if not isinstance(element, (int, float)):
                return False
        
        return True
        
    except Exception as e:
        print(f"Error validating face encoding: {e}")
        return False


def get_face_encoding_distance(known_encoding, unknown_encoding):
    """
    Get the distance between two face encodings using cosine similarity.
    Higher similarity means more similar faces.
    
    Args:
        known_encoding: Known face encoding
        unknown_encoding: Unknown face encoding
    
    Returns:
        float: Similarity score (0-1), or None if error
    """
    try:
        # Parse encodings if they are JSON strings
        if isinstance(known_encoding, str):
            known_encoding = json.loads(known_encoding)
        if isinstance(unknown_encoding, str):
            unknown_encoding = json.loads(unknown_encoding)
        
        # Convert to numpy arrays
        known_array = np.array(known_encoding)
        unknown_array = np.array(unknown_encoding)
        
        # Ensure both arrays have the same length
        min_length = min(len(known_array), len(unknown_array))
        known_array = known_array[:min_length]
        unknown_array = unknown_array[:min_length]
        
        # Calculate cosine similarity
        dot_product = np.dot(known_array, unknown_array)
        norm_known = np.linalg.norm(known_array)
        norm_unknown = np.linalg.norm(unknown_array)
        
        if norm_known == 0 or norm_unknown == 0:
            return None
        
        similarity = dot_product / (norm_known * norm_unknown)
        return similarity
        
    except Exception as e:
        print(f"Error calculating face distance: {e}")
        return None
