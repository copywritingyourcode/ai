"""
Embeddings module for handling vector embeddings.

This module provides functions to generate, normalize, and 
manipulate vector embeddings for semantic search and retrieval.
"""

import logging
import numpy as np
from typing import List, Dict, Any, Union, Optional
from pathlib import Path

# Local imports
from local_ai_assistant.models.model_manager import ModelManager


# Logger for this module
logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """
    Generates and manipulates vector embeddings using the 
    Ollama embedding model (nomic-embed-text by default).
    """
    
    def __init__(self, model_manager: ModelManager):
        """
        Initialize the embedding generator.
        
        Args:
            model_manager: Model manager instance for embedding generation
        """
        self.model_manager = model_manager
        self.embedding_model = self.model_manager.embedding_model
        logger.info(f"Embedding generator initialized with model: {self.embedding_model}")
    
    def generate_embeddings(self, texts: Union[str, List[str]]) -> List[List[float]]:
        """
        Generate embeddings for text(s).
        
        Args:
            texts: Single text or list of texts to embed
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            logger.warning("Empty text passed to generate_embeddings")
            return []
        
        # Handle single text
        if isinstance(texts, str):
            texts = [texts]
        
        try:
            # Generate embeddings using model manager
            embeddings = self.model_manager.generate_embeddings(texts)
            logger.debug(f"Generated {len(embeddings)} embeddings")
            return embeddings
            
        except Exception as e:
            logger.error(f"Error generating embeddings: {str(e)}")
            raise RuntimeError(f"Failed to generate embeddings: {str(e)}")
    
    def normalize_embeddings(self, embeddings: List[List[float]]) -> List[List[float]]:
        """
        Normalize embedding vectors to unit length (L2 norm).
        
        Args:
            embeddings: List of embedding vectors
            
        Returns:
            List of normalized embedding vectors
        """
        if not embeddings:
            return []
        
        try:
            # Convert to numpy for efficient operations
            np_embeddings = np.array(embeddings)
            
            # Calculate L2 norm (sqrt of sum of squares)
            norms = np.linalg.norm(np_embeddings, axis=1, keepdims=True)
            
            # Avoid division by zero
            norms = np.where(norms == 0, 1e-10, norms)
            
            # Normalize
            normalized = np_embeddings / norms
            
            # Convert back to list
            return normalized.tolist()
            
        except Exception as e:
            logger.error(f"Error normalizing embeddings: {str(e)}")
            # Return original embeddings if normalization fails
            return embeddings
    
    def compute_similarity(
        self,
        embedding1: List[float],
        embedding2: List[float],
        method: str = "cosine"
    ) -> float:
        """
        Compute similarity between two embeddings.
        
        Args:
            embedding1: First embedding
            embedding2: Second embedding
            method: Similarity method (cosine, dot, euclidean)
            
        Returns:
            Similarity score
        """
        if not embedding1 or not embedding2:
            logger.warning("Empty embedding passed to compute_similarity")
            return 0.0
        
        try:
            # Convert to numpy
            v1 = np.array(embedding1)
            v2 = np.array(embedding2)
            
            if method == "cosine":
                # Cosine similarity: dot product of normalized vectors
                norm1 = np.linalg.norm(v1)
                norm2 = np.linalg.norm(v2)
                
                # Avoid division by zero
                if norm1 == 0 or norm2 == 0:
                    return 0.0
                    
                return np.dot(v1, v2) / (norm1 * norm2)
                
            elif method == "dot":
                # Simple dot product
                return np.dot(v1, v2)
                
            elif method == "euclidean":
                # Euclidean distance (converted to similarity)
                distance = np.linalg.norm(v1 - v2)
                # Convert distance to similarity (1 / (1 + distance))
                return 1.0 / (1.0 + distance)
                
            else:
                logger.warning(f"Unknown similarity method: {method}, using cosine")
                # Default to cosine
                norm1 = np.linalg.norm(v1)
                norm2 = np.linalg.norm(v2)
                
                # Avoid division by zero
                if norm1 == 0 or norm2 == 0:
                    return 0.0
                    
                return np.dot(v1, v2) / (norm1 * norm2)
                
        except Exception as e:
            logger.error(f"Error computing similarity: {str(e)}")
            return 0.0
    
    def batch_compute_similarity(
        self,
        query_embedding: List[float],
        document_embeddings: List[List[float]],
        method: str = "cosine"
    ) -> List[float]:
        """
        Compute similarity between one query embedding and multiple document embeddings.
        
        Args:
            query_embedding: Query embedding
            document_embeddings: List of document embeddings
            method: Similarity method (cosine, dot, euclidean)
            
        Returns:
            List of similarity scores
        """
        if not query_embedding or not document_embeddings:
            logger.warning("Empty embeddings passed to batch_compute_similarity")
            return [0.0] * len(document_embeddings) if document_embeddings else []
        
        try:
            # Convert to numpy
            query = np.array(query_embedding)
            docs = np.array(document_embeddings)
            
            if method == "cosine":
                # Cosine similarity: normalize and then dot product
                query_norm = np.linalg.norm(query)
                
                # Avoid division by zero
                if query_norm == 0:
                    return [0.0] * len(document_embeddings)
                    
                # Normalize query
                query_normalized = query / query_norm
                
                # Normalize documents (row-wise)
                docs_norm = np.linalg.norm(docs, axis=1, keepdims=True)
                # Replace zeros with small value to avoid division by zero
                docs_norm = np.where(docs_norm == 0, 1e-10, docs_norm)
                docs_normalized = docs / docs_norm
                
                # Compute dot products
                similarities = np.dot(docs_normalized, query_normalized)
                
                return similarities.tolist()
                
            elif method == "dot":
                # Simple dot product
                similarities = np.dot(docs, query)
                return similarities.tolist()
                
            elif method == "euclidean":
                # Euclidean distance (converted to similarity)
                distances = np.linalg.norm(docs - query, axis=1)
                # Convert distances to similarities (1 / (1 + distance))
                similarities = 1.0 / (1.0 + distances)
                return similarities.tolist()
                
            else:
                logger.warning(f"Unknown similarity method: {method}, using cosine")
                # Default to cosine (same as above)
                query_norm = np.linalg.norm(query)
                
                # Avoid division by zero
                if query_norm == 0:
                    return [0.0] * len(document_embeddings)
                    
                query_normalized = query / query_norm
                docs_norm = np.linalg.norm(docs, axis=1, keepdims=True)
                docs_norm = np.where(docs_norm == 0, 1e-10, docs_norm)
                docs_normalized = docs / docs_norm
                
                similarities = np.dot(docs_normalized, query_normalized)
                return similarities.tolist()
                
        except Exception as e:
            logger.error(f"Error in batch_compute_similarity: {str(e)}")
            return [0.0] * len(document_embeddings) 