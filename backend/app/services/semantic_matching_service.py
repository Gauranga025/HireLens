"""
Semantic matching service using sentence-transformers.
Provides requirement-level semantic similarity matching.
"""
import functools
import logging
from typing import Optional, List, Dict, Tuple, Any
from enum import Enum

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)


class SemanticErrorType(Enum):
    """Types of semantic matching errors."""
    PACKAGE_NOT_INSTALLED = "package_not_installed"
    IMPORT_FAILURE = "import_failure"
    DLL_DEPENDENCY_FAILURE = "dll_dependency_failure"
    MODEL_DOWNLOAD_FAILURE = "model_download_failure"
    MODEL_LOADING_FAILURE = "model_loading_failure"
    INFERENCE_FAILURE = "inference_failure"


class SemanticError(Exception):
    """Custom exception for semantic matching errors."""
    
    def __init__(self, error_type: SemanticErrorType, message: str):
        self.error_type = error_type
        self.message = message
        super().__init__(message)


class SemanticMatchingService:
    """Service for semantic similarity matching using sentence-transformers."""
    
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """
        Initialize the semantic matching service.
        
        Args:
            model_name: Name of the sentence-transformers model to use.
        """
        self.model_name = model_name
        self._model = None
        self._load_attempted = False
        self._load_error: Optional[SemanticError] = None
    
    @functools.lru_cache(maxsize=1)
    def _load_model(self) -> None:
        """
        Load the sentence-transformers model (cached).
        
        Raises:
            SemanticError: If model loading fails.
        """
        if self._load_attempted:
            if self._load_error:
                raise self._load_error
            return
        
        self._load_attempted = True
        
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as e:
            error = SemanticError(
                SemanticErrorType.PACKAGE_NOT_INSTALLED,
                f"sentence-transformers package not installed: {e}"
            )
            self._load_error = error
            logger.warning("sentence-transformers package not installed. Semantic matching disabled.")
            raise error
        except OSError as e:
            error = SemanticError(
                SemanticErrorType.DLL_DEPENDENCY_FAILURE,
                f"Failed to load sentence-transformers (DLL/dependency issue): {e}"
            )
            self._load_error = error
            logger.warning(f"Failed to load sentence-transformers (DLL/dependency issue): {e}")
            raise error
        except Exception as e:
            error = SemanticError(
                SemanticErrorType.IMPORT_FAILURE,
                f"Failed to import sentence-transformers: {e}"
            )
            self._load_error = error
            logger.error(f"Unexpected error importing sentence-transformers: {e}")
            raise error
        
        try:
            logger.info(f"Loading semantic model: {self.model_name}")
            self._model = SentenceTransformer(self.model_name)
            logger.info("Semantic model loaded successfully")
        except Exception as e:
            error = SemanticError(
                SemanticErrorType.MODEL_LOADING_FAILURE,
                f"Failed to load model {self.model_name}: {e}"
            )
            self._load_error = error
            logger.error(f"Failed to load semantic model: {e}")
            raise error
    
    def is_available(self) -> bool:
        """
        Check if semantic matching is available.
        
        Returns:
            True if model is loaded and available, False otherwise.
        """
        if not self._load_attempted:
            try:
                self._load_model()
                return True
            except SemanticError:
                return False
        return self._load_error is None
    
    def get_error_info(self) -> Optional[Dict[str, str]]:
        """
        Get information about the loading error if any.
        
        Returns:
            Dictionary with error type and message, or None if no error.
        """
        if self._load_error:
            return {
                "error_type": self._load_error.error_type.value,
                "message": self._load_error.message
            }
        return None
    
    def compute_embedding(self, text: str) -> Optional[np.ndarray]:
        """
        Compute embedding for a single text.
        
        Args:
            text: Input text.
            
        Returns:
            Embedding vector, or None if computation fails.
        """
        if not text or not text.strip():
            return None
        
        try:
            self._load_model()
            if self._model is None:
                return None
            
            embedding = self._model.encode(text, convert_to_numpy=True)
            return embedding
        except SemanticError:
            return None
        except Exception as e:
            logger.error(f"Embedding computation failed: {e}")
            return None
    
    def compute_embeddings(self, texts: List[str]) -> List[Optional[np.ndarray]]:
        """
        Compute embeddings for multiple texts.
        
        Args:
            texts: List of input texts.
            
        Returns:
            List of embedding vectors (None for failed computations).
        """
        if not texts:
            return []
        
        try:
            self._load_model()
            if self._model is None:
                return [None] * len(texts)
            
            embeddings = self._model.encode(texts, convert_to_numpy=True)
            return list(embeddings)
        except SemanticError:
            return [None] * len(texts)
        except Exception as e:
            logger.error(f"Batch embedding computation failed: {e}")
            return [None] * len(texts)
    
    def compute_similarity(
        self,
        text1: str,
        text2: str,
    ) -> Optional[float]:
        """
        Compute cosine similarity between two texts.
        
        Args:
            text1: First text.
            text2: Second text.
            
        Returns:
            Similarity score between 0 and 1, or None if computation fails.
        """
        if not text1 or not text2 or not text1.strip() or not text2.strip():
            return None
        
        try:
            self._load_model()
            if self._model is None:
                return None
            
            embeddings = self._model.encode([text1, text2], convert_to_numpy=True)
            similarity_matrix = cosine_similarity(embeddings[0:1], embeddings[1:2])
            score = float(similarity_matrix[0][0])
            return float(np.clip(score, 0.0, 1.0))
        except SemanticError:
            return None
        except Exception as e:
            logger.error(f"Similarity computation failed: {e}")
            return None
    
    def find_best_match(
        self,
        query: str,
        candidates: List[str],
        threshold: float = 0.5,
    ) -> Tuple[Optional[str], Optional[float]]:
        """
        Find the best matching candidate for a query.
        
        Args:
            query: Query text.
            candidates: List of candidate texts.
            threshold: Minimum similarity threshold.
            
        Returns:
            Tuple of (best_match, similarity_score), or (None, None) if no match above threshold.
        """
        if not query or not candidates:
            return None, None
        
        try:
            self._load_model()
            if self._model is None:
                return None, None
            
            # Compute embeddings
            query_embedding = self._model.encode([query], convert_to_numpy=True)
            candidate_embeddings = self._model.encode(candidates, convert_to_numpy=True)
            
            # Compute similarities
            similarities = cosine_similarity(query_embedding, candidate_embeddings)[0]
            
            # Find best match
            best_idx = int(np.argmax(similarities))
            best_score = float(similarities[best_idx])
            
            if best_score >= threshold:
                return candidates[best_idx], best_score
            
            return None, None
        except SemanticError:
            return None, None
        except Exception as e:
            logger.error(f"Best match search failed: {e}")
            return None, None
    
    def match_requirements(
        self,
        requirements: List[str],
        evidence_texts: List[str],
        threshold: float = 0.5,
    ) -> List[Dict[str, Any]]:
        """
        Match job requirements against resume evidence texts.
        
        Args:
            requirements: List of job requirement texts.
            evidence_texts: List of resume evidence snippets.
            threshold: Minimum similarity threshold.
            
        Returns:
            List of match results with similarity scores.
        """
        if not requirements or not evidence_texts:
            return []
        
        try:
            self._load_model()
            if self._model is None:
                return []
            
            results = []
            
            # Compute embeddings
            req_embeddings = self._model.encode(requirements, convert_to_numpy=True)
            evidence_embeddings = self._model.encode(evidence_texts, convert_to_numpy=True)
            
            # Compute similarity matrix
            similarity_matrix = cosine_similarity(req_embeddings, evidence_embeddings)
            
            # For each requirement, find best matching evidence
            for i, requirement in enumerate(requirements):
                best_idx = int(np.argmax(similarity_matrix[i]))
                best_score = float(similarity_matrix[i][best_idx])
                
                result = {
                    "requirement": requirement,
                    "matched": best_score >= threshold,
                    "similarity_score": best_score,
                    "best_evidence": evidence_texts[best_idx] if best_score >= threshold else None,
                }
                results.append(result)
            
            return results
        except SemanticError:
            return []
        except Exception as e:
            logger.error(f"Requirements matching failed: {e}")
            return []
