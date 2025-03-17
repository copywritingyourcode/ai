"""
Code sandbox module for safe code execution.

This module provides a secure environment for executing code snippets
to validate their correctness and identify potential issues.
"""

import logging
import os
import sys
import subprocess
import tempfile
import resource
import signal
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple
import yaml
import ast
import time

# Logger for this module
logger = logging.getLogger(__name__)


class CodeSandbox:
    """
    Provides a secure environment for executing code snippets.
    
    This class implements various safety measures to run code securely:
    - Resource limits (CPU time, memory, file size)
    - Process isolation
    - Restricted module access
    - Output capture and error detection
    """
    
    def __init__(self, config_path: Union[str, Path]):
        """
        Initialize the code sandbox.
        
        Args:
            config_path: Path to the configuration file
        """
        self.config_path = Path(config_path)
        
        # Load configuration
        with open(self.config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # Extract debug settings
        debug_config = self.config['debug']
        sandbox_config = debug_config['sandbox']
        
        # Set sandbox parameters
        self.timeout_seconds = sandbox_config['timeout_seconds']
        self.max_memory_mb = sandbox_config['max_memory_mb']
        self.allowed_modules = set(sandbox_config['allowed_modules'])
        
        # Temp directory for code execution
        self.temp_dir = Path(self.config['system']['temp_dir'])
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Code sandbox initialized, timeout: {self.timeout_seconds}s, max memory: {self.max_memory_mb}MB")
    
    def execute_python(self, code: str) -> Dict[str, Any]:
        """
        Execute Python code in a sandbox.
        
        Args:
            code: Python code to execute
            
        Returns:
            Dictionary with execution results
        """
        # Check code for potential issues before execution
        security_check = self._check_python_code_security(code)
        if not security_check['is_safe']:
            logger.warning(f"Code failed security check: {security_check['reason']}")
            return {
                'success': False,
                'error': f"Security check failed: {security_check['reason']}",
                'output': '',
                'execution_time': 0
            }
        
        try:
            # Create a temporary file for the code
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.py',
                dir=self.temp_dir,
                delete=False
            ) as temp_file:
                # Write code to the file
                temp_file.write(code)
                temp_path = temp_file.name
            
            # Prepare command to run the code in a separate process
            cmd = [
                sys.executable,  # Current Python interpreter
                '-c',
                f"""
import sys
import os
import resource
import time
import signal
import json

# Set resource limits
def set_limits():
    # Set CPU time limit (seconds)
    resource.setrlimit(resource.RLIMIT_CPU, ({self.timeout_seconds}, {self.timeout_seconds}))
    
    # Set memory limit (bytes)
    mem_limit = {self.max_memory_mb} * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_AS, (mem_limit, mem_limit))
    
    # Set file size limit (bytes)
    file_limit = 1 * 1024 * 1024  # 1MB
    resource.setrlimit(resource.RLIMIT_FSIZE, (file_limit, file_limit))

# Execute the code with limits
start_time = time.time()
output = ""
error = ""
success = True

try:
    # Set resource limits
    set_limits()
    
    # Redirect stdout and stderr to capture output
    sys.stdout = open('stdout.txt', 'w')
    sys.stderr = open('stderr.txt', 'w')
    
    # Execute the code
    with open('{temp_path}') as f:
        code = compile(f.read(), '{temp_path}', 'exec')
        exec(code, {{}}, {{}})
    
    # Close output files
    sys.stdout.close()
    sys.stderr.close()
    
    # Reopen standard streams
    sys.stdout = sys.__stdout__
    sys.stderr = sys.__stderr__
    
    # Read captured output
    with open('stdout.txt', 'r') as f:
        output = f.read()
    
    with open('stderr.txt', 'r') as f:
        error = f.read()
    
except Exception as e:
    success = False
    if not error:
        error = str(e)

# Prepare result
result = {{
    'success': success,
    'error': error,
    'output': output,
    'execution_time': time.time() - start_time
}}

# Print result as JSON
print(json.dumps(result))
                """
            ]
            
            # Execute the code in a separate process
            start_time = time.time()
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=str(self.temp_dir)
            )
            
            try:
                # Wait for the process to complete with timeout
                stdout, stderr = process.communicate(timeout=self.timeout_seconds + 1)
                execution_time = time.time() - start_time
                
                # Parse result from JSON output
                try:
                    result = json.loads(stdout)
                    result['execution_time'] = execution_time  # Use actual wall time
                    logger.debug(f"Code execution completed in {execution_time:.2f}s")
                except json.JSONDecodeError:
                    # If output is not valid JSON, return raw output
                    result = {
                        'success': process.returncode == 0,
                        'error': stderr,
                        'output': stdout,
                        'execution_time': execution_time
                    }
                
            except subprocess.TimeoutExpired:
                # Kill the process if it times out
                process.kill()
                stdout, stderr = process.communicate()
                
                logger.warning(f"Code execution timed out after {self.timeout_seconds}s")
                result = {
                    'success': False,
                    'error': f"Execution timed out after {self.timeout_seconds} seconds",
                    'output': stdout,
                    'execution_time': self.timeout_seconds
                }
            
            # Clean up temporary file
            try:
                os.unlink(temp_path)
                for file in ['stdout.txt', 'stderr.txt']:
                    if (self.temp_dir / file).exists():
                        (self.temp_dir / file).unlink()
            except Exception as e:
                logger.warning(f"Error cleaning up temp files: {str(e)}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing Python code: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'output': '',
                'execution_time': 0
            }
    
    def _check_python_code_security(self, code: str) -> Dict[str, Any]:
        """
        Check Python code for security issues before execution.
        
        Args:
            code: Python code to check
            
        Returns:
            Dictionary with security check results
        """
        result = {
            'is_safe': True,
            'reason': ''
        }
        
        try:
            # Parse the code
            tree = ast.parse(code)
            
            # Check for imports
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for name in node.names:
                        module_name = name.name.split('.')[0]
                        if module_name not in self.allowed_modules:
                            result['is_safe'] = False
                            result['reason'] = f"Import of non-allowed module: {module_name}"
                            return result
                
                elif isinstance(node, ast.ImportFrom):
                    module_name = node.module.split('.')[0] if node.module else ''
                    if module_name and module_name not in self.allowed_modules:
                        result['is_safe'] = False
                        result['reason'] = f"Import of non-allowed module: {module_name}"
                        return result
                
                # Check for potential dangerous operations
                elif isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        func_name = node.func.id
                        if func_name in ['eval', 'exec', 'compile']:
                            result['is_safe'] = False
                            result['reason'] = f"Use of potentially dangerous function: {func_name}"
                            return result
                    
                    elif isinstance(node.func, ast.Attribute):
                        if isinstance(node.func.value, ast.Name):
                            if node.func.value.id == 'os' and node.func.attr in ['system', 'popen', 'spawn']:
                                result['is_safe'] = False
                                result['reason'] = f"Use of potentially dangerous function: os.{node.func.attr}"
                                return result
                            
                            elif node.func.value.id == 'subprocess':
                                result['is_safe'] = False
                                result['reason'] = f"Use of subprocess module"
                                return result
            
            return result
            
        except SyntaxError as e:
            # Syntax errors are not security issues
            return result
            
        except Exception as e:
            logger.error(f"Error checking code security: {str(e)}")
            # If we can't check, assume it's not safe
            result['is_safe'] = False
            result['reason'] = f"Security check failed: {str(e)}"
            return result
    
    def execute_javascript(self, code: str) -> Dict[str, Any]:
        """
        Execute JavaScript code in a sandbox.
        
        Args:
            code: JavaScript code to execute
            
        Returns:
            Dictionary with execution results
        """
        try:
            # Create a temporary file for the code
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.js',
                dir=self.temp_dir,
                delete=False
            ) as temp_file:
                # Write code to the file
                temp_file.write("""
// Sandbox wrapper
try {
    // Capture start time
    const startTime = Date.now();
    
    // Capture console output
    let output = '';
    const originalConsole = console.log;
    console.log = function() {
        output += Array.from(arguments).join(' ') + '\\n';
        originalConsole.apply(console, arguments);
    };
    
""")
                temp_file.write(code)
                temp_file.write("""

    // Prepare result
    const result = {
        success: true,
        error: '',
        output: output,
        execution_time: (Date.now() - startTime) / 1000
    };
    
    console.log(JSON.stringify(result));
} catch (error) {
    // Handle errors
    const result = {
        success: false,
        error: error.toString(),
        output: '',
        execution_time: 0
    };
    
    console.log(JSON.stringify(result));
}
""")
                temp_path = temp_file.name
            
            # Check if Node.js is available
            try:
                # Execute the code with Node.js
                start_time = time.time()
                process = subprocess.Popen(
                    ['node', temp_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    cwd=str(self.temp_dir)
                )
                
                try:
                    # Wait for the process to complete with timeout
                    stdout, stderr = process.communicate(timeout=self.timeout_seconds)
                    execution_time = time.time() - start_time
                    
                    # Find the last JSON object in stdout
                    try:
                        # Extract the last line that looks like a JSON object
                        json_lines = [line for line in stdout.splitlines() if line.strip().startswith('{')]
                        if json_lines:
                            last_json = json_lines[-1]
                            result = json.loads(last_json)
                            result['execution_time'] = execution_time  # Use actual wall time
                            logger.debug(f"JavaScript execution completed in {execution_time:.2f}s")
                        else:
                            # No JSON found, return raw output
                            result = {
                                'success': process.returncode == 0,
                                'error': stderr,
                                'output': stdout,
                                'execution_time': execution_time
                            }
                    except json.JSONDecodeError:
                        # If output is not valid JSON, return raw output
                        result = {
                            'success': process.returncode == 0,
                            'error': stderr,
                            'output': stdout,
                            'execution_time': execution_time
                        }
                    
                except subprocess.TimeoutExpired:
                    # Kill the process if it times out
                    process.kill()
                    stdout, stderr = process.communicate()
                    
                    logger.warning(f"JavaScript execution timed out after {self.timeout_seconds}s")
                    result = {
                        'success': False,
                        'error': f"Execution timed out after {self.timeout_seconds} seconds",
                        'output': stdout,
                        'execution_time': self.timeout_seconds
                    }
                
            except FileNotFoundError:
                # Node.js not available
                logger.warning("Node.js not found, cannot execute JavaScript")
                result = {
                    'success': False,
                    'error': "Node.js not found on the system, cannot execute JavaScript",
                    'output': '',
                    'execution_time': 0
                }
            
            # Clean up temporary file
            try:
                os.unlink(temp_path)
            except Exception as e:
                logger.warning(f"Error cleaning up temp files: {str(e)}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing JavaScript code: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'output': '',
                'execution_time': 0
            }
    
    def execute_code(self, code: str, language: str) -> Dict[str, Any]:
        """
        Execute code in the appropriate sandbox based on language.
        
        Args:
            code: Code to execute
            language: Programming language
            
        Returns:
            Dictionary with execution results
        """
        language = language.lower()
        
        if language in ['python', 'py']:
            return self.execute_python(code)
            
        elif language in ['javascript', 'js']:
            return self.execute_javascript(code)
            
        else:
            logger.warning(f"Unsupported language for execution: {language}")
            return {
                'success': False,
                'error': f"Unsupported language: {language}",
                'output': '',
                'execution_time': 0
            } 