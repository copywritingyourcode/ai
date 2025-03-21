"""
Vector store module for persistent memory storage.

This module provides a vector database for storing and retrieving
conversation history and document chunks.
"""

import logging
import json
import os
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple
import yaml

# Try importing ChromaDB, but don't fail if it's not available
try:
    import chromadb
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

# Local imports
from local_ai_assistant.models.model_manager import ModelManager


# Logger for this module
logger = logging.getLogger(__name__)


class VectorStore:
    """
    Vector database for persistent memory storage.
    
    This class provides methods to store and retrieve conversation
    memory and document chunks using a vector database.
    """
    
    def __init__(self, config_path: Union[str, Path]):
        """
        Initialize the vector store.
        
        Args:
            config_path: Path to the configuration file
        """
        self.config_path = Path(config_path)
        
        # Load configuration
        with open(self.config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # Extract memory settings
        memory_config = self.config['memory']['vector_store']
        
        # Storage directory
        self.persist_directory = Path(memory_config['persist_directory'])
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        
        # Collection name
        self.collection_name = memory_config['collection_name']
        
        # Distance metric
        self.distance_metric = memory_config.get('distance_metric', 'cosine')
        
        # Initialize model manager (needed for embeddings)
        self.model_manager = None
        
        # Initialize ChromaDB client and collection if available
        self.chromadb_available = CHROMADB_AVAILABLE
        self.client = None
        self.collection = None
        
        # For mock mode, use a simple in-memory list
        self.memory_items = []
        
        # Initialize ChromaDB if available
        if self.chromadb_available:
            try:
                self.client = chromadb.PersistentClient(path=str(self.persist_directory))
                self.collection = self._get_or_create_collection()
                logger.info(f"ChromaDB initialized with collection: {self.collection_name}")
            except Exception as e:
                logger.warning(f"Failed to initialize ChromaDB: {str(e)}")
                self.chromadb_available = False
                logger.warning("Running in mock mode with in-memory storage")
        else:
            logger.warning("ChromaDB not available. Running in mock mode with in-memory storage")
            # Try to load existing items from disk in mock mode
            self._load_memory_items()
    
    def _ensure_embedding_generator(self):
        """
        Make sure we have a model manager for generating embeddings.
        
        This is initialized lazily to avoid circular imports.
        """
        if self.model_manager is None:
            from local_ai_assistant.models.model_manager import ModelManager
            self.model_manager = ModelManager(self.config_path)
    
    def _get_or_create_collection(self):
        """Get or create the ChromaDB collection."""
        try:
            # Check if collection exists
            collection = self.client.get_collection(
                name=self.collection_name,
                embedding_function=None  # We'll handle embeddings ourselves
            )
            return collection
        except Exception:
            # Create new collection
            collection = self.client.create_collection(
                name=self.collection_name,
                embedding_function=None,
                metadata={"distance_metric": self.distance_metric}
            )
            return collection
    
    def _load_memory_items(self):
        """Load memory items from disk in mock mode."""
        try:
            memory_file = self.persist_directory / f"{self.collection_name}.json"
            if memory_file.exists():
                with open(memory_file, 'r') as f:
                    self.memory_items = json.load(f)
                logger.info(f"Loaded {len(self.memory_items)} items from {memory_file}")
        except Exception as e:
            logger.error(f"Error loading memory items: {str(e)}")
            self.memory_items = []
            
    def _save_memory_items(self):
        """Save memory items to disk in mock mode."""
        try:
            memory_file = self.persist_directory / f"{self.collection_name}.json"
            with open(memory_file, 'w') as f:
                json.dump(self.memory_items, f)
            logger.debug(f"Saved {len(self.memory_items)} items to {memory_file}")
        except Exception as e:
            logger.error(f"Error saving memory items: {str(e)}")
    
    def add_to_memory(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
        embedding: Optional[List[float]] = None,
        id: Optional[str] = None
    ) -> str:
        """
        Add an item to the memory vector store.
        
        Args:
            text: Text content to store
            metadata: Optional metadata for the item
            embedding: Optional pre-computed embedding vector
            id: Optional ID for the item (generated if not provided)
            
        Returns:
            ID of the stored item
        """
        # Generate ID if not provided
        if id is None:
            id = str(uuid.uuid4())
        
        # Initialize metadata if not provided
        if metadata is None:
            metadata = {}
        
        # Add timestamp if not provided
        if 'timestamp' not in metadata:
            metadata['timestamp'] = time.time()
        
        # Generate embedding if not provided
        if embedding is None:
            # Ensure we have a model manager
            self._ensure_embedding_generator()
            embedding = self.model_manager.generate_embeddings(text)[0]
        
        if self.chromadb_available:
            try:
                # Add to ChromaDB collection
                self.collection.add(
                    ids=[id],
                    embeddings=[embedding],
                    metadatas=[metadata],
                    documents=[text]
                )
                logger.debug(f"Added item to vector store with ID: {id}")
                return id
            except Exception as e:
                logger.error(f"Error adding to ChromaDB: {str(e)}")
                
                # Fall back to in-memory storage
                logger.warning("Falling back to in-memory storage")
                self.chromadb_available = False
        
        # Mock mode: store in memory list
        self.memory_items.append({
            'id': id,
            'text': text,
            'embedding': embedding,
            'metadata': metadata
        })
        
        # Save to disk in mock mode
        self._save_memory_items()
        
        logger.debug(f"Added item to in-memory store with ID: {id}")
        return id
    
    def add_conversation_pair(
        self,
        user_message: str,
        assistant_response: str,
        user_metadata: Optional[Dict[str, Any]] = None,
        assistant_metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, str]:
        """
        Add a user-assistant message pair to memory.
        
        Args:
            user_message: User message text
            assistant_response: Assistant response text
            user_metadata: Optional metadata for user message
            assistant_metadata: Optional metadata for assistant response
            
        Returns:
            Tuple of (user_id, assistant_id)
        """
        # Ensure metadata dictionaries
        if user_metadata is None:
            user_metadata = {}
        if assistant_metadata is None:
            assistant_metadata = {}
        
        # Set role in metadata
        user_metadata['role'] = 'user'
        assistant_metadata['role'] = 'assistant'
        
        # Set timestamp if not present
        if 'timestamp' not in user_metadata:
            user_metadata['timestamp'] = time.time()
        if 'timestamp' not in assistant_metadata:
            assistant_metadata['timestamp'] = user_metadata.get('timestamp', time.time()) + 0.1
        
        # Generate embeddings using the model manager
        self._ensure_embedding_generator()
        embeddings = self.model_manager.generate_embeddings([user_message, assistant_response])
        
        # Add messages to memory
        user_id = self.add_to_memory(
            text=user_message,
            metadata=user_metadata,
            embedding=embeddings[0]
        )
        
        assistant_id = self.add_to_memory(
            text=assistant_response,
            metadata=assistant_metadata,
            embedding=embeddings[1]
        )
        
        logger.debug(f"Added conversation pair to memory: {user_id}, {assistant_id}")
        return user_id, assistant_id
    
    def search_memory(
        self,
        query_text: str,
        n_results: int = 5,
        metadata_filter: Optional[Dict[str, Any]] = None,
        embedding: Optional[List[float]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search memory for items related to the query.
        
        Args:
            query_text: Text to search for
            n_results: Maximum number of results to return
            metadata_filter: Optional filter for metadata fields
            embedding: Optional pre-computed query embedding
            
        Returns:
            List of matching items with their texts, metadata, and IDs
        """
        # Generate embedding if not provided
        if embedding is None and query_text:
            self._ensure_embedding_generator()
            embedding = self.model_manager.generate_embeddings(query_text)[0]
        
        if self.chromadb_available and embedding is not None:
            try:
                # Search ChromaDB
                where = metadata_filter if metadata_filter else None
                results = self.collection.query(
                    query_embeddings=[embedding],
                    n_results=n_results,
                    where=where
                )
                
                # Format results
                items = []
                for i in range(len(results['ids'][0])):
                    items.append({
                        'id': results['ids'][0][i],
                        'text': results['documents'][0][i],
                        'metadata': results['metadatas'][0][i],
                        'distance': results.get('distances', [[0] * len(results['ids'][0])])[0][i]
                    })
                
                return items
            except Exception as e:
                logger.error(f"Error searching ChromaDB: {str(e)}")
                
                # Fall back to in-memory search
                logger.warning("Falling back to in-memory search")
                self.chromadb_available = False
        
        # Mock mode: simple in-memory search
        # In a real implementation, we'd calculate embedding similarity
        # For this mock version, just do basic filtering
        filtered_items = self.memory_items
        
        # Apply metadata filter if provided
        if metadata_filter:
            filtered_items = []
            for item in self.memory_items:
                match = True
                for key, value in metadata_filter.items():
                    if key not in item['metadata'] or item['metadata'][key] != value:
                        match = False
                        break
                if match:
                    filtered_items.append(item)
        
        # Sort by recency (as a simple approximation of relevance)
        filtered_items.sort(
            key=lambda x: x['metadata'].get('timestamp', 0), 
            reverse=True
        )
        
        # Return the requested number of items
        return filtered_items[:n_results]
    
    def get_conversation_context(
        self,
        query_text: str,
        n_relevant: int = 5,
        include_recent: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Get conversation context for the current query.
        
        This combines semantically relevant and recent messages.
        
        Args:
            query_text: Current query text
            n_relevant: Number of relevant items to include
            include_recent: Number of most recent items to include
            
        Returns:
            List of context items sorted in chronological order
        """
        # Get recent items
        recent_items = self.get_recent_messages(include_recent)
        
        # Get relevant items based on query
        relevant_items = []
        if query_text:
            relevant_items = self.search_memory(
                query_text=query_text, 
                n_results=n_relevant
            )
        
        # Combine, ensuring no duplicates
        context_items = []
        seen_ids = set()
        
        # Add recent items first
        for item in recent_items:
            item_id = item['id']
            if item_id not in seen_ids:
                context_items.append(item)
                seen_ids.add(item_id)
        
        # Then add relevant items
        for item in relevant_items:
            item_id = item['id']
            if item_id not in seen_ids:
                context_items.append(item)
                seen_ids.add(item_id)
        
        # Sort by timestamp for chronological order
        context_items.sort(
            key=lambda x: x['metadata'].get('timestamp', 0)
        )
        
        logger.debug(f"Retrieved conversation context: {len(context_items)} items")
        return context_items
    
    def get_document_context(
        self,
        query_text: str,
        n_results: int = 3,
        doc_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get document context relevant to a query.
        
        This specifically searches for document chunks (not conversation memory).
        
        Args:
            query_text: Query text
            n_results: Number of document chunks to retrieve
            doc_filter: Optional document ID to filter by
            
        Returns:
            List of relevant document chunks
        """
        # Prepare metadata filter for document chunks
        metadata_filter = {'type': 'document_chunk'}
        
        # Add doc_id filter if provided
        if doc_filter:
            metadata_filter['doc_id'] = doc_filter
            
        # Search for document chunks
        results = self.search_memory(
            query_text=query_text,
            n_results=n_results,
            metadata_filter=metadata_filter
        )
        
        logger.debug(f"Found {len(results)} document chunks relevant to query")
        return results
        
    def get_combined_context(
        self,
        query_text: str,
        n_conversation: int = 3,
        n_documents: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Get combined context from conversation memory and documents.
        
        Args:
            query_text: Query text
            n_conversation: Number of conversation messages to include
            n_documents: Number of document chunks to include
            
        Returns:
            List of context items (conversation + documents)
        """
        # Get recent conversation context
        conversation = self.get_recent_messages(n_conversation)
        
        # Get document context
        documents = self.get_document_context(query_text, n_results=n_documents)
        
        # Combine contexts
        combined = []
        
        # Add conversation items first
        for item in conversation:
            combined.append({
                'id': item.get('id', ''),
                'text': item.get('text', ''),
                'metadata': item.get('metadata', {}),
                'source': 'conversation'
            })
        
        # Add document items
        for item in documents:
            combined.append({
                'id': item.get('id', ''),
                'text': item.get('text', ''),
                'metadata': item.get('metadata', {}),
                'source': 'document',
                'relevance': 1.0 - (item.get('distance', 0) or 0)  # Convert distance to relevance score
            })
        
        logger.debug(f"Combined context: {len(conversation)} conversation items, {len(documents)} document chunks")
        return combined
    
    def format_context_for_prompt(self, context_items: List[Dict[str, Any]]) -> str:
        """
        Format context items into a string for inclusion in a prompt.
        
        Args:
            context_items: List of context items
            
        Returns:
            Formatted context string
        """
        if not context_items:
            return ""
        
        parts = []
        
        # Process each context item
        for item in context_items:
            source = item.get('source', 'unknown')
            text = item.get('text', '')
            metadata = item.get('metadata', {})
            
            if source == 'conversation':
                role = metadata.get('role', 'unknown')
                parts.append(f"[Previous {role}]: {text}")
            
            elif source == 'document':
                doc_id = metadata.get('doc_id', 'unknown')
                filename = metadata.get('filename', 'unknown document')
                relevance = item.get('relevance', 0.0)
                parts.append(f"[Document: {filename} (ID: {doc_id}) - Relevance: {relevance:.2f}]:\n{text}")
        
        return "\n\n".join(parts)
    
    def get_recent_messages(self, n: int = 5) -> List[Dict[str, Any]]:
        """
        Get the most recent n messages.
        
        Args:
            n: Number of recent messages to retrieve
            
        Returns:
            List of recent messages with text, metadata, and ID
        """
        if self.chromadb_available:
            try:
                # Get all items with role metadata
                results = self.collection.get(
                    where={"$or": [{"role": "user"}, {"role": "assistant"}]},
                    include=["metadatas", "documents", "embeddings"]
                )
                
                # Format results
                formatted_results = []
                if results and 'ids' in results and results['ids']:
                    for i in range(len(results['ids'])):
                        formatted_results.append({
                            'id': results['ids'][i],
                            'text': results['documents'][i],
                            'metadata': results['metadatas'][i]
                        })
                    
                    # Sort by timestamp (most recent first)
                    formatted_results.sort(
                        key=lambda x: x.get('metadata', {}).get('timestamp', 0),
                        reverse=True
                    )
                    
                    # Take the n most recent
                    formatted_results = formatted_results[:n]
                    
                    # Reverse to get chronological order
                    formatted_results.reverse()
                
                logger.debug(f"Retrieved {len(formatted_results)} recent messages")
                return formatted_results
                
            except Exception as e:
                logger.error(f"Error getting recent messages: {str(e)}")
                # Fall back to in-memory method
                
        # Mock mode or fallback
        # Sort by timestamp (most recent first)
        sorted_items = sorted(
            [item for item in self.memory_items if item.get('metadata', {}).get('role') in ['user', 'assistant']],
            key=lambda x: x.get('metadata', {}).get('timestamp', 0),
            reverse=True
        )
        
        # Get the n most recent items and reverse for chronological order
        recent = sorted_items[:n]
        recent.reverse()
        
        return recent
    
    def get_message_by_id(self, id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific message by ID.
        
        Args:
            id: ID of the message to retrieve
            
        Returns:
            Message dict or None if not found
        """
        if self.chromadb_available:
            try:
                results = self.collection.get(
                    ids=[id],
                    include=["documents", "metadatas", "embeddings"]
                )
                
                if results and 'ids' in results and results['ids']:
                    return {
                        'id': results['ids'][0],
                        'text': results['documents'][0],
                        'metadata': results['metadatas'][0],
                        'embedding': results.get('embeddings', [[]])[0] if 'embeddings' in results else None
                    }
                else:
                    logger.warning(f"Message with ID {id} not found")
                    return None
                    
            except Exception as e:
                logger.error(f"Error getting message by ID: {str(e)}")
                # Fall back to in-memory method
        
        # Mock mode or fallback
        for item in self.memory_items:
            if item.get('id') == id:
                return item
        
        logger.warning(f"Message with ID {id} not found in memory")
        return None
    
    def delete_message(self, id: str) -> bool:
        """
        Delete a message from memory.
        
        Args:
            id: ID of the message to delete
            
        Returns:
            True if successful, False otherwise
        """
        if self.chromadb_available:
            try:
                self.collection.delete(ids=[id])
                logger.debug(f"Deleted message with ID: {id}")
                return True
                
            except Exception as e:
                logger.error(f"Error deleting message: {str(e)}")
                # Fall back to in-memory method
        
        # Mock mode or fallback
        before_len = len(self.memory_items)
        self.memory_items = [item for item in self.memory_items if item.get('id') != id]
        
        # Check if any item was removed
        if len(self.memory_items) < before_len:
            self._save_memory_items()
            logger.debug(f"Deleted message with ID: {id} from memory")
            return True
        
        logger.warning(f"Message with ID {id} not found for deletion")
        return False
    
    def clear_memory(self) -> bool:
        """
        Clear all memory.
        
        Returns:
            True if successful, False otherwise
        """
        if self.chromadb_available:
            try:
                # Get the current collection name
                name = self.collection_name
                
                # Delete the collection
                self.client.delete_collection(name)
                logger.warning(f"Deleted collection '{name}'")
                
                # Recreate the collection
                self.collection = self.client.create_collection(
                    name=name,
                    embedding_function=None,
                    metadata={"hnsw:space": self.distance_metric}
                )
                
                logger.info(f"Recreated empty collection '{name}'")
                return True
                
            except Exception as e:
                logger.error(f"Error clearing memory: {str(e)}")
                # Fall back to in-memory method
        
        # Mock mode or fallback
        self.memory_items = []
        self._save_memory_items()
        logger.warning("Cleared in-memory storage")
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the vector store.
        
        Returns:
            Dictionary of statistics
        """
        if self.chromadb_available:
            try:
                # Get count of items
                count = self.collection.count()
                
                # Get all IDs to compute additional stats
                results = self.collection.get(
                    include=["metadatas"],
                    limit=10000  # Reasonable limit to avoid memory issues
                )
                
                stats = {
                    'total_items': count,
                    'collection_name': self.collection_name
                }
                
                # Add role counts if available
                if results and 'metadatas' in results:
                    user_count = sum(1 for meta in results['metadatas'] if meta.get('role') == 'user')
                    assistant_count = sum(1 for meta in results['metadatas'] if meta.get('role') == 'assistant')
                    doc_chunks = sum(1 for meta in results['metadatas'] if meta.get('type') == 'document_chunk')
                    
                    stats.update({
                        'user_messages': user_count,
                        'assistant_messages': assistant_count,
                        'document_chunks': doc_chunks
                    })
                    
                    # Get first and last timestamp if available
                    timestamps = [meta.get('timestamp', 0) for meta in results['metadatas']]
                    if timestamps:
                        stats.update({
                            'oldest_message': min(timestamps),
                            'newest_message': max(timestamps)
                        })
                
                return stats
                
            except Exception as e:
                logger.error(f"Error getting stats: {str(e)}")
                # Fall back to in-memory method
        
        # Mock mode
        user_count = sum(1 for item in self.memory_items if item.get('metadata', {}).get('role') == 'user')
        assistant_count = sum(1 for item in self.memory_items if item.get('metadata', {}).get('role') == 'assistant')
        doc_chunks = sum(1 for item in self.memory_items if item.get('metadata', {}).get('type') == 'document_chunk')
        
        timestamps = [item.get('metadata', {}).get('timestamp', 0) for item in self.memory_items]
        
        return {
            'total_items': len(self.memory_items),
            'collection_name': self.collection_name,
            'user_messages': user_count,
            'assistant_messages': assistant_count,
            'document_chunks': doc_chunks,
            'oldest_message': min(timestamps) if timestamps else 0,
            'newest_message': max(timestamps) if timestamps else 0
        } 