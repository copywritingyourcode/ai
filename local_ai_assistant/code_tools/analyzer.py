"""
Code analyzer module for static analysis and code quality checking.

This module provides functionality to analyze code for potential issues,
evaluate code quality, and suggest improvements.
"""

import logging
import subprocess
import os
import tempfile
import json
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Set, Tuple
import yaml
import re
import ast
import sys

# Logger for this module
logger = logging.getLogger(__name__)


class CodeAnalyzer:
    """
    Analyzes code for quality issues and potential bugs.
    
    This class provides methods to perform static analysis on code,
    identify common issues, and suggest improvements.
    """
    
    def __init__(self, config_path: Union[str, Path]):
        """
        Initialize the code analyzer.
        
        Args:
            config_path: Path to the configuration file
        """
        self.config_path = Path(config_path)
        
        # Load configuration
        with open(self.config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # Extract code analyzer settings
        analyzer_config = self.config['code_tools'].get('analyzer', {})
        
        # External analyzers settings
        self.external_analyzers = analyzer_config.get('external_analyzers', {})
        
        # Enable analyzers by default
        self.enable_analyzers = analyzer_config.get('enable_analyzers', True)
        
        logger.info(f"Code analyzer initialized, enabled: {self.enable_analyzers}")
    
    def analyze_code(
        self, 
        code: str,
        language: str,
        filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze code for issues and quality.
        
        Args:
            code: Code to analyze
            language: Programming language of the code
            filename: Optional filename for context
            
        Returns:
            Dictionary with analysis results:
                - success: Whether analysis completed successfully
                - issues: List of detected issues
                - metrics: Code quality metrics
                - suggestions: Suggested improvements
                - error: Error message (if any)
        """
        if not self.enable_analyzers:
            return {
                'success': True,
                'issues': [],
                'metrics': {},
                'suggestions': [],
                'error': ''
            }
        
        # Normalize language name
        language = language.lower()
        
        # Select analyzer based on language
        if language in ('python', 'py'):
            return self._analyze_python(code, filename)
        elif language in ('javascript', 'js'):
            return self._analyze_javascript(code, filename)
        elif language in ('typescript', 'ts'):
            return self._analyze_typescript(code, filename)
        else:
            # Basic analysis for other languages
            return self._basic_analysis(code, language)
    
    def _analyze_python(
        self,
        code: str,
        filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze Python code using static analysis tools.
        
        Args:
            code: Python code to analyze
            filename: Optional filename for context
            
        Returns:
            Dictionary with analysis results
        """
        results = {
            'success': True,
            'issues': [],
            'metrics': {},
            'suggestions': [],
            'error': ''
        }
        
        # Use external analyzers if available
        external_results = self._run_external_python_analyzers(code, filename)
        if external_results['success']:
            # Merge external analysis with results
            results['issues'].extend(external_results['issues'])
            results['metrics'].update(external_results['metrics'])
            results['suggestions'].extend(external_results['suggestions'])
        
        # Always run basic Python analysis
        basic_results = self._basic_python_analysis(code)
        if basic_results['success']:
            # Merge basic analysis with results
            results['issues'].extend(basic_results['issues'])
            results['metrics'].update(basic_results['metrics'])
            results['suggestions'].extend(basic_results['suggestions'])
        else:
            # If basic analysis failed but external succeeded, still consider overall success
            if not external_results['success']:
                results['success'] = False
                results['error'] = f"Analysis failed: {basic_results['error']}"
        
        return results
    
    def _run_external_python_analyzers(
        self,
        code: str,
        filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Run external Python analyzers like pylint, flake8, etc.
        
        Args:
            code: Python code to analyze
            filename: Optional filename for context
            
        Returns:
            Dictionary with analysis results
        """
        results = {
            'success': True,
            'issues': [],
            'metrics': {},
            'suggestions': [],
            'error': ''
        }
        
        # Create a temporary file for analysis
        temp_file = None
        try:
            with tempfile.NamedTemporaryFile(suffix='.py', mode='w+', delete=False) as f:
                temp_file = f.name
                f.write(code)
            
            # Run pylint if available
            if self._check_external_analyzer('pylint'):
                pylint_results = self._run_pylint(temp_file)
                if pylint_results['success']:
                    results['issues'].extend(pylint_results['issues'])
                    results['metrics'].update(pylint_results['metrics'])
                    results['suggestions'].extend(pylint_results['suggestions'])
            
            # Run flake8 if available
            if self._check_external_analyzer('flake8'):
                flake8_results = self._run_flake8(temp_file)
                if flake8_results['success']:
                    results['issues'].extend(flake8_results['issues'])
            
            # Run bandit if available (security checks)
            if self._check_external_analyzer('bandit'):
                bandit_results = self._run_bandit(temp_file)
                if bandit_results['success']:
                    results['issues'].extend(bandit_results['issues'])
            
            # Run mypy if available (type checking)
            if self._check_external_analyzer('mypy'):
                mypy_results = self._run_mypy(temp_file)
                if mypy_results['success']:
                    results['issues'].extend(mypy_results['issues'])
            
        except Exception as e:
            logger.error(f"Error during external Python analysis: {str(e)}")
            results['success'] = False
            results['error'] = f"Error during external Python analysis: {str(e)}"
        finally:
            # Clean up temporary file
            if temp_file and os.path.exists(temp_file):
                os.unlink(temp_file)
        
        return results
    
    def _run_pylint(self, file_path: str) -> Dict[str, Any]:
        """
        Run pylint on a Python file.
        
        Args:
            file_path: Path to the Python file
            
        Returns:
            Dictionary with pylint results
        """
        try:
            # Run pylint with JSON reporter
            result = subprocess.run(
                ['pylint', '--output-format=json', file_path],
                capture_output=True,
                text=True
            )
            
            issues = []
            metrics = {'score': 10.0}  # Default score (perfect)
            suggestions = []
            
            # Parse pylint output
            if result.stdout:
                try:
                    pylint_json = json.loads(result.stdout)
                    
                    # Extract issues
                    for item in pylint_json:
                        issue = {
                            'line': item.get('line', 0),
                            'column': item.get('column', 0),
                            'message': item.get('message', ''),
                            'message-id': item.get('message-id', ''),
                            'symbol': item.get('symbol', ''),
                            'severity': item.get('type', 'warning')
                        }
                        issues.append(issue)
                        
                        # Add suggestion for fixable issues
                        if item.get('symbol') in ['unused-import', 'trailing-whitespace', 'missing-docstring']:
                            suggestions.append({
                                'line': item.get('line', 0),
                                'message': f"Fix: {item.get('message', '')}",
                                'fix': self._get_pylint_fix(item)
                            })
                    
                except json.JSONDecodeError:
                    logger.warning("Failed to parse pylint JSON output")
            
            # Extract score from stderr (it's not in the JSON output)
            if result.stderr:
                score_match = re.search(r'Your code has been rated at (-?\d+\.\d+)/10', result.stderr)
                if score_match:
                    metrics['score'] = float(score_match.group(1))
            
            return {
                'success': True,
                'issues': issues,
                'metrics': metrics,
                'suggestions': suggestions
            }
            
        except Exception as e:
            logger.error(f"Error running pylint: {str(e)}")
            return {
                'success': False,
                'issues': [],
                'metrics': {},
                'suggestions': [],
                'error': f"Error running pylint: {str(e)}"
            }
    
    def _get_pylint_fix(self, pylint_issue: Dict[str, Any]) -> str:
        """
        Generate a fix suggestion for a pylint issue.
        
        Args:
            pylint_issue: Pylint issue dictionary
            
        Returns:
            Suggested fix as a string
        """
        symbol = pylint_issue.get('symbol', '')
        
        if symbol == 'unused-import':
            return "Remove the unused import"
        elif symbol == 'trailing-whitespace':
            return "Remove trailing whitespace"
        elif symbol == 'missing-docstring':
            return "Add a docstring describing the purpose of this element"
        else:
            return "Review and address the issue according to pylint guidelines"
    
    def _run_flake8(self, file_path: str) -> Dict[str, Any]:
        """
        Run flake8 on a Python file.
        
        Args:
            file_path: Path to the Python file
            
        Returns:
            Dictionary with flake8 results
        """
        try:
            # Run flake8
            result = subprocess.run(
                ['flake8', file_path],
                capture_output=True,
                text=True
            )
            
            issues = []
            
            # Parse flake8 output
            # Format: filename:line:column: error_code error_message
            if result.stdout:
                for line in result.stdout.splitlines():
                    match = re.match(r'.*:(\d+):(\d+): (\w+) (.*)', line)
                    if match:
                        line_num, col, code, message = match.groups()
                        issues.append({
                            'line': int(line_num),
                            'column': int(col),
                            'code': code,
                            'message': message,
                            'severity': 'convention' if code.startswith('E') else 'warning'
                        })
            
            return {
                'success': True,
                'issues': issues
            }
            
        except Exception as e:
            logger.error(f"Error running flake8: {str(e)}")
            return {
                'success': False,
                'issues': [],
                'error': f"Error running flake8: {str(e)}"
            }
    
    def _run_bandit(self, file_path: str) -> Dict[str, Any]:
        """
        Run bandit on a Python file for security checks.
        
        Args:
            file_path: Path to the Python file
            
        Returns:
            Dictionary with bandit results
        """
        try:
            # Run bandit with JSON formatter
            result = subprocess.run(
                ['bandit', '-f', 'json', file_path],
                capture_output=True,
                text=True
            )
            
            issues = []
            
            # Parse bandit output
            if result.stdout:
                try:
                    bandit_data = json.loads(result.stdout)
                    results = bandit_data.get('results', [])
                    
                    for item in results:
                        issues.append({
                            'line': item.get('line_number', 0),
                            'message': item.get('issue_text', ''),
                            'severity': item.get('issue_severity', 'medium').lower(),
                            'confidence': item.get('issue_confidence', ''),
                            'code': item.get('test_id', '')
                        })
                        
                except json.JSONDecodeError:
                    logger.warning("Failed to parse bandit JSON output")
            
            return {
                'success': True,
                'issues': issues
            }
            
        except Exception as e:
            logger.error(f"Error running bandit: {str(e)}")
            return {
                'success': False,
                'issues': [],
                'error': f"Error running bandit: {str(e)}"
            }
    
    def _run_mypy(self, file_path: str) -> Dict[str, Any]:
        """
        Run mypy on a Python file for type checking.
        
        Args:
            file_path: Path to the Python file
            
        Returns:
            Dictionary with mypy results
        """
        try:
            # Run mypy
            result = subprocess.run(
                ['mypy', file_path],
                capture_output=True,
                text=True
            )
            
            issues = []
            
            # Parse mypy output
            # Format: file:line: error: message
            if result.stdout:
                for line in result.stdout.splitlines():
                    match = re.match(r'.*:(\d+): (\w+): (.*)', line)
                    if match:
                        line_num, severity, message = match.groups()
                        issues.append({
                            'line': int(line_num),
                            'message': message,
                            'severity': severity.lower()
                        })
            
            return {
                'success': True,
                'issues': issues
            }
            
        except Exception as e:
            logger.error(f"Error running mypy: {str(e)}")
            return {
                'success': False,
                'issues': [],
                'error': f"Error running mypy: {str(e)}"
            }
    
    def _basic_python_analysis(self, code: str) -> Dict[str, Any]:
        """
        Perform basic Python code analysis using the ast module.
        
        Args:
            code: Python code to analyze
            
        Returns:
            Dictionary with analysis results
        """
        results = {
            'success': True,
            'issues': [],
            'metrics': {},
            'suggestions': [],
            'error': ''
        }
        
        try:
            # Parse the code to an AST
            tree = ast.parse(code)
            
            # Collect metrics
            metrics = {
                'line_count': len(code.splitlines()),
                'function_count': 0,
                'class_count': 0,
                'import_count': 0,
                'complexity': {}
            }
            
            # Track used and imported names
            imported_names = set()
            used_names = set()
            
            # Visitor for basic analysis
            class BasicVisitor(ast.NodeVisitor):
                def visit_FunctionDef(self, node):
                    metrics['function_count'] += 1
                    
                    # Calculate cyclomatic complexity
                    complexity = self._calculate_complexity(node)
                    metrics['complexity'][node.name] = complexity
                    
                    # Check for missing docstring
                    if not ast.get_docstring(node):
                        results['issues'].append({
                            'line': node.lineno,
                            'message': f"Function '{node.name}' is missing a docstring",
                            'severity': 'convention'
                        })
                    
                    self.generic_visit(node)
                
                def visit_ClassDef(self, node):
                    metrics['class_count'] += 1
                    
                    # Check for missing docstring
                    if not ast.get_docstring(node):
                        results['issues'].append({
                            'line': node.lineno,
                            'message': f"Class '{node.name}' is missing a docstring",
                            'severity': 'convention'
                        })
                    
                    self.generic_visit(node)
                
                def visit_Import(self, node):
                    metrics['import_count'] += len(node.names)
                    for alias in node.names:
                        imported_names.add(alias.name)
                    self.generic_visit(node)
                
                def visit_ImportFrom(self, node):
                    metrics['import_count'] += len(node.names)
                    for alias in node.names:
                        if node.module:
                            imported_names.add(f"{node.module}.{alias.name}")
                        else:
                            imported_names.add(alias.name)
                    self.generic_visit(node)
                
                def visit_Name(self, node):
                    if isinstance(node.ctx, ast.Load):
                        used_names.add(node.id)
                    self.generic_visit(node)
                
                def _calculate_complexity(self, node):
                    """Calculate cyclomatic complexity."""
                    complexity = 1  # Base complexity
                    
                    class ComplexityVisitor(ast.NodeVisitor):
                        def __init__(self):
                            self.complexity = 0
                        
                        def visit_If(self, node):
                            self.complexity += 1
                            self.generic_visit(node)
                        
                        def visit_For(self, node):
                            self.complexity += 1
                            self.generic_visit(node)
                        
                        def visit_While(self, node):
                            self.complexity += 1
                            self.generic_visit(node)
                        
                        def visit_Try(self, node):
                            self.complexity += len(node.handlers)
                            self.generic_visit(node)
                        
                        def visit_BoolOp(self, node):
                            if isinstance(node.op, ast.And) or isinstance(node.op, ast.Or):
                                self.complexity += len(node.values) - 1
                            self.generic_visit(node)
                    
                    visitor = ComplexityVisitor()
                    visitor.visit(node)
                    
                    return complexity + visitor.complexity
            
            # Run the visitor
            visitor = BasicVisitor()
            visitor.visit(tree)
            
            # Find unused imports
            for name in imported_names:
                base_name = name.split('.')[0]
                if base_name not in used_names and name not in used_names:
                    # Try to find the import statement for this name
                    for node in ast.walk(tree):
                        if isinstance(node, (ast.Import, ast.ImportFrom)):
                            for alias in node.names:
                                if alias.name == name or alias.name == base_name:
                                    results['issues'].append({
                                        'line': node.lineno,
                                        'message': f"Unused import: {name}",
                                        'severity': 'warning'
                                    })
                                    
                                    results['suggestions'].append({
                                        'line': node.lineno,
                                        'message': f"Remove unused import: {name}",
                                        'fix': f"Remove the import for '{name}'"
                                    })
            
            # Check for high complexity functions
            for func_name, complexity in metrics['complexity'].items():
                if complexity > 10:
                    # Find the function node
                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef) and node.name == func_name:
                            results['issues'].append({
                                'line': node.lineno,
                                'message': f"Function '{func_name}' has high cyclomatic complexity ({complexity})",
                                'severity': 'warning'
                            })
                            
                            results['suggestions'].append({
                                'line': node.lineno,
                                'message': f"Refactor function '{func_name}' to reduce complexity",
                                'fix': "Consider breaking this function into smaller, more focused functions"
                            })
            
            results['metrics'] = metrics
            
            return results
            
        except SyntaxError as e:
            # Handle syntax errors
            results['success'] = False
            results['error'] = f"Syntax error: {str(e)}"
            
            # Extract line number and message
            if hasattr(e, 'lineno') and hasattr(e, 'msg'):
                results['issues'].append({
                    'line': e.lineno,
                    'message': f"Syntax error: {e.msg}",
                    'severity': 'error'
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Error in basic Python analysis: {str(e)}")
            results['success'] = False
            results['error'] = f"Error in basic Python analysis: {str(e)}"
            return results
    
    def _analyze_javascript(
        self,
        code: str,
        filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze JavaScript code using ESLint.
        
        Args:
            code: JavaScript code to analyze
            filename: Optional filename for context
            
        Returns:
            Dictionary with analysis results
        """
        # Use ESLint if available
        if self._check_external_analyzer('eslint'):
            return self._run_eslint(code, filename, 'javascript')
        
        # Basic analysis as fallback
        return self._basic_analysis(code, 'javascript')
    
    def _analyze_typescript(
        self,
        code: str,
        filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze TypeScript code using ESLint with TypeScript support.
        
        Args:
            code: TypeScript code to analyze
            filename: Optional filename for context
            
        Returns:
            Dictionary with analysis results
        """
        # Use ESLint if available
        if self._check_external_analyzer('eslint'):
            return self._run_eslint(code, filename, 'typescript')
        
        # Basic analysis as fallback
        return self._basic_analysis(code, 'typescript')
    
    def _run_eslint(
        self,
        code: str,
        filename: Optional[str] = None,
        language: str = 'javascript'
    ) -> Dict[str, Any]:
        """
        Run ESLint on JavaScript/TypeScript code.
        
        Args:
            code: Code to analyze
            filename: Optional filename for context
            language: Language identifier ('javascript' or 'typescript')
            
        Returns:
            Dictionary with ESLint results
        """
        try:
            # Create a temporary file for analysis
            suffix = '.ts' if language == 'typescript' else '.js'
            temp_file = None
            
            try:
                with tempfile.NamedTemporaryFile(suffix=suffix, mode='w+', delete=False) as f:
                    temp_file = f.name
                    f.write(code)
                
                # Run ESLint with JSON formatter
                cmd = ['eslint', '--format=json', temp_file]
                
                # If TypeScript, ensure TypeScript config
                if language == 'typescript':
                    cmd.append('--parser-options={"ecmaVersion":2020,"sourceType":"module"}')
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True
                )
                
                issues = []
                suggestions = []
                
                # Parse ESLint output
                if result.stdout:
                    try:
                        eslint_json = json.loads(result.stdout)
                        
                        for file_result in eslint_json:
                            for msg in file_result.get('messages', []):
                                issue = {
                                    'line': msg.get('line', 0),
                                    'column': msg.get('column', 0),
                                    'message': msg.get('message', ''),
                                    'rule_id': msg.get('ruleId', ''),
                                    'severity': 'error' if msg.get('severity') == 2 else 'warning'
                                }
                                issues.append(issue)
                                
                                # Add suggestion if fix is available
                                if 'fix' in msg:
                                    suggestions.append({
                                        'line': msg.get('line', 0),
                                        'message': f"Fix: {msg.get('message', '')}",
                                        'fix': msg.get('fix', {}).get('text', '')
                                    })
                                
                    except json.JSONDecodeError:
                        logger.warning("Failed to parse ESLint JSON output")
                
                return {
                    'success': True,
                    'issues': issues,
                    'metrics': {},
                    'suggestions': suggestions
                }
                
            finally:
                # Clean up temporary file
                if temp_file and os.path.exists(temp_file):
                    os.unlink(temp_file)
                    
        except Exception as e:
            logger.error(f"Error running ESLint: {str(e)}")
            return {
                'success': False,
                'issues': [],
                'metrics': {},
                'suggestions': [],
                'error': f"Error running ESLint: {str(e)}"
            }
    
    def _basic_analysis(
        self,
        code: str,
        language: str
    ) -> Dict[str, Any]:
        """
        Perform basic code analysis for any language.
        
        Args:
            code: Code to analyze
            language: Language identifier
            
        Returns:
            Dictionary with analysis results
        """
        results = {
            'success': True,
            'issues': [],
            'metrics': {},
            'suggestions': [],
            'error': ''
        }
        
        try:
            # Calculate basic metrics
            lines = code.splitlines()
            results['metrics'] = {
                'line_count': len(lines),
                'character_count': len(code),
                'average_line_length': len(code) / max(1, len(lines))
            }
            
            # Check for very long lines
            for i, line in enumerate(lines):
                if len(line) > 100:
                    results['issues'].append({
                        'line': i + 1,
                        'message': f"Line is too long ({len(line)} characters)",
                        'severity': 'convention'
                    })
            
            # Check for trailing whitespace
            for i, line in enumerate(lines):
                if line and line[-1].isspace():
                    results['issues'].append({
                        'line': i + 1,
                        'message': "Line has trailing whitespace",
                        'severity': 'convention'
                    })
                    
                    results['suggestions'].append({
                        'line': i + 1,
                        'message': "Remove trailing whitespace",
                        'fix': "Remove whitespace at the end of the line"
                    })
            
            # Check for mixing tabs and spaces
            has_tabs = any('\t' in line for line in lines)
            has_spaces = any('    ' in line for line in lines)
            if has_tabs and has_spaces:
                results['issues'].append({
                    'line': 1,
                    'message': "Mixed use of tabs and spaces for indentation",
                    'severity': 'convention'
                })
                
                results['suggestions'].append({
                    'line': 1,
                    'message': "Standardize on either tabs or spaces for indentation",
                    'fix': "Convert all indentation to spaces (recommended)"
                })
            
            # Check for excessive blank lines
            blank_line_count = sum(1 for line in lines if not line.strip())
            if blank_line_count > len(lines) / 3:
                results['issues'].append({
                    'line': 1,
                    'message': f"Excessive blank lines ({blank_line_count} out of {len(lines)})",
                    'severity': 'convention'
                })
                
                results['suggestions'].append({
                    'line': 1,
                    'message': "Reduce the number of blank lines",
                    'fix': "Remove unnecessary blank lines to improve code readability"
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Error in basic analysis: {str(e)}")
            results['success'] = False
            results['error'] = f"Error in basic analysis: {str(e)}"
            return results
    
    def _check_external_analyzer(self, analyzer_name: str) -> bool:
        """
        Check if an external analyzer is available and enabled.
        
        Args:
            analyzer_name: Name of the analyzer
            
        Returns:
            True if the analyzer is available, False otherwise
        """
        if analyzer_name not in self.external_analyzers:
            return False
        
        analyzer_config = self.external_analyzers[analyzer_name]
        if not analyzer_config.get('enabled', True):
            return False
        
        # Check if the analyzer is installed
        try:
            if analyzer_name == 'eslint':
                cmd = [analyzer_name, '--version']
            else:
                cmd = [analyzer_name, '--version']
                
            subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            return True
        except (subprocess.SubprocessError, FileNotFoundError):
            logger.warning(f"External analyzer {analyzer_name} not found")
            return False
    
    def analyze_file(
        self,
        file_path: Union[str, Path]
    ) -> Dict[str, Any]:
        """
        Analyze a file for code quality issues.
        
        Args:
            file_path: Path to the file to analyze
            
        Returns:
            Dictionary with analysis results
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
            
            # Analyze the code
            return self.analyze_code(code, language, str(file_path))
            
        except Exception as e:
            logger.error(f"Error analyzing file {file_path}: {str(e)}")
            return {
                'success': False,
                'error': f"Error analyzing file: {str(e)}"
            }
    
    def analyze_directory(
        self,
        directory_path: Union[str, Path],
        recursive: bool = True,
        file_extensions: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Analyze all files in a directory.
        
        Args:
            directory_path: Path to the directory
            recursive: Whether to recursively analyze subdirectories
            file_extensions: List of file extensions to analyze
            
        Returns:
            Dictionary with analysis results
        """
        directory_path = Path(directory_path)
        
        # Check if directory exists
        if not directory_path.exists() or not directory_path.is_dir():
            return {
                'success': False,
                'error': f"Directory not found: {directory_path}"
            }
        
        # Default file extensions to analyze
        if file_extensions is None:
            file_extensions = ['py', 'js', 'ts', 'jsx', 'tsx']
        
        # Normalize extensions
        file_extensions = [ext.lower().lstrip('.') for ext in file_extensions]
        
        results = {
            'success': True,
            'analyzed_files': [],
            'issues_by_file': {},
            'metrics_by_file': {},
            'overall_metrics': {
                'total_issues': 0,
                'error_count': 0,
                'warning_count': 0,
                'convention_count': 0,
                'total_lines': 0,
                'average_issues_per_line': 0
            },
            'error': ''
        }
        
        try:
            # Find files to analyze
            files_to_analyze = []
            
            if recursive:
                for root, _, files in os.walk(directory_path):
                    for file in files:
                        file_path = Path(root) / file
                        if file_path.suffix.lower().lstrip('.') in file_extensions:
                            files_to_analyze.append(file_path)
            else:
                for file in os.listdir(directory_path):
                    file_path = directory_path / file
                    if file_path.is_file() and file_path.suffix.lower().lstrip('.') in file_extensions:
                        files_to_analyze.append(file_path)
            
            # Analyze each file
            for file_path in files_to_analyze:
                file_result = self.analyze_file(file_path)
                
                if file_result['success']:
                    file_key = str(file_path.relative_to(directory_path))
                    results['analyzed_files'].append(file_key)
                    
                    # Store issues and metrics
                    results['issues_by_file'][file_key] = file_result.get('issues', [])
                    results['metrics_by_file'][file_key] = file_result.get('metrics', {})
                    
                    # Update overall metrics
                    results['overall_metrics']['total_issues'] += len(file_result.get('issues', []))
                    results['overall_metrics']['total_lines'] += file_result.get('metrics', {}).get('line_count', 0)
                    
                    # Count by severity
                    for issue in file_result.get('issues', []):
                        severity = issue.get('severity', 'warning')
                        if severity == 'error':
                            results['overall_metrics']['error_count'] += 1
                        elif severity == 'warning':
                            results['overall_metrics']['warning_count'] += 1
                        elif severity == 'convention':
                            results['overall_metrics']['convention_count'] += 1
            
            # Calculate average issues per line
            if results['overall_metrics']['total_lines'] > 0:
                results['overall_metrics']['average_issues_per_line'] = (
                    results['overall_metrics']['total_issues'] / results['overall_metrics']['total_lines']
                )
            
            return results
            
        except Exception as e:
            logger.error(f"Error analyzing directory {directory_path}: {str(e)}")
            return {
                'success': False,
                'analyzed_files': results['analyzed_files'],
                'issues_by_file': results['issues_by_file'],
                'metrics_by_file': results['metrics_by_file'],
                'overall_metrics': results['overall_metrics'],
                'error': f"Error analyzing directory: {str(e)}"
            } 