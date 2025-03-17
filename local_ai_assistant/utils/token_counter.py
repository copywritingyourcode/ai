"""
Token counter module for measuring token usage.

This module provides functions to count tokens in text for different models.
"""

import logging
import re
from typing import Dict, List, Optional, Any, Union, Callable

# Try importing tiktoken, but don't fail if it's not available
try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False

# Logger for this module
logger = logging.getLogger(__name__)


class TokenCounter:
    """
    Counts tokens in text for different LLM models.
    
    This class provides methods to estimate token counts for different
    models, helpful for managing context windows and usage tracking.
    """
    
    def __init__(self):
        """Initialize the token counter."""
        self.tiktoken_available = TIKTOKEN_AVAILABLE
        self.encoders = {}
        
        if self.tiktoken_available:
            try:
                # Initialize common encoders
                self.encoders["cl100k_base"] = tiktoken.get_encoding("cl100k_base")  # GPT-4, GPT-3.5-Turbo
                logger.debug("Initialized cl100k_base encoder")
            except Exception as e:
                logger.warning(f"Error initializing tiktoken encoders: {str(e)}")
                self.tiktoken_available = False
    
    def count_tokens(self, text: str, model: str = "default") -> int:
        """
        Count tokens in text for a specific model.
        
        Args:
            text: Text to count tokens in
            model: Model name or encoding to use
            
        Returns:
            Estimated token count
        """
        if not text:
            return 0
            
        # Use tiktoken if available
        if self.tiktoken_available:
            try:
                # Map model names to encoding names
                encoding_name = self._get_encoding_for_model(model)
                
                # Get or create encoder
                if encoding_name not in self.encoders:
                    self.encoders[encoding_name] = tiktoken.get_encoding(encoding_name)
                
                # Count tokens
                encoder = self.encoders[encoding_name]
                tokens = encoder.encode(text)
                return len(tokens)
            except Exception as e:
                logger.warning(f"Error counting tokens with tiktoken: {str(e)}")
                # Fall back to heuristic method
        
        # Fall back to heuristic token counting
        return self._count_tokens_heuristic(text)
    
    def _get_encoding_for_model(self, model: str) -> str:
        """
        Get the appropriate encoding name for a model.
        
        Args:
            model: Model name
            
        Returns:
            Encoding name
        """
        # Map common model names to encodings
        model = model.lower()
        
        if model in ["gpt-4", "gpt-3.5-turbo", "text-embedding-ada-002"] or model.startswith("gpt-4-") or model.startswith("gpt-3.5-turbo-"):
            return "cl100k_base"
        elif "llama" in model or "gemma" in model or "mistral" in model:
            # Many recent models (Llama, Gemma) use similar tokenization to cl100k
            return "cl100k_base"
        else:
            # Default to cl100k for most modern models
            return "cl100k_base"
    
    def _count_tokens_heuristic(self, text: str) -> int:
        """
        Count tokens using a simple heuristic approach.
        
        This is a fallback when tiktoken is not available.
        
        Args:
            text: Text to count tokens in
            
        Returns:
            Estimated token count
        """
        # Simple heuristic: split on whitespace and punctuation
        words = re.findall(r'\w+|[^\w\s]', text)
        
        # Count the number of words
        word_count = len(words)
        
        # Estimate tokens (typically, tokens are ~75% of words for English text)
        # This is very approximate and will be more accurate for some
        # languages than others
        token_count = int(word_count * 1.3)
        
        return token_count
    
    def truncate_to_token_limit(self, text: str, max_tokens: int, model: str = "default") -> str:
        """
        Truncate text to fit within a token limit.
        
        Args:
            text: Text to truncate
            max_tokens: Maximum number of tokens
            model: Model name or encoding to use
            
        Returns:
            Truncated text
        """
        if not text:
            return ""
            
        # Count tokens in the original text
        token_count = self.count_tokens(text, model)
        
        # If already under the limit, return as is
        if token_count <= max_tokens:
            return text
            
        # Use tiktoken for accurate truncation if available
        if self.tiktoken_available:
            try:
                # Get the appropriate encoding
                encoding_name = self._get_encoding_for_model(model)
                
                # Get or create encoder
                if encoding_name not in self.encoders:
                    self.encoders[encoding_name] = tiktoken.get_encoding(encoding_name)
                
                # Encode the text
                encoder = self.encoders[encoding_name]
                tokens = encoder.encode(text)
                
                # Truncate tokens
                truncated_tokens = tokens[:max_tokens]
                
                # Decode back to text
                truncated_text = encoder.decode(truncated_tokens)
                return truncated_text
            except Exception as e:
                logger.warning(f"Error truncating with tiktoken: {str(e)}")
                # Fall back to heuristic method
        
        # Fall back to heuristic truncation (less accurate)
        return self._truncate_heuristic(text, max_tokens)
    
    def _truncate_heuristic(self, text: str, max_tokens: int) -> str:
        """
        Truncate text using a heuristic approach.
        
        Args:
            text: Text to truncate
            max_tokens: Maximum number of tokens
            
        Returns:
            Truncated text
        """
        # Simple approach: estimate average chars per token and truncate
        # Average English token is about 4 characters
        chars_per_token = 4
        
        # Calculate character limit
        char_limit = max_tokens * chars_per_token
        
        # Truncate text
        if len(text) > char_limit:
            return text[:char_limit]
        
        return text


def get_encoder(model_name: str) -> tiktoken.Encoding:
    """
    Get the appropriate tokenizer for a given model.
    
    Args:
        model_name: Name of the model to get tokenizer for
        
    Returns:
        A tiktoken Encoding for the specified model
    """
    # Use cached encoder if available
    if model_name in _ENCODER_CACHE:
        return _ENCODER_CACHE[model_name]
    
    try:
        # Handle common model families
        if model_name.startswith(("gpt-3.5", "gpt-4")):
            encoding_name = "cl100k_base"  # GPT-3.5/4 encoding
        elif model_name.startswith(("text-embedding-ada", "text-davinci")):
            encoding_name = "cl100k_base"  # Ada/Davinci encoding
        elif "gemma" in model_name.lower():
            # Gemma models use a custom tokenizer, but cl100k is a reasonable approximation
            encoding_name = "cl100k_base"
        elif "llama" in model_name.lower():
            # Llama tokenizer approximation
            encoding_name = "cl100k_base"
        else:
            # Default to cl100k for unknown models
            encoding_name = "cl100k_base"
            logger.warning(f"Unknown model: {model_name}, using cl100k_base tokenizer as an approximation")
        
        # Get the encoding
        encoding = tiktoken.get_encoding(encoding_name)
        _ENCODER_CACHE[model_name] = encoding
        return encoding
        
    except Exception as e:
        logger.error(f"Error getting tokenizer for model {model_name}: {str(e)}")
        # Fallback to cl100k_base
        logger.warning(f"Falling back to cl100k_base tokenizer")
        encoding = tiktoken.get_encoding("cl100k_base")
        _ENCODER_CACHE[model_name] = encoding
        return encoding


def count_tokens(text: str, model_name: str = "gemma3:27b") -> int:
    """
    Count the number of tokens in a text string.
    
    Args:
        text: The text to count tokens for
        model_name: The model to use for tokenization
        
    Returns:
        Number of tokens in the text
    """
    if not text:
        return 0
    
    try:
        # Clean model name (remove Ollama prefixes if present)
        clean_model_name = model_name.split(":")[-1] if ":" in model_name else model_name
        
        # Get encoder and count tokens
        encoder = get_encoder(clean_model_name)
        tokens = encoder.encode(text)
        return len(tokens)
    except Exception as e:
        logger.error(f"Error counting tokens: {str(e)}")
        # Fallback to character approximation (very rough)
        approx_tokens = len(text) // 4
        logger.warning(f"Using character approximation: ~{approx_tokens} tokens")
        return approx_tokens


def truncate_text_to_token_limit(
    text: str, 
    max_tokens: int, 
    model_name: str = "gemma3:27b"
) -> str:
    """
    Truncate text to fit within a token limit.
    
    Args:
        text: Text to truncate
        max_tokens: Maximum number of tokens allowed
        model_name: Model to use for tokenization
        
    Returns:
        Truncated text that fits within the token limit
    """
    if not text:
        return ""
    
    try:
        # Get tokens
        clean_model_name = model_name.split(":")[-1] if ":" in model_name else model_name
        encoder = get_encoder(clean_model_name)
        tokens = encoder.encode(text)
        
        # Check if truncation is needed
        if len(tokens) <= max_tokens:
            return text
        
        # Truncate tokens and decode
        truncated_tokens = tokens[:max_tokens]
        truncated_text = encoder.decode(truncated_tokens)
        return truncated_text
    except Exception as e:
        logger.error(f"Error truncating text: {str(e)}")
        # Fallback to character approximation
        chars_per_token = 4  # Rough approximation
        max_chars = max_tokens * chars_per_token
        logger.warning(f"Using character approximation for truncation")
        return text[:max_chars]


def estimate_tokens_from_chunk_count(
    text: str, 
    num_chunks: int,
    model_name: str = "gemma3:27b"
) -> int:
    """
    Estimate tokens per chunk by dividing total tokens by number of chunks.
    
    Args:
        text: Full text
        num_chunks: Number of chunks to create
        model_name: Model to use for tokenization
        
    Returns:
        Estimated tokens per chunk
    """
    total_tokens = count_tokens(text, model_name)
    return total_tokens // num_chunks 