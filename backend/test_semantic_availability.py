import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.semantic_matching_service import SemanticMatchingService

async def main():
    print("Testing semantic matching service availability...")
    
    service = SemanticMatchingService()
    
    # Check if available
    is_available = service.is_available()
    print(f"Semantic matching available: {is_available}")
    
    if not is_available:
        error_info = service.get_error_info()
        if error_info:
            print(f"Error type: {error_info['error_type']}")
            print(f"Error message: {error_info['message']}")
    else:
        # Test a simple similarity computation
        try:
            similarity = service.compute_similarity(
                "Python developer with FastAPI experience",
                "Built REST APIs using Python and FastAPI framework"
            )
            print(f"Test similarity score: {similarity}")
        except Exception as e:
            print(f"Similarity computation failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
