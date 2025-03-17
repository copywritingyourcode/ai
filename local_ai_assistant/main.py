#!/usr/bin/env python3
"""
Main module for Local AI Assistant.

This module initializes all components and starts the CLI interface.
"""

import argparse
import logging
import os
import sys
import yaml
from pathlib import Path

# Local imports
from local_ai_assistant.models.model_manager import ModelManager
from local_ai_assistant.memory.vector_store import VectorStore
from local_ai_assistant.document.loader import DocumentLoader
from local_ai_assistant.cli.interface import CLI


# Configure logger
def setup_logging(config):
    """Set up logging configuration."""
    log_config = config.get('logging', {})
    log_level = getattr(logging, log_config.get('level', 'INFO'))
    log_format = log_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    log_file = log_config.get('file')
    
    # Create log directory if it doesn't exist
    if log_file:
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
    
    # Configure logging
    handlers = []
    if log_file:
        handlers.append(logging.FileHandler(log_file))
    handlers.append(logging.StreamHandler())
    
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=handlers
    )
    
    # Log startup info
    logging.info("Logging initialized")


def main():
    """Initialize and run the assistant."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Local AI Assistant")
    parser.add_argument("--config", type=str, default="config.yaml", help="Path to config file")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args()
    
    try:
        # Load configuration
        config_path = Path(args.config).resolve()
        if not config_path.exists():
            print(f"Error: Config file not found: {config_path}")
            return 1
        
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Set up logging
        setup_logging(config)
        
        # Log startup information
        logging.info("Starting Local AI Assistant")
        
        # Initialize components
        logging.info("Initializing model manager")
        model_manager = ModelManager(config_path)
        
        logging.info("Initializing vector store")
        vector_store = VectorStore(config_path)
        
        logging.info("Initializing document loader")
        document_loader = DocumentLoader(config_path)
        
        # Initialize CLI with components
        debug_enabled = args.debug or config.get('debug', {}).get('enabled', False)
        cli = CLI(
            config_path=config_path,
            model_manager=model_manager,
            vector_store=vector_store,
            document_loader=document_loader,
            debug_enabled=debug_enabled
        )
        
        # Run the CLI
        return cli.run()
        
    except Exception as e:
        print(f"Error initializing assistant: {str(e)}")
        if args.debug:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())