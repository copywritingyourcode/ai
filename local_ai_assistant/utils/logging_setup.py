"""
Logging setup module for the Local AI Assistant.

This module configures logging for the entire application based on the 
configuration file settings.
"""

import os
import logging
import logging.handlers
from pathlib import Path
import yaml


def setup_logging(config_path, override_level=None):
    """
    Configure logging based on configuration file settings.
    
    Args:
        config_path (Path): Path to the configuration file
        override_level (str, optional): Override logging level from command line
    """
    # Load configuration
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Determine log level
    log_level_str = override_level or config['system']['log_level']
    log_level = getattr(logging, log_level_str)
    
    # Create log directory if it doesn't exist
    log_dir = Path(config['system']['log_dir'])
    log_dir.mkdir(exist_ok=True, parents=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_format)
    root_logger.addHandler(console_handler)
    
    # Create file handler for general logs
    general_log_path = log_dir / 'assistant.log'
    file_handler = logging.handlers.RotatingFileHandler(
        general_log_path,
        maxBytes=10485760,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(log_level)
    file_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(file_format)
    root_logger.addHandler(file_handler)
    
    # Create error log handler
    error_log_path = log_dir / 'errors.log'
    error_handler = logging.handlers.RotatingFileHandler(
        error_log_path,
        maxBytes=10485760,  # 10MB
        backupCount=5
    )
    error_handler.setLevel(logging.ERROR)
    error_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    error_handler.setFormatter(error_format)
    root_logger.addHandler(error_handler)
    
    # Create debug log handler if in debug mode
    if log_level <= logging.DEBUG:
        debug_log_path = log_dir / 'debug.log'
        debug_handler = logging.handlers.RotatingFileHandler(
            debug_log_path,
            maxBytes=10485760,  # 10MB
            backupCount=5
        )
        debug_handler.setLevel(logging.DEBUG)
        debug_format = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(pathname)s:%(lineno)d - %(message)s'
        )
        debug_handler.setFormatter(debug_format)
        root_logger.addHandler(debug_handler)
    
    # Log initial startup message
    logging.info("Logging initialized")
    
    # Log configuration path
    logging.debug(f"Using configuration file: {config_path}")
    
    # Return the configured logger (mainly for testing)
    return root_logger 