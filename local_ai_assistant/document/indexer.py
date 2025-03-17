"""
Document indexer module for embedding and storing document chunks.

This module provides functions to index document chunks in the vector store
for retrieval-augmented generation.
"""

import logging
import time
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple
import yaml
import uuid

# Local imports
from local_ai_assistant.document.loader import DocumentLoader
from local_ai_assistant.memory.vector_store import VectorStore
from local_ai_assistant.models.model_manager import ModelManager


# Logger for this module
logger = logging.getLogger(__name__)


class DocumentIndexer:
    """
    Indexes document chunks in the vector store.
    
    This class coordinates document loading, chunking, embedding generation,
    and storage in the vector database for RAG.
    """
    
    def __init__(
        self, 
        config_path: Union[str, Path], 
        document_loader: DocumentLoader,
        vector_store: VectorStore,
        model_manager: ModelManager
    ):
        """
        Initialize the document indexer.
        
        Args:
            config_path: Path to the configuration file
            document_loader: Document loader instance
            vector_store: Vector store instance
            model_manager: Model manager instance
        """
        self.config_path = Path(config_path)
        self.document_loader = document_loader
        self.vector_store = vector_store
        self.model_manager = model_manager
        
        # Load configuration
        with open(self.config_path, 'r') as f:
            self.config = yaml.safe_load(f)
            
        # Extract chunking settings from config
        doc_config = self.config['document']
        self.chunk_size = doc_config.get('chunk_size', 1000)
        self.chunk_overlap = doc_config.get('chunk_overlap', 200)
        
        # Track indexed documents
        self.indexed_docs = {}
        
        logger.info("Document indexer initialized")
    
    def chunk_document(self, text: str, metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Split document text into chunks.
        
        Args:
            text: Document text
            metadata: Document metadata
            
        Returns:
            List of chunk dictionaries with text and metadata
        """
        # Simple chunking implementation (by characters with overlap)
        if not text:
            return []
            
        chunks = []
        
        # Ensure we have metadata
        if metadata is None:
            metadata = {}
        
        # Create chunks with overlap
        i = 0
        while i < len(text):
            chunk_text = text[i:i + self.chunk_size]
            
            # Skip empty chunks
            if not chunk_text.strip():
                i += max(1, self.chunk_size - self.chunk_overlap)
                continue
                
            # Create chunk metadata
            chunk_metadata = metadata.copy()
            chunk_metadata.update({
                'chunk_index': len(chunks),
                'chunk_start_char': i,
                'chunk_end_char': min(i + self.chunk_size, len(text)),
                'is_chunk': True
            })
            
            # Add chunk
            chunks.append({
                'text': chunk_text,
                'metadata': chunk_metadata
            })
            
            # Move to next chunk with overlap
            i += max(1, self.chunk_size - self.chunk_overlap)
        
        logger.info(f"Created {len(chunks)} chunks from document")
        return chunks
    
    def index_document(self, doc_id: str) -> bool:
        """
        Index a document in the vector store.
        
        Args:
            doc_id: Document ID
            
        Returns:
            True if successful, False otherwise
        """
        # Get document
        doc = self.document_loader.get_document(doc_id)
        if doc is None:
            logger.error(f"Document not found: {doc_id}")
            return False
        
        try:
            # Get document text and metadata
            text = doc.get('text', '')
            metadata = doc.get('metadata', {})
            
            # Chunk document
            chunks = self.chunk_document(text, metadata)
            
            if not chunks:
                logger.warning(f"No chunks created for document {doc_id}")
                return False
            
            # Generate embeddings for chunks
            chunk_texts = [chunk['text'] for chunk in chunks]
            embeddings = self.model_manager.generate_embeddings(chunk_texts)
            
            # Store chunks in vector store
            chunk_ids = []
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                # Create chunk ID
                chunk_id = f"{doc_id}_chunk_{i}"
                
                # Add chunk to vector store
                self.vector_store.add_to_memory(
                    text=chunk['text'],
                    metadata={
                        **chunk['metadata'],
                        'doc_id': doc_id,
                        'chunk_id': chunk_id,
                        'type': 'document_chunk'
                    },
                    embedding=embedding,
                    id=chunk_id
                )
                
                chunk_ids.append(chunk_id)
            
            # Store document index info
            self.indexed_docs[doc_id] = {
                'doc_id': doc_id,
                'chunk_ids': chunk_ids,
                'chunk_count': len(chunks),
                'indexed_at': time.time()
            }
            
            logger.info(f"Indexed document {doc_id} with {len(chunks)} chunks")
            return True
            
        except Exception as e:
            logger.error(f"Error indexing document {doc_id}: {str(e)}")
            return False
    
    def index_all_documents(self) -> int:
        """
        Index all loaded documents.
        
        Returns:
            Number of successfully indexed documents
        """
        # Get all documents
        docs = self.document_loader.list_documents()
        
        if not docs:
            logger.info("No documents to index")
            return 0
        
        # Index each document
        success_count = 0
        for doc in docs:
            doc_id = doc.get('id')
            if doc_id and self.index_document(doc_id):
                success_count += 1
        
        logger.info(f"Indexed {success_count} out of {len(docs)} documents")
        return success_count
    
    def search_documents(
        self, 
        query: str, 
        n_results: int = 5, 
        doc_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search document chunks by semantic similarity.
        
        Args:
            query: Search query
            n_results: Maximum number of results
            doc_id: Optional document ID to limit search to
            
        Returns:
            List of matching chunks with text and metadata
        """
        # Generate query embedding
        query_embedding = self.model_manager.generate_embeddings(query)[0]
        
        # Set up metadata filter if doc_id is provided
        metadata_filter = None
        if doc_id:
            metadata_filter = {'doc_id': doc_id, 'type': 'document_chunk'}
        else:
            metadata_filter = {'type': 'document_chunk'}
        
        # Search vector store
        results = self.vector_store.search_memory(
            query_text=query,
            n_results=n_results,
            metadata_filter=metadata_filter,
            embedding=query_embedding
        )
        
        logger.info(f"Found {len(results)} document chunks for query: {query}")
        return results
    
    def delete_document_index(self, doc_id: str) -> bool:
        """
        Delete document index from vector store.
        
        Args:
            doc_id: Document ID
            
        Returns:
            True if successful, False otherwise
        """
        if doc_id not in self.indexed_docs:
            logger.warning(f"Document {doc_id} not indexed")
            return False
        
        try:
            # Get chunk IDs
            chunk_ids = self.indexed_docs[doc_id].get('chunk_ids', [])
            
            # Delete chunks from vector store
            for chunk_id in chunk_ids:
                self.vector_store.delete_message(chunk_id)
            
            # Remove from indexed documents
            del self.indexed_docs[doc_id]
            
            logger.info(f"Deleted document index for {doc_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting document index {doc_id}: {str(e)}")
            return False 