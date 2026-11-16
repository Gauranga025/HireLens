"""
Minimal FastAPI app to isolate PyTorch DLL loading issue.
Run with: python -m uvicorn app.diagnostic_minimal:app --host 127.0.0.1 --port 8001
"""
import logging
import sys
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Minimal lifespan for testing torch import."""
    logger.info("[MINIMAL_APP] === Startup ===")
    logger.info(f"[MINIMAL_APP] sys.executable: {sys.executable}")
    logger.info(f"[MINIMAL_APP] CWD: {os.getcwd()}")

    # Test 1: Import torch
    logger.info("[MINIMAL_APP] Test 1: Import torch...")
    try:
        import torch
        logger.info(f"[MINIMAL_APP] SUCCESS: torch {torch.__version__}")
        tensor = torch.tensor([1.0, 2.0, 3.0])
        logger.info(f"[MINIMAL_APP] Tensor created: {tensor}")
    except Exception as e:
        logger.error(f"[MINIMAL_APP] FAILED: {e}")

    # Test 2: Import sentence-transformers
    logger.info("[MINIMAL_APP] Test 2: Import sentence-transformers...")
    try:
        from sentence_transformers import SentenceTransformer
        logger.info("[MINIMAL_APP] SUCCESS: sentence-transformers imported")
        model = SentenceTransformer('all-MiniLM-L6-v2', device='cpu')
        logger.info("[MINIMAL_APP] Model loaded")
        embeddings = model.encode(['test text', 'another test'])
        logger.info(f"[MINIMAL_APP] Embeddings shape: {embeddings.shape}")
    except Exception as e:
        logger.error(f"[MINIMAL_APP] FAILED: {e}")

    yield
    logger.info("[MINIMAL_APP] === Shutdown ===")


app = FastAPI(lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok", "app": "minimal_diagnostic"}


@app.get("/test-torch")
async def test_torch():
    """Test torch import on request."""
    try:
        import torch
        return {"torch": "ok", "version": torch.__version__}
    except Exception as e:
        return {"torch": "error", "message": str(e)}


@app.get("/test-st")
async def test_sentence_transformers():
    """Test sentence-transformers on request."""
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer('all-MiniLM-L6-v2', device='cpu')
        embeddings = model.encode(['test'])
        return {"sentence_transformers": "ok", "embeddings_shape": list(embeddings.shape)}
    except Exception as e:
        return {"sentence_transformers": "error", "message": str(e)}
