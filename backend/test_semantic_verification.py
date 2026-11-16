"""
Quick verification script for semantic model loading and embedding generation.
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.semantic_matching_service import SemanticMatchingService

def main():
    print("Testing semantic model loading and embedding generation...")
    
    service = SemanticMatchingService()
    
    # Check availability
    available = service.is_available()
    print(f"Semantic matching available: {available}")
    
    if not available:
        error_info = service.get_error_info()
        print(f"Error: {error_info}")
        return False
    
    # Test embedding generation
    text1 = "Developed RESTful APIs using Python and FastAPI"
    text2 = "Built scalable HTTP services with Python"
    
    print(f"\nTest text 1: {text1}")
    print(f"Test text 2: {text2}")
    
    # Test similarity
    similarity = service.compute_similarity(text1, text2)
    print(f"\nSimilarity score: {similarity}")
    
    # Test embedding
    embedding = service.compute_embedding(text1)
    print(f"Embedding shape: {embedding.shape if embedding is not None else 'None'}")
    
    print("\n✓ Semantic model verification passed")
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
