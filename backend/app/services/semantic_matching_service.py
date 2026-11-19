"""
Semantic matching service using sentence-transformers.
Provides requirement-level semantic similarity matching.
"""
import functools
import hashlib
import logging
import os
import re
import threading
from collections import OrderedDict
from typing import Optional, List, Dict, Tuple, Any
from enum import Enum

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)

REQUIREMENT_EMBEDDING_CACHE_SIZE = 256
CHUNK_EMBEDDING_CACHE_SIZE = 2048

DEFAULT_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
# Verified against the local Hugging Face cache on 2026-11-19. The unpinned and
# explicitly pinned snapshots expose identical config, tokenizer, weights, and
# embeddings; see the root README.
VERIFIED_MODEL_REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"


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
    
    def __init__(
        self,
        model_name: Optional[str] = None,
        revision: Optional[str] = None,
    ):
        """
        Initialize the semantic matching service.

        Args:
            model_name: Model repository name. Defaults to the verified
                Sentence Transformers model, overridable with
                ``SEMANTIC_MODEL_NAME``.
            revision: Exact model revision. Defaults to the verified pinned
                snapshot for the standard model, overridable with
                ``SEMANTIC_MODEL_REVISION``. Custom models use ``main`` unless
                an explicit revision is supplied.
        """
        self.model_name = model_name or os.getenv(
            "SEMANTIC_MODEL_NAME", DEFAULT_MODEL_NAME
        )
        if revision is not None:
            self.model_revision = revision
        else:
            env_revision = os.getenv("SEMANTIC_MODEL_REVISION")
            self.model_revision = (
                env_revision
                or (
                    VERIFIED_MODEL_REVISION
                    if self.model_name == DEFAULT_MODEL_NAME
                    else "main"
                )
            )
        self._model = None
        self._load_attempted = False
        self._load_error: Optional[SemanticError] = None
        self._model_revision: str = self.model_revision
        self._cache_lock = threading.RLock()
        self._embedding_caches: Dict[str, OrderedDict] = {
            "requirement": OrderedDict(),
            "chunk": OrderedDict(),
        }
        self._cache_limits: Dict[str, int] = {
            "requirement": REQUIREMENT_EMBEDDING_CACHE_SIZE,
            "chunk": CHUNK_EMBEDDING_CACHE_SIZE,
        }
        self._cache_stats: Dict[str, Dict[str, int]] = {
            "requirement": {"hits": 0, "misses": 0, "evictions": 0},
            "chunk": {"hits": 0, "misses": 0, "evictions": 0},
        }
    
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
            logger.info(
                "Loading semantic model %s at revision %s",
                self.model_name,
                self.model_revision,
            )
            self._model = SentenceTransformer(
                self.model_name,
                revision=self.model_revision,
            )
            logger.info("Semantic model loaded successfully")
        except OSError as e:
            error = SemanticError(
                SemanticErrorType.MODEL_DOWNLOAD_FAILURE,
                f"Failed to download or cache model {self.model_name} "
                f"at revision {self.model_revision}: {e}"
            )
            self._load_error = error
            logger.error(f"Failed to download semantic model: {e}")
            raise error
        except Exception as e:
            error = SemanticError(
                SemanticErrorType.MODEL_LOADING_FAILURE,
                f"Failed to load model {self.model_name} "
                f"at revision {self.model_revision}: {e}"
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

    def _revision_from_model(self) -> str:
        """Return the loaded model's revision, or the configured fallback."""
        model = self._model
        if model is not None:
            for attribute in ("_model_revision", "model_revision", "revision"):
                value = getattr(model, attribute, None)
                if value:
                    return str(value)

            configs = [getattr(model, "config", None)]
            first_module_factory = getattr(model, "_first_module", None)
            if callable(first_module_factory):
                try:
                    first_module = first_module_factory()
                except Exception:
                    first_module = None
                auto_model = getattr(first_module, "auto_model", None)
                configs.append(getattr(auto_model, "config", None))

            for config in configs:
                for attribute in ("_commit_hash", "commit_hash"):
                    value = getattr(config, attribute, None) if config is not None else None
                    if value:
                        return str(value)
        return self.model_revision or "unpinned"

    def get_model_context(self) -> Dict[str, Any]:
        """Expose the loaded model's tokenizer and verified maximum length."""
        self._load_model()
        model = self._model
        if model is None:
            raise SemanticError(
                SemanticErrorType.INFERENCE_FAILURE,
                "Semantic model is not available for token verification.",
            )

        tokenizer = getattr(model, "tokenizer", None)
        if tokenizer is None:
            first_module = getattr(model, "_first_module", None)
            if callable(first_module):
                module = first_module()
                tokenizer = getattr(module, "tokenizer", None)
        if tokenizer is None:
            raise SemanticError(
                SemanticErrorType.MODEL_LOADING_FAILURE,
                "The semantic model did not expose a tokenizer.",
            )

        max_length_candidates: List[int] = []
        for value in (
            getattr(model, "max_seq_length", None),
            getattr(tokenizer, "model_max_length", None),
        ):
            try:
                numeric = int(value)
            except (TypeError, ValueError):
                continue
            if 0 < numeric < 1_000_000:
                max_length_candidates.append(numeric)
        if not max_length_candidates:
            raise SemanticError(
                SemanticErrorType.MODEL_LOADING_FAILURE,
                "The semantic model did not expose a usable maximum sequence length.",
            )

        revision = self._revision_from_model()
        self._model_revision = revision
        return {
            "tokenizer": tokenizer,
            "max_seq_length": min(max_length_candidates),
            "model_name": self.model_name,
            "model_revision": revision,
        }

    @staticmethod
    def _normalized_text_hash(text: str) -> str:
        normalized = re.sub(r"\s+", " ", text or "").strip().casefold()
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def _embedding_cache_key(self, text: str) -> Tuple[str, str, str]:
        return (self.model_name, self._revision_from_model(), self._normalized_text_hash(text))

    def compute_embeddings_cached(
        self,
        texts: List[str],
        cache_kind: str,
    ) -> List[Optional[np.ndarray]]:
        """Embed unique texts once per bounded LRU cache."""
        if cache_kind not in self._embedding_caches:
            raise SemanticError(
                SemanticErrorType.INFERENCE_FAILURE,
                f"Unknown embedding cache kind: {cache_kind}",
            )
        # The cache key includes model revision information that may only be
        # available after the lazy model load, so load before deriving keys.
        self._load_model()
        cache = self._embedding_caches[cache_kind]
        results: List[Optional[np.ndarray]] = [None] * len(texts)
        unique_missing: List[str] = []
        missing_positions_by_key: Dict[Tuple[str, str, str], List[int]] = {}

        with self._cache_lock:
            for position, text in enumerate(texts):
                if not text or not text.strip():
                    raise SemanticError(
                        SemanticErrorType.INFERENCE_FAILURE,
                        "Refusing to embed empty text.",
                    )
                key = self._embedding_cache_key(text)
                if key in cache:
                    cache.move_to_end(key)
                    results[position] = cache[key]
                    self._cache_stats[cache_kind]["hits"] += 1
                elif key in missing_positions_by_key:
                    # A duplicate inside this batch counts as a hit and reuses
                    # the same embedding object as its first occurrence.
                    missing_positions_by_key[key].append(position)
                    self._cache_stats[cache_kind]["hits"] += 1
                else:
                    self._cache_stats[cache_kind]["misses"] += 1
                    missing_positions_by_key[key] = [position]
                    unique_missing.append(text)

        if unique_missing:
            computed = self.compute_embeddings(unique_missing)
            if len(computed) != len(unique_missing) or any(
                embedding is None for embedding in computed
            ):
                raise SemanticError(
                    SemanticErrorType.INFERENCE_FAILURE,
                    "Batch embedding computation returned no embedding for a text.",
                )
            with self._cache_lock:
                limit = self._cache_limits[cache_kind]
                for text, embedding in zip(unique_missing, computed):
                    key = self._embedding_cache_key(text)
                    cache[key] = embedding
                    cache.move_to_end(key)
                    while len(cache) > limit:
                        cache.popitem(last=False)
                        self._cache_stats[cache_kind]["evictions"] += 1
            for text, embedding in zip(unique_missing, computed):
                key = self._embedding_cache_key(text)
                for position in missing_positions_by_key[key]:
                    results[position] = embedding

        return results

    def compute_similarity_matrix(
        self,
        query_texts: List[str],
        chunk_texts: List[str],
    ) -> Optional[np.ndarray]:
        """Compute a clipped cosine matrix from batched, cached embeddings."""
        if not query_texts or not chunk_texts:
            return np.zeros((len(query_texts), len(chunk_texts)), dtype=float)
        try:
            query_embeddings = self.compute_embeddings_cached(
                list(query_texts), "requirement"
            )
            chunk_embeddings = self.compute_embeddings_cached(
                list(chunk_texts), "chunk"
            )
            query_matrix = np.vstack(query_embeddings)
            chunk_matrix = np.vstack(chunk_embeddings)
            similarities = cosine_similarity(query_matrix, chunk_matrix)
            return np.clip(similarities, 0.0, 1.0)
        except SemanticError:
            return None
        except Exception as exc:
            logger.error(f"Similarity matrix computation failed: {exc}")
            return None

    def get_cache_stats(self) -> Dict[str, Dict[str, int]]:
        """Return a snapshot of bounded embedding-cache counters."""
        with self._cache_lock:
            return {
                kind: dict(stats) | {"size": len(self._embedding_caches[kind])}
                for kind, stats in self._cache_stats.items()
            }

    def clear_embedding_caches(self) -> None:
        """Clear cached embeddings and counters (diagnostic/testing helper)."""
        with self._cache_lock:
            for cache in self._embedding_caches.values():
                cache.clear()
            for stats in self._cache_stats.values():
                stats.update({"hits": 0, "misses": 0, "evictions": 0})

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
