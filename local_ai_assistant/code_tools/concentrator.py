"""
Code concentrator module for bundling code from multiple files.

This module provides functions to gather source code from a project
into a single document for easier analysis by AI tools.
"""

import logging
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple, Set
import yaml

# Logger for this module
logger = logging.getLogger(__name__)


class CodeConcentrator:
    """
    Gathers code from multiple files into a single document.
    
    This class provides methods to traverse a directory structure,
    collect code files, and combine them into a structured document
    for analysis by AI tools.
    """
    
    def __init__(self, config_path: Union[str, Path]):
        """
        Initialize the code concentrator.
        
        Args:
            config_path: Path to the configuration file
        """
        self.config_path = Path(config_path)
        
        # Load configuration
        with open(self.config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # Extract code tool settings
        code_tool_config = self.config['code_tools']['concentrator']
        
        # Patterns to ignore
        self.ignored_patterns = code_tool_config.get('ignored_patterns', [])
        
        # Extensions to include (if empty, include all non-binary files)
        self.include_extensions = code_tool_config.get('include_extensions', [])
        
        # Maximum file size (in KB) to include
        self.max_file_size_kb = code_tool_config.get('max_file_size_kb', 500)
        
        logger.info(f"Code concentrator initialized, ignored patterns: {self.ignored_patterns}")
    
    def concentrate_code(
        self, 
        directory_path: Union[str, Path],
        recursive: bool = True,
        include_hidden: bool = False
    ) -> str:
        """
        Gather code from directory into a single document.
        
        Args:
            directory_path: Path to the directory to concentrate
            recursive: Whether to recursively traverse subdirectories
            include_hidden: Whether to include hidden files and directories
            
        Returns:
            Concentrated code as a string
        """
        directory_path = Path(directory_path)
        
        # Check if directory exists
        if not directory_path.exists() or not directory_path.is_dir():
            logger.error(f"Directory not found: {directory_path}")
            return f"Error: Directory not found: {directory_path}"
        
        # Get list of files
        files = self._get_files(directory_path, recursive, include_hidden)
        
        # Read and concatenate files
        concentrated_code = self._concatenate_files(files, directory_path)
        
        return concentrated_code
    
    def _get_files(
        self, 
        directory_path: Path,
        recursive: bool,
        include_hidden: bool
    ) -> List[Path]:
        """
        Get list of files to concentrate.
        
        Args:
            directory_path: Path to the directory
            recursive: Whether to recursively traverse subdirectories
            include_hidden: Whether to include hidden files and directories
            
        Returns:
            List of file paths
        """
        files = []
        
        # Use os.walk for efficiency
        for root, dirs, filenames in os.walk(directory_path):
            # Convert root to Path
            root_path = Path(root)
            
            # Filter out directories to skip
            dirs_to_remove = []
            for d in dirs:
                # Skip hidden directories if not included
                if not include_hidden and d.startswith('.'):
                    dirs_to_remove.append(d)
                    continue
                
                # Skip directories matching ignored patterns
                if self._should_ignore(d):
                    dirs_to_remove.append(d)
                    continue
            
            # Remove directories from the walk
            for d in dirs_to_remove:
                dirs.remove(d)
            
            # Stop recursion if not recursive
            if not recursive:
                dirs.clear()
            
            # Process files
            for filename in filenames:
                # Skip hidden files if not included
                if not include_hidden and filename.startswith('.'):
                    continue
                
                # Skip files matching ignored patterns
                if self._should_ignore(filename):
                    continue
                
                # Get file path
                file_path = root_path / filename
                
                # Skip if not a regular file
                if not file_path.is_file():
                    continue
                
                # Skip if too large
                if file_path.stat().st_size > self.max_file_size_kb * 1024:
                    logger.warning(f"Skipping file {file_path} (too large: {file_path.stat().st_size / 1024:.1f} KB)")
                    continue
                
                # Skip if not a text file (simple check)
                if not self._is_text_file(file_path):
                    logger.debug(f"Skipping binary file: {file_path}")
                    continue
                
                # Skip if extension not included (if extensions list is provided)
                if self.include_extensions and file_path.suffix.lower().lstrip('.') not in self.include_extensions:
                    continue
                
                # Add file to list
                files.append(file_path)
        
        return files
    
    def _should_ignore(self, name: str) -> bool:
        """
        Check if a file or directory name should be ignored.
        
        Args:
            name: File or directory name
            
        Returns:
            True if the name should be ignored, False otherwise
        """
        for pattern in self.ignored_patterns:
            # Convert glob pattern to regex
            if pattern.startswith('*'):
                pattern = '.' + pattern
            
            regex = pattern.replace('.', '\\.').replace('*', '.*')
            if re.match(regex, name):
                return True
        
        return False
    
    def _is_text_file(self, file_path: Path) -> bool:
        """
        Check if a file is a text file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if the file is a text file, False otherwise
        """
        # Common text file extensions
        text_extensions = {
            'txt', 'md', 'py', 'js', 'jsx', 'ts', 'tsx', 'html', 'css', 'scss',
            'json', 'yaml', 'yml', 'toml', 'ini', 'cfg', 'conf', 'xml', 'sh',
            'bash', 'c', 'cpp', 'h', 'hpp', 'java', 'kt', 'cs', 'go', 'rs',
            'php', 'rb', 'pl', 'pm', 'lua', 'swift', 'r', 'sql', 'bat', 'ps1'
        }
        
        # Check extension
        ext = file_path.suffix.lower().lstrip('.')
        if ext in text_extensions:
            return True
        
        # If no extension or unknown extension, check file content
        try:
            with open(file_path, 'rb') as f:
                # Read the first 1024 bytes
                data = f.read(1024)
                
                # If file contains null bytes, it's probably binary
                if b'\x00' in data:
                    return False
                
                # Check if at least 90% of bytes are in ASCII range
                ascii_bytes = sum(1 for b in data if b < 128)
                if len(data) > 0 and ascii_bytes / len(data) < 0.9:
                    return False
                
                return True
                
        except Exception as e:
            logger.warning(f"Error checking if file is text: {str(e)}")
            return False
    
    def _concatenate_files(self, files: List[Path], base_dir: Path) -> str:
        """
        Concatenate files into a single document.
        
        Args:
            files: List of file paths
            base_dir: Base directory for relative paths
            
        Returns:
            Concatenated code as a string
        """
        result = []
        
        # Sort files to ensure deterministic output
        files.sort()
        
        for file_path in files:
            try:
                # Get relative path
                relative_path = file_path.relative_to(base_dir)
                
                # Read file content
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
                
                # Add file header
                result.append(f"\n\n### File: {relative_path} ###\n")
                
                # Add file content
                result.append(content)
                
            except Exception as e:
                logger.warning(f"Error reading file {file_path}: {str(e)}")
                result.append(f"\n\n### File: {relative_path} (Error: {str(e)}) ###\n")
        
        return "\n".join(result)
    
    def concentrate_selected_files(
        self, 
        file_paths: List[Union[str, Path]],
        base_dir: Optional[Union[str, Path]] = None
    ) -> str:
        """
        Concentrate specific files into a single document.
        
        Args:
            file_paths: List of file paths to concentrate
            base_dir: Base directory for relative paths (optional)
            
        Returns:
            Concentrated code as a string
        """
        # Convert paths to Path objects
        files = [Path(p) for p in file_paths]
        
        # Determine base directory
        if base_dir:
            base_dir = Path(base_dir)
        else:
            # Try to find a common parent directory
            common_parents = []
            for file_path in files:
                if file_path.exists():
                    common_parents.append(file_path.parent)
            
            if common_parents:
                # Find common parent
                base_dir = Path(os.path.commonpath(common_parents))
            else:
                # Use current directory as fallback
                base_dir = Path.cwd()
        
        # Filter existing files
        existing_files = [p for p in files if p.exists() and p.is_file()]
        
        if not existing_files:
            logger.warning("No valid files to concentrate")
            return "Error: No valid files to concentrate"
        
        # Concatenate files
        return self._concatenate_files(existing_files, base_dir) 