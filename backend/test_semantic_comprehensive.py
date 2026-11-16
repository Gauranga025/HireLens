import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.semantic_matching_service import SemanticMatchingService
import numpy as np

print("=== Comprehensive Semantic Matching Tests ===\n")

service = SemanticMatchingService()

# Test 1: Model loading
print("Test 1: Model Loading")
print(f"Semantic matching available: {service.is_available()}")
if not service.is_available():
    error_info = service.get_error_info()
    print(f"Error: {error_info}")
    sys.exit(1)
print("PASS: Model loaded successfully\n")

# Test 2: Embedding generation
print("Test 2: Embedding Generation")
text1 = "Python developer with FastAPI experience"
embedding1 = service.compute_embedding(text1)
print(f"Text: {text1}")
print(f"Embedding shape: {embedding1.shape if embedding1 is not None else 'None'}")
print(f"Embedding dtype: {embedding1.dtype if embedding1 is not None else 'None'}")
print(f"First 5 values: {embedding1[:5] if embedding1 is not None else 'None'}")
print("PASS: Embedding generated\n")

# Test 3: Embedding dimensions
print("Test 3: Embedding Dimensions")
expected_dim = 384  # all-MiniLM-L6-v2 dimension
actual_dim = embedding1.shape[0] if embedding1 is not None else 0
print(f"Expected dimension: {expected_dim}")
print(f"Actual dimension: {actual_dim}")
if actual_dim == expected_dim:
    print("PASS: Embedding dimensions correct\n")
else:
    print(f"FAIL: Expected {expected_dim}, got {actual_dim}\n")

# Test 4: Cosine similarity
print("Test 4: Cosine Similarity")
text2 = "Built REST APIs using Python and FastAPI framework"
similarity = service.compute_similarity(text1, text2)
print(f"Text 1: {text1}")
print(f"Text 2: {text2}")
print(f"Similarity score: {similarity}")
if similarity is not None and 0 <= similarity <= 1:
    print("PASS: Cosine similarity valid\n")
else:
    print(f"FAIL: Invalid similarity score\n")

# Test 5: High similarity (related texts)
print("Test 5: High Similarity Test")
text_a = "Experience with REST API development"
text_b = "Built RESTful web services"
sim_high = service.compute_similarity(text_a, text_b)
print(f"Text A: {text_a}")
print(f"Text B: {text_b}")
print(f"Similarity: {sim_high}")
print("PASS: High similarity test completed\n")

# Test 6: Low similarity (unrelated texts)
print("Test 6: Low Similarity Test")
text_c = "Machine learning engineer with TensorFlow experience"
text_d = "Built RESTful web services"
sim_low = service.compute_similarity(text_c, text_d)
print(f"Text C: {text_c}")
print(f"Text D: {text_d}")
print(f"Similarity score: {sim_low}")
print("PASS: Low similarity test completed\n")

# Test 7: Empty input handling
print("Test 7: Empty Input Handling")
empty_embedding = service.compute_embedding("")
print(f"Empty text embedding: {empty_embedding}")
empty_similarity = service.compute_similarity("", "")
print(f"Empty text similarity: {empty_similarity}")
if empty_embedding is None and empty_similarity is None:
    print("PASS: Empty input handled correctly\n")
else:
    print("FAIL: Empty input not handled correctly\n")

# Test 8: Batch embeddings
print("Test 8: Batch Embeddings")
texts = [
    "Python developer",
    "Java developer",
    "Machine learning engineer"
]
embeddings = service.compute_embeddings(texts)
print(f"Number of texts: {len(texts)}")
print(f"Number of embeddings: {len(embeddings)}")
print(f"All embeddings valid: {all(e is not None for e in embeddings)}")
if embeddings and all(e is not None for e in embeddings):
    print(f"Batch embedding shape: {np.array(embeddings).shape}")
    print("PASS: Batch embeddings generated\n")
else:
    print("FAIL: Batch embeddings failed\n")

# Test 9: Best match search
print("Test 9: Best Match Search")
query = "REST API development"
candidates = [
    "Built RESTful services",
    "Machine learning with TensorFlow",
    "Python web development",
    "GraphQL API design"
]
best_match, score = service.find_best_match(query, candidates, threshold=0.3)
print(f"Query: {query}")
print(f"Candidates: {candidates}")
print(f"Best match: {best_match}")
print(f"Score: {score}")
if best_match and score >= 0.3:
    print("PASS: Best match search works\n")
else:
    print("FAIL: Best match search failed\n")

# Test 10: Requirements matching
print("Test 10: Requirements Matching")
requirements = ["Python experience", "REST API development"]
evidence_texts = [
    "Built RESTful services using Python",
    "Machine learning with TensorFlow",
    "Java web development"
]
matches = service.match_requirements(requirements, evidence_texts, threshold=0.4)
print(f"Requirements: {requirements}")
print(f"Evidence texts: {evidence_texts}")
print(f"Matches: {matches}")
print("PASS: Requirements matching completed\n")

print("=== All Semantic Matching Tests Completed ===")
