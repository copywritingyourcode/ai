"""
Command parser for Local AI Assistant CLI.

This module provides functions to parse and interpret user commands.
"""

import logging
import shlex
from typing import Dict, List, Optional, Tuple, Any


# Logger for this module
logger = logging.getLogger(__name__)


def parse_command(command_text: str) -> Tuple[str, List[str], Dict[str, Any]]:
    """
    Parse a command string into command name, arguments, and options.
    
    Args:
        command_text: Raw command text from user
        
    Returns:
        Tuple of (command_name, positional_args, option_dict)
    """
    if not command_text or not command_text.startswith('/'):
        return '', [], {}
    
    # Remove leading slash and split by whitespace (respecting quotes)
    try:
        parts = shlex.split(command_text[1:])
    except ValueError as e:
        logger.warning(f"Error parsing command: {str(e)}")
        return '', [], {}
    
    if not parts:
        return '', [], {}
    
    # Command name is the first part
    command_name = parts[0].lower()
    
    # Extract options (--key=value or --flag) and args
    args = []
    options = {}
    
    for part in parts[1:]:
        if part.startswith('--'):
            # Handle --key=value format
            if '=' in part:
                key, value = part[2:].split('=', 1)
                options[key] = _parse_value(value)
            # Handle --flag format (boolean flag)
            else:
                options[part[2:]] = True
        else:
            args.append(part)
    
    logger.debug(f"Parsed command '{command_name}' with args={args}, options={options}")
    return command_name, args, options


def _parse_value(value_str: str) -> Any:
    """
    Convert string value to appropriate type.
    
    Args:
        value_str: String value from command
        
    Returns:
        Parsed value with appropriate type
    """
    # Convert numbers
    if value_str.isdigit():
        return int(value_str)
    
    # Convert floats
    try:
        float_val = float(value_str)
        # Check if it's actually an integer
        if float_val.is_integer():
            return int(float_val)
        return float_val
    except ValueError:
        pass
    
    # Convert booleans
    if value_str.lower() in ('true', 'yes', 'y'):
        return True
    if value_str.lower() in ('false', 'no', 'n'):
        return False
    
    # Leave as string
    return value_str 