"""
Test script to verify face encoding algorithm consistency
"""

import numpy as np
import json

def test_face_encoding_algorithm():
    """Test that the face encoding algorithm produces consistent results"""
    
    # Simulate a simple face image (100x100 grayscale)
    np.random.seed(42)  # For reproducible results
    face_image = np.random.randint(0, 256, (100, 100), dtype=np.uint8)
    
    print("Testing face encoding algorithm...")
    print(f"Input image shape: {face_image.shape}")
    print(f"Input image range: {face_image.min()} - {face_image.max()}")
    
    # Simulate the frontend JavaScript algorithm
    features = []
    for i in range(face_image.shape[0]):
        for j in range(face_image.shape[1]):
            gray = face_image[i, j]
            features.append(gray / 255.0)  # Normalize to 0-1 range
    
    # Add statistical features
    mean = np.mean(features)
    variance = np.var(features)
    std = np.sqrt(variance)
    features.extend([mean, variance, std])
    
    # Add histogram features (32 bins)
    histogram = np.zeros(32)
    for i in range(len(features) - 3):  # Exclude the 3 statistical features
        bin_index = int(features[i] * 31)  # 0-31 bins
        bin_index = max(0, min(31, bin_index))  # Clamp to valid range
        histogram[bin_index] += 1
    
    # Normalize histogram
    hist_sum = np.sum(histogram)
    if hist_sum > 0:
        histogram = histogram / hist_sum
    
    features.extend(histogram)
    
    print(f"Generated features length: {len(features)}")
    print(f"Features range: {min(features):.4f} - {max(features):.4f}")
    print(f"First 10 features: {features[:10]}")
    print(f"Last 10 features: {features[-10:]}")
    
    # Test similarity with itself (should be 1.0)
    features_array = np.array(features)
    dot_product = np.dot(features_array, features_array)
    norm = np.linalg.norm(features_array)
    similarity = dot_product / (norm * norm)
    
    print(f"Self-similarity: {similarity:.6f} (should be 1.0)")
    
    # Test with slightly different image
    face_image2 = face_image.copy()
    face_image2[50, 50] = min(255, face_image2[50, 50] + 10)  # Small change
    
    features2 = []
    for i in range(face_image2.shape[0]):
        for j in range(face_image2.shape[1]):
            gray = face_image2[i, j]
            features2.append(gray / 255.0)
    
    mean2 = np.mean(features2)
    variance2 = np.var(features2)
    std2 = np.sqrt(variance2)
    features2.extend([mean2, variance2, std2])
    
    histogram2 = np.zeros(32)
    for i in range(len(features2) - 3):
        bin_index = int(features2[i] * 31)
        bin_index = max(0, min(31, bin_index))
        histogram2[bin_index] += 1
    
    hist_sum2 = np.sum(histogram2)
    if hist_sum2 > 0:
        histogram2 = histogram2 / hist_sum2
    
    features2.extend(histogram2)
    
    # Calculate similarity
    features2_array = np.array(features2)
    dot_product2 = np.dot(features_array, features2_array)
    norm2 = np.linalg.norm(features2_array)
    similarity2 = dot_product2 / (norm * norm2)
    
    print(f"Similarity with slightly different image: {similarity2:.6f}")
    print(f"Difference threshold test: {'PASS' if similarity2 > 0.75 else 'FAIL'}")
    
    return features

if __name__ == "__main__":
    test_face_encoding_algorithm()
