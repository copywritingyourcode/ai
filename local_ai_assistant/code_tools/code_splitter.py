"""
Code splitter module for creating token-limited code files.

This module extends the CodeConcentrator to split concentrated code into multiple 
files that fit within AI token limits for easier uploading and review.
"""

import logging
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Union, Tuple
import yaml
import sys
import json

# Local imports
from .concentrator import CodeConcentrator
from ..utils.token_counter import TokenCounter

# Logger for this module
logger = logging.getLogger(__name__)


class CodeSplitter:
    """
    Splits concentrated code into token-limited files.
    
    This class extends the CodeConcentrator functionality to create multiple
    files that are sized appropriately for AI model token limits.
    """
    
    def __init__(self, config_path: Union[str, Path]):
        """
        Initialize the code splitter.
        
        Args:
            config_path: Path to the configuration file
        """
        self.config_path = Path(config_path)
        
        # Load configuration
        with open(self.config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # Create concentrator
        self.concentrator = CodeConcentrator(config_path)
        
        # Create token counter
        self.token_counter = TokenCounter()
        
        # Default token limit for AI models
        self.default_token_limit = 8000  # Conservative default
        
        # Output directory for splits
        self.output_dir = Path("code_splits")
        
        logger.info(f"Code splitter initialized with token limit: {self.default_token_limit}")
    
    def split_codebase(
        self,
        directory_path: Union[str, Path],
        output_dir: Optional[Union[str, Path]] = None,
        token_limit: int = None,
        recursive: bool = True,
        include_hidden: bool = False,
        model: str = "default"
    ) -> List[Path]:
        """
        Split codebase into token-limited files.
        
        Args:
            directory_path: Path to the directory with code to split
            output_dir: Directory to save the split files (default: './code_splits')
            token_limit: Maximum tokens per file (default: 8000)
            recursive: Whether to recursively traverse subdirectories
            include_hidden: Whether to include hidden files and directories
            model: Model name for token counting
            
        Returns:
            List of paths to the generated files
        """
        # Set output directory
        if output_dir:
            self.output_dir = Path(output_dir)
        
        # Set token limit
        if token_limit is None:
            token_limit = self.default_token_limit
        
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # First concentrate the code
        concentrated_code = self.concentrator.concentrate_code(
            directory_path, recursive, include_hidden
        )
        
        # Get token count of concentrated code
        total_tokens = self.token_counter.count_tokens(concentrated_code, model)
        logger.info(f"Total tokens in concentrated code: {total_tokens}")
        
        # Split the code into chunks
        code_chunks = self._split_code(concentrated_code, token_limit, model)
        logger.info(f"Split code into {len(code_chunks)} chunks")
        
        # Write chunks to files
        output_files = self._write_chunks_to_files(code_chunks, Path(directory_path).name)
        
        # Write metadata file
        self._write_metadata(directory_path, output_files, total_tokens)
        
        return output_files
    
    def split_selected_files(
        self,
        file_paths: List[Union[str, Path]],
        output_dir: Optional[Union[str, Path]] = None,
        token_limit: int = None,
        base_dir: Optional[Union[str, Path]] = None,
        model: str = "default"
    ) -> List[Path]:
        """
        Split selected files into token-limited files.
        
        Args:
            file_paths: List of file paths to split
            output_dir: Directory to save the split files
            token_limit: Maximum tokens per file
            base_dir: Base directory for relative paths
            model: Model name for token counting
            
        Returns:
            List of paths to the generated files
        """
        # Set output directory
        if output_dir:
            self.output_dir = Path(output_dir)
        
        # Set token limit
        if token_limit is None:
            token_limit = self.default_token_limit
        
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # First concentrate the selected files
        concentrated_code = self.concentrator.concentrate_selected_files(
            file_paths, base_dir
        )
        
        # Get token count of concentrated code
        total_tokens = self.token_counter.count_tokens(concentrated_code, model)
        logger.info(f"Total tokens in concentrated code: {total_tokens}")
        
        # Split the code into chunks
        code_chunks = self._split_code(concentrated_code, token_limit, model)
        logger.info(f"Split code into {len(code_chunks)} chunks")
        
        # Determine project name
        if base_dir:
            project_name = Path(base_dir).name
        else:
            # Try to extract a common prefix from filenames
            common_parent = os.path.commonpath([str(Path(f)) for f in file_paths])
            project_name = Path(common_parent).name or "selected_files"
        
        # Write chunks to files
        output_files = self._write_chunks_to_files(code_chunks, project_name)
        
        # Write metadata file
        self._write_metadata(file_paths, output_files, total_tokens)
        
        return output_files
    
    def _split_code(
        self,
        concentrated_code: str,
        token_limit: int,
        model: str = "default"
    ) -> List[str]:
        """
        Split concentrated code into chunks respecting file boundaries.
        
        Args:
            concentrated_code: Concentrated code to split
            token_limit: Maximum tokens per chunk
            model: Model name for token counting
            
        Returns:
            List of code chunks
        """
        # Split code by file boundary markers
        file_pattern = r'(\n\n### File: [^\n]+ ###\n)'
        file_blocks = re.split(file_pattern, concentrated_code)
        
        # Reassemble file headers with their content
        files = []
        current_header = None
        
        for block in file_blocks:
            if block.startswith('\n\n### File:'):
                current_header = block
            elif current_header is not None:
                files.append(current_header + block)
                current_header = None
        
        # Now we have a list of individual files with their headers
        chunks = []
        current_chunk = []
        current_tokens = 0
        
        for file_content in files:
            file_tokens = self.token_counter.count_tokens(file_content, model)
            
            # If this file alone exceeds token limit, we need to split it
            if file_tokens > token_limit:
                # If we have content in the current chunk, add it first
                if current_chunk:
                    chunks.append(''.join(current_chunk))
                    current_chunk = []
                    current_tokens = 0
                
                # Split this large file
                file_chunks = self._split_large_file(file_content, token_limit, model)
                chunks.extend(file_chunks)
                continue
            
            # If adding this file would exceed the limit, start a new chunk
            if current_tokens + file_tokens > token_limit and current_chunk:
                chunks.append(''.join(current_chunk))
                current_chunk = []
                current_tokens = 0
            
            # Add this file to the current chunk
            current_chunk.append(file_content)
            current_tokens += file_tokens
        
        # Add the last chunk if it has content
        if current_chunk:
            chunks.append(''.join(current_chunk))
        
        return chunks
    
    def _split_large_file(
        self,
        file_content: str,
        token_limit: int,
        model: str = "default"
    ) -> List[str]:
        """
        Split a large file into multiple chunks.
        
        Args:
            file_content: File content with header
            token_limit: Maximum tokens per chunk
            model: Model name for token counting
            
        Returns:
            List of file chunks
        """
        # Extract file header
        header_match = re.match(r'(\n\n### File: [^\n]+ ###\n)', file_content)
        if not header_match:
            # If no header found, treat the whole content as the body
            header = ""
            body = file_content
        else:
            header = header_match.group(1)
            body = file_content[len(header):]
        
        # Split by lines to preserve code structure
        lines = body.split('\n')
        
        chunks = []
        current_lines = []
        current_tokens = self.token_counter.count_tokens(header, model) if header else 0
        
        for i, line in enumerate(lines):
            line_tokens = self.token_counter.count_tokens(line + '\n', model)
            
            # If this single line exceeds token limit (rare), we have to truncate it
            if line_tokens > token_limit:
                # For extremely long lines, just add them as their own chunk
                if current_lines:
                    chunks.append(header + '\n'.join(current_lines))
                    current_lines = []
                
                truncated_line = self.token_counter.truncate_to_token_limit(
                    line, token_limit - self.token_counter.count_tokens(header, model), model
                )
                chunks.append(header + truncated_line)
                current_tokens = 0
                continue
            
            # If adding this line would exceed the limit, start a new chunk
            if current_tokens + line_tokens > token_limit and current_lines:
                chunks.append(header + '\n'.join(current_lines))
                current_lines = []
                current_tokens = self.token_counter.count_tokens(header, model) if header else 0
            
            # Add this line to the current chunk
            current_lines.append(line)
            current_tokens += line_tokens
        
        # Add the last chunk if it has content
        if current_lines:
            chunks.append(header + '\n'.join(current_lines))
        
        # Add part number to headers for clarity
        for i in range(len(chunks)):
            if header:
                # Extract the original filename
                filename_match = re.search(r'### File: ([^\n]+) ###', chunks[i])
                if filename_match:
                    original_filename = filename_match.group(1)
                    new_header = f"\n\n### File: {original_filename} (Part {i+1}/{len(chunks)}) ###\n"
                    chunks[i] = chunks[i].replace(header, new_header)
        
        return chunks
    
    def _write_chunks_to_files(
        self,
        chunks: List[str],
        project_name: str
    ) -> List[Path]:
        """
        Write code chunks to files.
        
        Args:
            chunks: List of code chunks
            project_name: Name of the project for filenames
            
        Returns:
            List of paths to the generated files
        """
        output_files = []
        
        # Sanitize project name for filenames
        safe_project_name = re.sub(r'[^\w\-\.]', '_', project_name)
        
        for i, chunk in enumerate(chunks):
            # Create filename with padding for correct sorting
            filename = f"{safe_project_name}_part_{i+1:03d}.txt"
            file_path = self.output_dir / filename
            
            # Write chunk to file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(chunk)
            
            output_files.append(file_path)
            logger.info(f"Wrote chunk {i+1}/{len(chunks)} to {file_path}")
        
        return output_files
    
    def _write_metadata(
        self,
        source_path: Union[str, Path, List[Union[str, Path]]],
        output_files: List[Path],
        total_tokens: int
    ) -> None:
        """
        Write metadata file with information about the split.
        
        Args:
            source_path: Source directory or files
            output_files: List of generated files
            total_tokens: Total tokens in the concentrated code
        """
        metadata = {
            "source": str(source_path) if not isinstance(source_path, list) else [str(p) for p in source_path],
            "output_files": [str(f) for f in output_files],
            "total_tokens": total_tokens,
            "files_count": len(output_files),
            "timestamp": str(Path(self.output_dir).stat().st_mtime)
        }
        
        metadata_path = self.output_dir / "split_metadata.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Wrote metadata to {metadata_path}") 