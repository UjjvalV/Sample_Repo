"""
Face recognition utilities using OpenCV for face detection and comparison.
This module provides functions for face encoding and comparison using OpenCV.
"""

import base64
import json
import numpy as np
from PIL import Image
import io
import cv2
import os
from django.core.files.base import ContentFile


def get_face_cascade():
    """Get OpenCV face cascade classifier"""
    try:
        # Try to load the cascade from OpenCV data
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        face_cascade = cv2.CascadeClassifier(cascade_path)
        return face_cascade
    except Exception as e:
        print(f"Error loading face cascade: {e}")
        return None


def detect_faces_in_image(image_array):
    """
    Detect faces in an image using OpenCV.
    
    Args:
        image_array: Numpy array of the image
    
    Returns:
        list: List of face rectangles (x, y, w, h)
    """
    try:
        face_cascade = get_face_cascade()
        if face_cascade is None:
            return []
        
        # Convert to grayscale for face detection
        gray = cv2.cvtColor(image_array, cv2.COLOR_RGB2GRAY)
        
        # Detect faces
        faces = face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30)
        )
        
        return faces.tolist() if len(faces) > 0 else []
        
    except Exception as e:
        print(f"Error detecting faces: {e}")
        return []


def extract_face_features(image_array, face_rect):
    """
    Extract face features for comparison using OpenCV.
    
    Args:
        image_array: Numpy array of the image
        face_rect: Face rectangle (x, y, w, h)
    
    Returns:
        list: Face features as a list of numbers
    """
    try:
        x, y, w, h = face_rect
        
        # Extract face region
        face_region = image_array[y:y+h, x:x+w]
        
        # Resize to standard size
        face_resized = cv2.resize(face_region, (100, 100))
        
        # Convert to grayscale
        face_gray = cv2.cvtColor(face_resized, cv2.COLOR_RGB2GRAY)
        
        # Apply histogram equalization for better contrast
        face_equalized = cv2.equalizeHist(face_gray)
        
        # Apply Gaussian blur to reduce noise
        face_blurred = cv2.GaussianBlur(face_equalized, (3, 3), 0)
        
        # Extract features using multiple methods
        features = []
        
        # 1. Raw pixel values (normalized)
        features.extend(face_blurred.flatten() / 255.0)
        
        # 2. Histogram features
        hist = cv2.calcHist([face_blurred], [0], None, [32], [0, 256])
        features.extend(hist.flatten() / np.sum(hist))
        
        # 3. Edge features using Canny
        edges = cv2.Canny(face_blurred, 50, 150)
        features.extend(edges.flatten() / 255.0)
        
        # 4. LBP-like features (simplified)
        lbp_features = []
        for i in range(1, face_blurred.shape[0]-1):
            for j in range(1, face_blurred.shape[1]-1):
                center = face_blurred[i, j]
                lbp = 0
                if face_blurred[i-1, j-1] >= center: lbp += 1
                if face_blurred[i-1, j] >= center: lbp += 2
                if face_blurred[i-1, j+1] >= center: lbp += 4
                if face_blurred[i, j+1] >= center: lbp += 8
                if face_blurred[i+1, j+1] >= center: lbp += 16
                if face_blurred[i+1, j] >= center: lbp += 32
                if face_blurred[i+1, j-1] >= center: lbp += 64
                if face_blurred[i, j-1] >= center: lbp += 128
                lbp_features.append(lbp)
        
        features.extend(np.array(lbp_features) / 255.0)
        
        return features
        
    except Exception as e:
        print(f"Error extracting face features: {e}")
        return None


def encode_face_from_base64(base64_data):
    """
    Encode a face from base64 image data using OpenCV.
    
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
        faces = detect_faces_in_image(image_array)
        
        if len(faces) > 0:
            # Use the first face found
            face_rect = faces[0]
            face_features = extract_face_features(image_array, face_rect)
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
        faces = detect_faces_in_image(image_array)
        
        if len(faces) > 0:
            # Use the first face found
            face_rect = faces[0]
            face_features = extract_face_features(image_array, face_rect)
            return face_features
        else:
            return None
            
    except Exception as e:
        print(f"Error encoding face from image file: {e}")
        return None


def compare_face_encodings(known_encoding, unknown_encoding, threshold=0.3):
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
        
        # Check if it has reasonable number of features (100x100 = 10000 for our case)
        if len(encoding) < 1000:  # Minimum reasonable size
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