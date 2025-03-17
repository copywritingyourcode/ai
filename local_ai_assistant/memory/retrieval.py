"""
Memory retrieval module for constructing conversation context.

This module provides functions to retrieve and format relevant 
memory items from the vector store for inclusion in LLM prompts.
"""

import logging
import time
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
import yaml

# Local imports
from local_ai_assistant.memory.vector_store import VectorStore
from local_ai_assistant.utils.token_counter import count_tokens, truncate_text_to_token_limit


# Logger for this module
logger = logging.getLogger(__name__)


class MemoryRetriever:
    """
    Retrieves and formats conversation memory for inclusion in prompts.
    
    This class provides methods to create optimized context from the 
    conversation history stored in the vector store.
    """
    
    def __init__(self, config_path: Union[str, Path], vector_store: VectorStore):
        """
        Initialize the memory retriever.
        
        Args:
            config_path: Path to the configuration file
            vector_store: Vector store instance for memory retrieval
        """
        self.config_path = Path(config_path)
        self.vector_store = vector_store
        
        # Load configuration
        with open(self.config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # Extract memory retrieval settings
        retrieval_config = self.config['memory']['retrieval']
        
        self.max_relevant_chunks = retrieval_config['max_relevant_chunks']
        self.similarity_threshold = retrieval_config['similarity_threshold']
        self.max_history_tokens = retrieval_config['max_history_tokens']
        self.include_recent_turns = retrieval_config['include_recent_turns']
        
        # Model name for token counting
        self.model_name = self.config['models']['default']
        
        logger.info(f"Memory retriever initialized, max history: {self.max_history_tokens} tokens")
    
    def get_formatted_history(self, query: str) -> str:
        """
        Get formatted conversation history relevant to the current query.
        
        Args:
            query: Current user query
            
        Returns:
            Formatted string of relevant conversation history
        """
        # Get context messages from vector store
        context_messages = self.vector_store.get_conversation_context(
            query_text=query,
            n_relevant=self.max_relevant_chunks,
            include_recent=self.include_recent_turns
        )
        
        if not context_messages:
            logger.debug("No context messages found for query")
            return ""
        
        # Format messages into conversation history
        history = self._format_context_messages(context_messages)
        
        # Truncate to fit within token limit
        if count_tokens(history, self.model_name) > self.max_history_tokens:
            logger.debug(f"Truncating history from {count_tokens(history, self.model_name)} tokens")
            history = truncate_text_to_token_limit(history, self.max_history_tokens, self.model_name)
        
        return history
    
    def _format_context_messages(self, messages: List[Dict[str, Any]]) -> str:
        """
        Format context messages into a conversation history string.
        
        Args:
            messages: List of message dicts from vector store
            
        Returns:
            Formatted conversation history string
        """
        if not messages:
            return ""
        
        formatted_parts = []
        
        for msg in messages:
            role = msg['metadata'].get('role', 'unknown')
            text = msg['text']
            
            # Add timestamp if available
            timestamp_sec = msg['metadata'].get('timestamp')
            timestamp_str = ""
            
            if timestamp_sec:
                # Convert to readable format
                time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp_sec))
                timestamp_str = f" [{time_str}]"
            
            # Format as "User/Assistant: message"
            if role == 'user':
                formatted_parts.append(f"User{timestamp_str}: {text}")
            elif role == 'assistant':
                formatted_parts.append(f"Assistant{timestamp_str}: {text}")
            else:
                formatted_parts.append(f"{role.capitalize()}{timestamp_str}: {text}")
        
        # Join with double newlines for clarity
        return "\n\n".join(formatted_parts)
    
    def get_memory_as_messages(self, query: str) -> List[Dict[str, str]]:
        """
        Get memory items formatted as a list of message dictionaries.
        
        This format is suitable for the chat API where messages are
        passed as a sequence of role/content pairs.
        
        Args:
            query: Current user query
            
        Returns:
            List of message dicts with 'role' and 'content' keys
        """
        # Get context messages from vector store
        context_messages = self.vector_store.get_conversation_context(
            query_text=query,
            n_relevant=self.max_relevant_chunks,
            include_recent=self.include_recent_turns
        )
        
        if not context_messages:
            logger.debug("No context messages found for query")
            return []
        
        # Format as message list
        message_list = []
        
        for msg in context_messages:
            role = msg['metadata'].get('role')
            
            # Map roles to those expected by the chat API (user, assistant, system)
            if role == 'user':
                message_list.append({
                    'role': 'user',
                    'content': msg['text']
                })
            elif role == 'assistant':
                message_list.append({
                    'role': 'assistant',
                    'content': msg['text']
                })
            else:
                # Default to user for unknown roles
                logger.warning(f"Unknown role '{role}' in message, treating as user")
                message_list.append({
                    'role': 'user',
                    'content': msg['text']
                })
        
        # Check token count and trim if needed
        total_tokens = sum(count_tokens(msg['content'], self.model_name) for msg in message_list)
        
        if total_tokens > self.max_history_tokens:
            logger.debug(f"Trimming message list from {total_tokens} tokens")
            
            # Keep removing oldest messages until under token limit
            # (but always keep the most recent self.include_recent_turns messages)
            while (total_tokens > self.max_history_tokens and 
                   len(message_list) > self.include_recent_turns):
                
                # Remove the oldest message (not one of the recent ones)
                removed = message_list.pop(0)
                total_tokens -= count_tokens(removed['content'], self.model_name)
                
                logger.debug(f"Removed message, remaining tokens: {total_tokens}")
        
        return message_list
    
    def search_specific_topic(self, topic: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search for messages specifically about a topic.
        
        Args:
            topic: Topic to search for
            limit: Maximum number of results
            
        Returns:
            List of matching message dicts
        """
        return self.vector_store.search_memory(
            query_text=topic,
            n_results=limit
        )
    
    def get_memory_summary(self, query: str = "") -> str:
        """
        Generate a summary of the relevant conversation history.
        
        Args:
            query: Optional query for relevance (if empty, summarize recent)
            
        Returns:
            Summary text of the conversation history
        """
        # If no query, just get recent messages
        if not query:
            messages = self.vector_store.get_recent_messages(n=10)
        else:
            # Get relevant messages for the query
            messages = self.vector_store.search_memory(query_text=query, n_results=10)
        
        if not messages:
            return "No conversation history available."
        
        # Format summary text
        summary_parts = []
        
        # Count total messages in store
        stats = self.vector_store.get_stats()
        total_items = stats.get('total_items', 0)
        
        summary_parts.append(f"Conversation History Summary (from {total_items} total messages):")
        
        # Add extracted messages
        for i, msg in enumerate(messages):
            role = msg['metadata'].get('role', 'unknown')
            timestamp_sec = msg['metadata'].get('timestamp')
            
            time_str = ""
            if timestamp_sec:
                time_str = time.strftime('%Y-%m-%d %H:%M', time.localtime(timestamp_sec))
                
            speaker = "User" if role == 'user' else "Assistant"
            summary_parts.append(f"{i+1}. {speaker} ({time_str}): {msg['text'][:100]}...")
        
        return "\n".join(summary_parts) 