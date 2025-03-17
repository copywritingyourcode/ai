#!/usr/bin/env python3
"""
Code Splitting CLI Tool

This script provides a command-line interface to split a codebase into
token-limited files for easier review by AI tools.
"""

import argparse
import logging
import os
import sys
from pathlib import Path

# Add the parent directory to the Python path to import local_ai_assistant
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from local_ai_assistant.code_tools.code_splitter import CodeSplitter

# Set up basic logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("code_split")


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Split codebase into token-limited files for AI review",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # Required arguments
    parser.add_argument(
        "path", 
        help="Path to the directory or list of files to process"
    )
    
    # Optional arguments
    parser.add_argument(
        "-o", "--output-dir", 
        help="Directory to save the split files",
        default="code_splits"
    )
    parser.add_argument(
        "-t", "--token-limit", 
        help="Maximum tokens per file",
        type=int,
        default=8000
    )
    parser.add_argument(
        "-m", "--model", 
        help="Model name for token counting",
        default="default"
    )
    parser.add_argument(
        "-c", "--config", 
        help="Path to config.yaml file",
        default="config.yaml"
    )
    parser.add_argument(
        "-r", "--recursive",
        help="Recursively process subdirectories",
        action="store_true",
        default=True
    )
    parser.add_argument(
        "--include-hidden",
        help="Include hidden files and directories",
        action="store_true",
        default=False
    )
    parser.add_argument(
        "-f", "--files",
        help="Process specific files instead of a directory",
        action="store_true",
        default=False
    )
    parser.add_argument(
        "-v", "--verbose",
        help="Increase output verbosity",
        action="store_true",
        default=False
    )
    
    return parser.parse_args()


def main():
    """Run the code splitter CLI tool."""
    args = parse_arguments()
    
    # Set log level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Check if config file exists
        config_path = Path(args.config)
        if not config_path.exists():
            logger.error(f"Config file not found: {config_path}")
            return 1
        
        # Initialize code splitter
        splitter = CodeSplitter(config_path)
        
        # Override default token limit if specified
        if args.token_limit:
            splitter.default_token_limit = args.token_limit
        
        # Process path
        path = Path(args.path)
        
        if args.files:
            # Process list of files
            if not path.exists() or not path.is_file():
                logger.error(f"File list not found: {path}")
                return 1
            
            # Read file list
            with open(path, 'r') as f:
                file_paths = [line.strip() for line in f if line.strip()]
            
            # Process files
            logger.info(f"Processing {len(file_paths)} files from list {path}")
            output_files = splitter.split_selected_files(
                file_paths=file_paths,
                output_dir=args.output_dir,
                token_limit=args.token_limit,
                model=args.model
            )
        else:
            # Process directory
            if not path.exists() or not path.is_dir():
                logger.error(f"Directory not found: {path}")
                return 1
            
            # Process directory
            logger.info(f"Processing directory: {path}")
            output_files = splitter.split_codebase(
                directory_path=path,
                output_dir=args.output_dir,
                token_limit=args.token_limit,
                recursive=args.recursive,
                include_hidden=args.include_hidden,
                model=args.model
            )
        
        # Print summary
        logger.info(f"Successfully generated {len(output_files)} files in {args.output_dir}")
        logger.info(f"Output directory: {os.path.abspath(args.output_dir)}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main()) 