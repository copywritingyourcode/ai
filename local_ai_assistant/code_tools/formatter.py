"""
Code formatter module for standardizing and cleaning up code.

This module provides functions to automatically format code according
to style guidelines and best practices.
"""

import logging
import subprocess
import os
import tempfile
import sys
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
import yaml
import re

# Logger for this module
logger = logging.getLogger(__name__)


class CodeFormatter:
    """
    Formats code according to style guidelines.
    
    This class provides methods to automatically clean up and standardize
    code formatting using tools like Black and isort for Python, or
    Prettier for JavaScript and related languages.
    """
    
    def __init__(self, config_path: Union[str, Path]):
        """
        Initialize the code formatter.
        
        Args:
            config_path: Path to the configuration file
        """
        self.config_path = Path(config_path)
        
        # Load configuration
        with open(self.config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # Extract code formatter settings
        formatter_config = self.config['code_tools'].get('formatter', {})
        
        # Default formatting settings
        self.python_line_length = formatter_config.get('python_line_length', 88)
        self.enable_formatters = formatter_config.get('enable_formatters', True)
        
        # External formatters settings
        self.external_formatters = formatter_config.get('external_formatters', {})
        
        logger.info(f"Code formatter initialized, enabled: {self.enable_formatters}")
    
    def format_code(
        self, 
        code: str,
        language: str,
        style: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Format code according to specified language and style.
        
        Args:
            code: Code to format
            language: Programming language of the code
            style: Style guide to follow (e.g., 'pep8', 'google')
            
        Returns:
            Dictionary with results:
                - success: Whether formatting completed successfully
                - formatted_code: Formatted code (if successful)
                - error: Error message (if any)
        """
        if not self.enable_formatters:
            return {
                'success': True,
                'formatted_code': code,
                'error': ''
            }
        
        # Normalize language name
        language = language.lower()
        
        # Select formatter based on language
        if language in ('python', 'py'):
            return self._format_python(code, style)
        elif language in ('javascript', 'js', 'typescript', 'ts', 'jsx', 'tsx'):
            return self._format_js_ts(code, language)
        elif language in ('html', 'css', 'json', 'yaml', 'yml', 'markdown', 'md'):
            return self._format_web(code, language)
        else:
            # Basic formatting for other languages
            return self._basic_format(code, language)
    
    def _format_python(
        self, 
        code: str, 
        style: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Format Python code using Black and isort.
        
        Args:
            code: Python code to format
            style: Style guide to follow
            
        Returns:
            Dictionary with formatting results
        """
        # Use external formatters if available and enabled
        if self._check_external_formatter('black') and self._check_external_formatter('isort'):
            return self._format_python_external(code, style)
        
        # Fallback to basic Python formatting
        return self._basic_python_format(code)
    
    def _format_python_external(
        self, 
        code: str, 
        style: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Format Python code using external tools (Black and isort).
        
        Args:
            code: Python code to format
            style: Style guide to follow
            
        Returns:
            Dictionary with formatting results
        """
        try:
            # Create a temporary file
            with tempfile.NamedTemporaryFile(suffix=".py", mode='w+', delete=False) as temp_file:
                temp_path = temp_file.name
                temp_file.write(code)
            
            # Format with Black
            black_args = ['black', '-q', f'--line-length={self.python_line_length}']
            
            # Add style options if provided
            if style == 'google':
                black_args.append('--preview')
            
            black_args.append(temp_path)
            
            black_result = subprocess.run(
                black_args,
                capture_output=True,
                text=True
            )
            
            if black_result.returncode != 0:
                logger.warning(f"Black formatting failed: {black_result.stderr}")
            
            # Format with isort
            isort_args = ['isort', '-q', f'--profile=black', f'--line-length={self.python_line_length}', temp_path]
            
            isort_result = subprocess.run(
                isort_args,
                capture_output=True,
                text=True
            )
            
            if isort_result.returncode != 0:
                logger.warning(f"isort formatting failed: {isort_result.stderr}")
            
            # Read the formatted code
            with open(temp_path, 'r') as f:
                formatted_code = f.read()
            
            # Clean up
            os.unlink(temp_path)
            
            return {
                'success': True,
                'formatted_code': formatted_code,
                'error': ''
            }
            
        except Exception as e:
            logger.error(f"Error formatting Python code: {str(e)}")
            return {
                'success': False,
                'formatted_code': code,
                'error': f"Error formatting Python code: {str(e)}"
            }
    
    def _basic_python_format(self, code: str) -> Dict[str, Any]:
        """
        Apply basic Python formatting without external tools.
        
        Args:
            code: Python code to format
            
        Returns:
            Dictionary with formatting results
        """
        try:
            lines = code.split('\n')
            result = []
            
            # Simple indentation fixing
            indent_level = 0
            for line in lines:
                stripped = line.strip()
                
                # Skip blank lines
                if not stripped:
                    result.append('')
                    continue
                
                # Check for indent decreasing tokens
                if stripped.startswith((')', ']', '}')):
                    indent_level = max(0, indent_level - 1)
                
                # Apply indentation
                if stripped:
                    result.append('    ' * indent_level + stripped)
                else:
                    result.append('')
                
                # Check for indent increasing tokens
                if stripped.endswith((':', '(', '[', '{')):
                    indent_level += 1
                
                # Balance closing brackets
                if stripped.endswith(('}', ']', ')')):
                    indent_level = max(0, indent_level - 1)
            
            formatted_code = '\n'.join(result)
            
            return {
                'success': True,
                'formatted_code': formatted_code,
                'error': ''
            }
            
        except Exception as e:
            logger.error(f"Error in basic Python formatting: {str(e)}")
            return {
                'success': False,
                'formatted_code': code,
                'error': f"Error in basic Python formatting: {str(e)}"
            }
    
    def _format_js_ts(
        self, 
        code: str, 
        language: str
    ) -> Dict[str, Any]:
        """
        Format JavaScript/TypeScript code using Prettier.
        
        Args:
            code: JS/TS code to format
            language: Specific language ('js', 'ts', etc.)
            
        Returns:
            Dictionary with formatting results
        """
        # Use external formatter if available
        if self._check_external_formatter('prettier'):
            return self._format_with_prettier(code, language)
        
        # Fallback to basic JS/TS formatting
        return self._basic_format(code, language)
    
    def _format_with_prettier(
        self, 
        code: str, 
        language: str
    ) -> Dict[str, Any]:
        """
        Format code using Prettier.
        
        Args:
            code: Code to format
            language: Language identifier
            
        Returns:
            Dictionary with formatting results
        """
        try:
            # Map language to file extension
            extension_map = {
                'javascript': '.js',
                'js': '.js',
                'typescript': '.ts',
                'ts': '.ts',
                'jsx': '.jsx',
                'tsx': '.tsx',
                'html': '.html',
                'css': '.css',
                'json': '.json',
                'yaml': '.yml',
                'yml': '.yml',
                'markdown': '.md',
                'md': '.md'
            }
            
            ext = extension_map.get(language, f'.{language}')
            
            # Create a temporary file
            with tempfile.NamedTemporaryFile(suffix=ext, mode='w+', delete=False) as temp_file:
                temp_path = temp_file.name
                temp_file.write(code)
            
            # Format with Prettier
            prettier_args = ['prettier', '--write', temp_path]
            
            prettier_result = subprocess.run(
                prettier_args,
                capture_output=True,
                text=True
            )
            
            if prettier_result.returncode != 0:
                logger.warning(f"Prettier formatting failed: {prettier_result.stderr}")
                return {
                    'success': False,
                    'formatted_code': code,
                    'error': f"Prettier error: {prettier_result.stderr}"
                }
            
            # Read the formatted code
            with open(temp_path, 'r') as f:
                formatted_code = f.read()
            
            # Clean up
            os.unlink(temp_path)
            
            return {
                'success': True,
                'formatted_code': formatted_code,
                'error': ''
            }
            
        except Exception as e:
            logger.error(f"Error formatting with Prettier: {str(e)}")
            return {
                'success': False,
                'formatted_code': code,
                'error': f"Error formatting with Prettier: {str(e)}"
            }
    
    def _format_web(
        self, 
        code: str, 
        language: str
    ) -> Dict[str, Any]:
        """
        Format web languages (HTML, CSS, etc.) using Prettier.
        
        Args:
            code: Code to format
            language: Web language identifier
            
        Returns:
            Dictionary with formatting results
        """
        return self._format_js_ts(code, language)
    
    def _basic_format(
        self, 
        code: str, 
        language: str
    ) -> Dict[str, Any]:
        """
        Apply basic formatting for any language.
        
        Args:
            code: Code to format
            language: Language identifier
            
        Returns:
            Dictionary with formatting results
        """
        try:
            lines = code.split('\n')
            result = []
            
            # Simple indentation fixing
            indent_level = 0
            for line in lines:
                stripped = line.strip()
                
                # Skip blank lines
                if not stripped:
                    result.append('')
                    continue
                
                # Check for indent decreasing tokens
                if stripped.startswith((')', ']', '}')):
                    indent_level = max(0, indent_level - 1)
                
                # Apply indentation
                if stripped:
                    result.append('  ' * indent_level + stripped)
                else:
                    result.append('')
                
                # Check for indent increasing tokens
                if stripped.endswith(('{', '[', '(')):
                    indent_level += 1
                
                # Balance closing brackets
                if stripped.endswith(('}', ']', ')')):
                    indent_level = max(0, indent_level - 1)
            
            formatted_code = '\n'.join(result)
            
            return {
                'success': True,
                'formatted_code': formatted_code,
                'error': ''
            }
            
        except Exception as e:
            logger.error(f"Error in basic formatting: {str(e)}")
            return {
                'success': False,
                'formatted_code': code,
                'error': f"Error in basic formatting: {str(e)}"
            }
    
    def _check_external_formatter(self, formatter_name: str) -> bool:
        """
        Check if an external formatter is available.
        
        Args:
            formatter_name: Name of the formatter
            
        Returns:
            True if the formatter is available, False otherwise
        """
        if formatter_name not in self.external_formatters:
            return False
        
        formatter_config = self.external_formatters[formatter_name]
        if not formatter_config.get('enabled', True):
            return False
        
        # Check if the formatter is installed
        try:
            subprocess.run(
                [formatter_name, '--version'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            return True
        except (subprocess.SubprocessError, FileNotFoundError):
            logger.warning(f"External formatter {formatter_name} not found")
            return False
    
    def format_file(
        self, 
        file_path: Union[str, Path],
        style: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Format a file according to its language.
        
        Args:
            file_path: Path to the file to format
            style: Style guide to follow
            
        Returns:
            Dictionary with formatting results
        """
        file_path = Path(file_path)
        
        # Check if file exists
        if not file_path.exists():
            return {
                'success': False,
                'error': f"File not found: {file_path}"
            }
        
        try:
            # Determine language from file extension
            ext = file_path.suffix.lower().lstrip('.')
            language_map = {
                'py': 'python',
                'js': 'javascript',
                'ts': 'typescript',
                'jsx': 'jsx',
                'tsx': 'tsx',
                'html': 'html',
                'css': 'css',
                'json': 'json',
                'yaml': 'yaml',
                'yml': 'yaml',
                'md': 'markdown'
            }
            
            language = language_map.get(ext, ext)
            
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
            
            # Format the code
            result = self.format_code(code, language, style)
            
            # Write back to file if successful
            if result['success']:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(result['formatted_code'])
            
            return result
            
        except Exception as e:
            logger.error(f"Error formatting file {file_path}: {str(e)}")
            return {
                'success': False,
                'error': f"Error formatting file: {str(e)}"
            }
    
    def format_directory(
        self, 
        directory_path: Union[str, Path],
        recursive: bool = True,
        file_extensions: Optional[List[str]] = None,
        style: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Format all files in a directory.
        
        Args:
            directory_path: Path to the directory
            recursive: Whether to recursively format subdirectories
            file_extensions: List of file extensions to format
            style: Style guide to follow
            
        Returns:
            Dictionary with formatting results
        """
        directory_path = Path(directory_path)
        
        # Check if directory exists
        if not directory_path.exists() or not directory_path.is_dir():
            return {
                'success': False,
                'error': f"Directory not found: {directory_path}"
            }
        
        # Default file extensions to format
        if file_extensions is None:
            file_extensions = ['py', 'js', 'ts', 'jsx', 'tsx', 'html', 'css', 'json', 'yaml', 'yml', 'md']
        
        # Normalize extensions
        file_extensions = [ext.lower().lstrip('.') for ext in file_extensions]
        
        results = {
            'success': True,
            'formatted_files': [],
            'failed_files': [],
            'error': ''
        }
        
        try:
            # Find files to format
            files_to_format = []
            
            if recursive:
                for root, _, files in os.walk(directory_path):
                    for file in files:
                        file_path = Path(root) / file
                        if file_path.suffix.lower().lstrip('.') in file_extensions:
                            files_to_format.append(file_path)
            else:
                for file in os.listdir(directory_path):
                    file_path = directory_path / file
                    if file_path.is_file() and file_path.suffix.lower().lstrip('.') in file_extensions:
                        files_to_format.append(file_path)
            
            # Format each file
            for file_path in files_to_format:
                result = self.format_file(file_path, style)
                
                if result['success']:
                    results['formatted_files'].append(str(file_path))
                else:
                    results['failed_files'].append({
                        'file': str(file_path),
                        'error': result['error']
                    })
            
            # Update overall success status
            if results['failed_files']:
                results['success'] = False
                results['error'] = f"Failed to format {len(results['failed_files'])} files"
            
            return results
            
        except Exception as e:
            logger.error(f"Error formatting directory {directory_path}: {str(e)}")
            return {
                'success': False,
                'formatted_files': results['formatted_files'],
                'failed_files': results['failed_files'],
                'error': f"Error formatting directory: {str(e)}"
            } 