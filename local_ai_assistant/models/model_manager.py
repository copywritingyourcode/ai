"""
Model manager for Local AI Assistant.

This module handles loading, unloading, and interacting with Ollama models.
"""

import logging
import os
import time
import json
import sys
import yaml
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple

# Try importing Ollama, but don't fail if it's not available
try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

# Local imports
from local_ai_assistant.utils.token_counter import TokenCounter

# Logger for this module
logger = logging.getLogger(__name__)


class ModelManager:
    """
    Manages Ollama models for the Local AI Assistant.
    
    This class handles loading, unloading, switching, and generating text
    using Ollama models.
    """
    
    def __init__(self, config_path: Union[str, Path]):
        """
        Initialize the model manager.
        
        Args:
            config_path: Path to the configuration file
        """
        self.config_path = Path(config_path)
        
        # Load configuration
        with open(self.config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # Extract model settings
        model_config = self.config['model']
        
        # Default model
        self.default_model = model_config.get('default', 'gemma3:27b')
        self.active_model = self.default_model
        
        # Model parameters
        self.temperature = model_config.get('temperature', 0.7)
        self.max_tokens = model_config.get('max_tokens', 2000)
        
        # Embedding model
        self.embedding_model = model_config.get('embedding', 'nomic-embed-text')
        
        # Ollama settings
        if 'ollama' in model_config:
            ollama_config = model_config['ollama']
            self.ollama_host = ollama_config.get('host', 'http://localhost')
            self.ollama_port = ollama_config.get('port', 11434)
        else:
            self.ollama_host = 'http://localhost'
            self.ollama_port = 11434
        
        # Initialize token counter
        self.token_counter = TokenCounter()
        
        # Check if Ollama is available
        self.ollama_available = OLLAMA_AVAILABLE and self._check_ollama_available()
        
        if self.ollama_available:
            # Set Ollama host if needed
            if self.ollama_host != 'http://localhost' or self.ollama_port != 11434:
                os.environ['OLLAMA_HOST'] = f"{self.ollama_host}:{self.ollama_port}"
            
            # Try to load the default model
            self.load_model(self.default_model)
        else:
            logger.warning("Ollama is not available. Running in mock mode.")
    
    def _check_ollama_available(self) -> bool:
        """
        Check if Ollama service is available.
        
        Returns:
            True if Ollama is available, False otherwise
        """
        if not OLLAMA_AVAILABLE:
            logger.warning("Ollama Python package is not installed")
            return False
            
        try:
            # Try to list models
            ollama.list()
            logger.info("Ollama service is available")
            return True
        except Exception as e:
            logger.warning(f"Ollama service is not available: {str(e)}")
            return False
    
    def list_models(self) -> List[Dict[str, Any]]:
        """
        List available models.
        
        Returns:
            List of model information dictionaries
        """
        if not self.ollama_available:
            # Return mock data with proper names
            return [
                {'name': 'gemma3:27b', 'size': 27000000000, 'modified_at': time.time()},
                {'name': 'llama3:8b', 'size': 8000000000, 'modified_at': time.time()},
                {'name': 'mistral:7b', 'size': 7000000000, 'modified_at': time.time()},
                {'name': 'nomic-embed-text', 'size': 500000000, 'modified_at': time.time()},
                {'name': 'deepseek-rag', 'size': 7000000000, 'modified_at': time.time()}
            ]
        
        try:
            response = ollama.list()
            
            # Handle new Ollama API response format (after ollama v0.1.26)
            if hasattr(response, 'models') and isinstance(response.models, list):
                # Convert new response format to dict format for backward compatibility
                return [
                    {
                        'name': model.model,
                        'size': getattr(model, 'size', 0),
                        'modified_at': getattr(model, 'modified_at', time.time()),
                        'details': getattr(model, 'details', {})
                    }
                    for model in response.models
                ]
            # Handle older Ollama API response format (dict with 'models' key)
            elif isinstance(response, dict) and 'models' in response:
                return response.get('models', [])
            else:
                logger.error(f"Unexpected response format from Ollama: {response}")
                return []
        except Exception as e:
            logger.error(f"Error listing models: {str(e)}")
            return []
    
    def load_model(self, model_name: str) -> bool:
        """
        Load a model.
        
        Args:
            model_name: Name of the model to load
            
        Returns:
            True if successful, False otherwise
        """
        if not self.ollama_available:
            logger.info(f"Mock loading model: {model_name}")
            self.active_model = model_name
            return True
            
        try:
            # Check if model is already available
            models = self.list_models()
            model_names = [model.get('name') for model in models]
            
            if model_name not in model_names:
                logger.info(f"Pulling model: {model_name}")
                ollama.pull(model_name)
                
            self.active_model = model_name
            logger.info(f"Loaded model: {model_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading model {model_name}: {str(e)}")
            return False
    
    def unload_model(self, model_name: str) -> bool:
        """
        Unload a model.
        
        Args:
            model_name: Name of the model to unload
            
        Returns:
            True if the model was unloaded successfully, False otherwise
        """
        if not self.ollama_available:
            logger.info(f"Mock unloading model: {model_name}")
            return True
            
        # For now, we don't actually unload the model
        # Ollama handles resource management
        logger.info(f"Model {model_name} will be managed by Ollama")
        return True
    
    def switch_model(self, model_name: str) -> bool:
        """
        Switch to a different model.
        
        Args:
            model_name: Name of the model to switch to
            
        Returns:
            True if the switch was successful, False otherwise
        """
        if not self.ollama_available:
            logger.info(f"Mock switching to model: {model_name}")
            self.active_model = model_name
            return True
            
        # Check if model exists
        models = self.list_models()
        model_names = [model.get('name') for model in models]
        
        if model_name not in model_names:
            logger.warning(f"Model {model_name} is not available")
            
            # Try to load the model
            if not self.load_model(model_name):
                return False
        
        # Set active model
        self.active_model = model_name
        logger.info(f"Switched to model: {model_name}")
        
        return True
    
    def generate_text(self, prompt: str, **kwargs) -> str:
        """
        Generate text using the active model.
        
        Args:
            prompt: Input prompt
            **kwargs: Additional parameters to pass to the model
            
        Returns:
            Generated text
        """
        if not self.ollama_available:
            logger.info("Mock generating text (Ollama not available)")
            time.sleep(1)  # Simulate processing time
            
            # Return a mock response
            return f"This is a mock response from {self.active_model}. Ollama is not available."
            
        try:
            # Check if the generate method requires parameters in 'options'
            # or directly as keyword arguments based on Ollama version
            try:
                # Try the new API format with options
                params = {
                    'model': self.active_model,
                    'prompt': prompt,
                    'options': {
                        'temperature': kwargs.get('temperature', self.temperature),
                        'num_predict': kwargs.get('max_tokens', self.max_tokens)
                    }
                }
                
                # Generate response
                response = ollama.generate(**params)
            except TypeError as e:
                # If that fails, try the old API format
                logger.warning(f"Trying old API format: {str(e)}")
                params = {
                    'model': self.active_model,
                    'prompt': prompt
                }
                
                # Add params directly if the options format failed
                if 'temperature' in kwargs or self.temperature is not None:
                    params['temperature'] = kwargs.get('temperature', self.temperature)
                if 'max_tokens' in kwargs or self.max_tokens is not None:
                    params['num_predict'] = kwargs.get('max_tokens', self.max_tokens)
                
                # Generate response
                response = ollama.generate(**params)
            
            # Handle both dictionary and object responses
            if isinstance(response, dict):
                return response.get('response', '')
            elif hasattr(response, 'response'):
                return response.response
            else:
                logger.warning(f"Unexpected response format: {response}")
                return str(response)
            
        except Exception as e:
            logger.error(f"Error generating text: {str(e)}")
            return f"Error generating response: {str(e)}"
    
    def generate_chat_response(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """
        Generate a chat response using the active model.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            **kwargs: Additional parameters to pass to the model
            
        Returns:
            Generated response text
        """
        if not self.ollama_available:
            logger.info("Mock generating chat response (Ollama not available)")
            time.sleep(1)  # Simulate processing time
            
            # Return a mock response
            return f"This is a mock chat response from {self.active_model}. Ollama is not available."
            
        try:
            # Try the new API format with options
            try:
                # Set default parameters
                params = {
                    'model': self.active_model,
                    'messages': messages,
                    'options': {
                        'temperature': kwargs.get('temperature', self.temperature),
                        'num_predict': kwargs.get('max_tokens', self.max_tokens)
                    }
                }
                
                # Generate response
                response = ollama.chat(**params)
            except TypeError as e:
                # If that fails, try the old API format
                logger.warning(f"Trying old API format: {str(e)}")
                params = {
                    'model': self.active_model,
                    'messages': messages
                }
                
                # Add params directly if the options format failed
                if 'temperature' in kwargs or self.temperature is not None:
                    params['temperature'] = kwargs.get('temperature', self.temperature)
                if 'max_tokens' in kwargs or self.max_tokens is not None:
                    params['num_predict'] = kwargs.get('max_tokens', self.max_tokens)
                
                # Generate response
                response = ollama.chat(**params)
            
            # Handle both old and new Ollama API formats
            if isinstance(response, dict):
                # Old format with message dictionary
                if 'message' in response:
                    return response['message'].get('content', '')
                # New format with direct response
                elif 'response' in response:
                    return response.get('response', '')
            # New format with object attributes
            elif hasattr(response, 'message') and hasattr(response.message, 'content'):
                return response.message.content
            elif hasattr(response, 'response'):
                return response.response
                
            # Fallback
            logger.warning(f"Unexpected response format: {response}")
            return str(response)
            
        except Exception as e:
            logger.error(f"Error generating chat response: {str(e)}")
            return f"Error generating chat response: {str(e)}"
    
    def generate_embeddings(self, texts: Union[str, List[str]]) -> List[List[float]]:
        """
        Generate embeddings for text.
        
        Args:
            texts: Text or list of texts to embed
            
        Returns:
            List of embedding vectors
        """
        if isinstance(texts, str):
            texts = [texts]
            
        if not self.ollama_available:
            logger.info("Mock generating embeddings (Ollama not available)")
            
            # Return mock embeddings (128-dimensional vectors of 0.0)
            return [[0.0] * 128 for _ in range(len(texts))]
            
        try:
            embeddings = []
            
            for text in texts:
                # Generate embedding
                response = ollama.embeddings(
                    model=self.embedding_model,
                    prompt=text
                )
                
                # Extract embedding from response
                if isinstance(response, dict) and 'embedding' in response:
                    embeddings.append(response['embedding'])
                elif hasattr(response, 'embedding'):
                    embeddings.append(response.embedding)
                else:
                    logger.error(f"No embedding in response: {response}")
                    embeddings.append([0.0] * 128)  # Fallback
            
            return embeddings
            
        except Exception as e:
            logger.error(f"Error generating embeddings: {str(e)}")
            return [[0.0] * 128 for _ in range(len(texts))]  # Fallback
    
    def shutdown(self):
        """Clean up resources before exit."""
        if not self.ollama_available:
            return
            
        logger.info("Shutting down model manager")
        # Nothing to do for now, as Ollama manages its own resources 