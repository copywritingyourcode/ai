"""
Code executor module for safely running code in a sandbox environment.

This module provides functionality to execute Python code in a controlled
environment, with limits on execution time and system resource usage.
"""

import logging
import subprocess
import os
import tempfile
import time
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, Any, Set
import yaml
import threading
import signal
import uuid
import shutil

# Logger for this module
logger = logging.getLogger(__name__)


class CodeExecutor:
    """
    Executes Python code in a safe, sandboxed environment.
    
    This class provides methods to run code with resource constraints,
    capture output, and enforce execution limits.
    """
    
    def __init__(self, config_path: Union[str, Path]):
        """
        Initialize the code executor.
        
        Args:
            config_path: Path to the configuration file
        """
        self.config_path = Path(config_path)
        
        # Load configuration
        with open(self.config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # Extract code executor settings
        code_tool_config = self.config['code_tools']['executor']
        
        # Execution timeout in seconds
        self.execution_timeout = code_tool_config.get('execution_timeout', 30)
        
        # Maximum memory usage in MB
        self.max_memory_mb = code_tool_config.get('max_memory_mb', 200)
        
        # Allowed modules for execution
        self.allowed_modules = set(code_tool_config.get('allowed_modules', []))
        
        # Disallowed modules for execution
        self.disallowed_modules = set(code_tool_config.get('disallowed_modules', []))
        
        # Base directory for execution
        self.base_dir = Path(code_tool_config.get('execution_dir', tempfile.gettempdir()))
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Code executor initialized with timeout: {self.execution_timeout}s, "
                    f"max memory: {self.max_memory_mb}MB")
    
    def execute_code(
        self, 
        code: str,
        inputs: Optional[str] = None,
        execution_dir: Optional[Union[str, Path]] = None,
        dependencies: Optional[List[str]] = None,
        env_vars: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Execute Python code in a safe environment.
        
        Args:
            code: Python code to execute
            inputs: Input data to provide to the code (via stdin)
            execution_dir: Directory to run the code in (temporary dir if None)
            dependencies: List of pip dependencies to install
            env_vars: Environment variables to set
            
        Returns:
            A dictionary containing execution results:
                - success: Whether execution completed successfully
                - output: stdout from the execution
                - error: stderr from the execution
                - execution_time: Time taken to execute (seconds)
                - exit_code: Exit code from the process
        """
        execution_id = str(uuid.uuid4())
        
        # Create a temporary directory for execution
        if execution_dir:
            temp_dir = Path(execution_dir)
            temp_dir.mkdir(parents=True, exist_ok=True)
            cleanup_dir = False
        else:
            temp_dir = Path(tempfile.mkdtemp(dir=self.base_dir))
            cleanup_dir = True
        
        try:
            # Record execution start time
            start_time = time.time()
            
            # Create code file
            code_file = temp_dir / "code_to_execute.py"
            with open(code_file, 'w') as f:
                f.write(self._prepare_code(code))
            
            # Create input file if needed
            input_file = None
            if inputs:
                input_file = temp_dir / "input.txt"
                with open(input_file, 'w') as f:
                    f.write(inputs)
            
            # Setup virtual environment if dependencies are required
            venv_dir = None
            python_exe = sys.executable
            
            if dependencies:
                venv_dir = temp_dir / "venv"
                result = self._create_virtual_env(venv_dir, dependencies)
                if not result['success']:
                    return {
                        'success': False,
                        'output': '',
                        'error': f"Failed to set up virtual environment: {result['error']}",
                        'execution_time': time.time() - start_time,
                        'exit_code': 1
                    }
                python_exe = self._get_venv_python(venv_dir)
            
            # Execute the code
            result = self._run_process(
                python_exe,
                code_file,
                temp_dir,
                input_file,
                env_vars
            )
            
            # Record execution end time
            end_time = time.time()
            execution_time = end_time - start_time
            
            # Prepare result
            return {
                'success': result['exit_code'] == 0,
                'output': result['stdout'],
                'error': result['stderr'],
                'execution_time': execution_time,
                'exit_code': result['exit_code']
            }
            
        except Exception as e:
            logger.error(f"Error executing code: {str(e)}")
            return {
                'success': False,
                'output': '',
                'error': f"Error executing code: {str(e)}",
                'execution_time': time.time() - start_time,
                'exit_code': 1
            }
        finally:
            # Clean up temporary directory if we created it
            if cleanup_dir and temp_dir.exists():
                try:
                    shutil.rmtree(temp_dir)
                except Exception as e:
                    logger.warning(f"Failed to clean up temporary directory: {str(e)}")
    
    def _prepare_code(self, code: str) -> str:
        """
        Prepare code for execution by adding import restrictions.
        
        Args:
            code: Python code to prepare
            
        Returns:
            Modified code with import restrictions
        """
        # Add import restrictions as part of the code
        restrict_imports = """
import builtins
import sys
import importlib

# Store original __import__ function
original_import = builtins.__import__

# Store original importlib.import_module
original_import_module = importlib.import_module

# Allowed modules
ALLOWED_MODULES = {allowed_modules}

# Disallowed modules
DISALLOWED_MODULES = {disallowed_modules}

# Import restriction function
def restricted_import(name, *args, **kwargs):
    if DISALLOWED_MODULES and name in DISALLOWED_MODULES:
        raise ImportError(f"Import of '{{name}}' is not allowed for security reasons")
    
    if ALLOWED_MODULES and name not in ALLOWED_MODULES and not any(name.startswith(m + '.') for m in ALLOWED_MODULES):
        raise ImportError(f"Import of '{{name}}' is not allowed. Only these modules can be imported: {{ALLOWED_MODULES}}")
    
    return original_import(name, *args, **kwargs)

# Restricted importlib.import_module
def restricted_import_module(name, *args, **kwargs):
    if DISALLOWED_MODULES and name in DISALLOWED_MODULES:
        raise ImportError(f"Import of '{{name}}' is not allowed for security reasons")
    
    if ALLOWED_MODULES and name not in ALLOWED_MODULES and not any(name.startswith(m + '.') for m in ALLOWED_MODULES):
        raise ImportError(f"Import of '{{name}}' is not allowed. Only these modules can be imported: {{ALLOWED_MODULES}}")
    
    return original_import_module(name, *args, **kwargs)

# Apply import restrictions if enabled
if {apply_restrictions}:
    builtins.__import__ = restricted_import
    importlib.import_module = restricted_import_module

# Resource limitation
import resource
if sys.platform != 'win32':
    # Set memory limit (in bytes)
    resource.setrlimit(resource.RLIMIT_AS, ({max_memory_bytes}, {max_memory_bytes}))

# User code starts here
""".format(
            allowed_modules=repr(list(self.allowed_modules)) if self.allowed_modules else "set()",
            disallowed_modules=repr(list(self.disallowed_modules)) if self.disallowed_modules else "set()",
            apply_restrictions=repr(bool(self.allowed_modules or self.disallowed_modules)),
            max_memory_bytes=self.max_memory_mb * 1024 * 1024
        )
        
        return restrict_imports + "\n\n" + code
    
    def _create_virtual_env(self, venv_dir: Path, dependencies: List[str]) -> Dict[str, Any]:
        """
        Create a virtual environment with specified dependencies.
        
        Args:
            venv_dir: Directory for the virtual environment
            dependencies: List of pip dependencies to install
            
        Returns:
            Dictionary with success status and error message if any
        """
        logger.info(f"Creating virtual environment at {venv_dir}")
        
        try:
            # Create virtual environment
            subprocess.run(
                [sys.executable, "-m", "venv", str(venv_dir)],
                check=True,
                capture_output=True,
                text=True
            )
            
            # Install dependencies
            pip_path = self._get_venv_pip(venv_dir)
            
            # Install each dependency separately for better error handling
            for dependency in dependencies:
                # Sanitize the dependency to prevent command injection
                # Only allow alphanumeric, dots, hyphens, underscores, and version constraints
                sanitized = ''.join(c for c in dependency if c.isalnum() or c in '.-_<>=~!')
                if sanitized != dependency:
                    return {
                        'success': False,
                        'error': f"Invalid dependency name: {dependency}"
                    }
                
                logger.info(f"Installing dependency: {dependency}")
                result = subprocess.run(
                    [pip_path, "install", dependency],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=120  # 2-minute timeout for dependency installation
                )
                
                if result.returncode != 0:
                    return {
                        'success': False,
                        'error': f"Failed to install {dependency}: {result.stderr}"
                    }
            
            return {
                'success': True,
                'error': ''
            }
            
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': "Dependency installation timed out"
            }
        except Exception as e:
            return {
                'success': False,
                'error': f"Failed to create virtual environment: {str(e)}"
            }
    
    def _get_venv_python(self, venv_dir: Path) -> str:
        """
        Get the path to the Python executable in a virtual environment.
        
        Args:
            venv_dir: Directory of the virtual environment
            
        Returns:
            Path to the Python executable
        """
        if os.name == 'nt':  # Windows
            return str(venv_dir / "Scripts" / "python.exe")
        else:  # Unix/Linux/Mac
            return str(venv_dir / "bin" / "python")
    
    def _get_venv_pip(self, venv_dir: Path) -> str:
        """
        Get the path to the pip executable in a virtual environment.
        
        Args:
            venv_dir: Directory of the virtual environment
            
        Returns:
            Path to the pip executable
        """
        if os.name == 'nt':  # Windows
            return str(venv_dir / "Scripts" / "pip.exe")
        else:  # Unix/Linux/Mac
            return str(venv_dir / "bin" / "pip")
    
    def _run_process(
        self,
        python_exe: str,
        code_file: Path,
        working_dir: Path,
        input_file: Optional[Path] = None,
        env_vars: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Run a Python process with time and resource constraints.
        
        Args:
            python_exe: Path to the Python executable
            code_file: Path to the Python file to execute
            working_dir: Working directory for execution
            input_file: Path to the input file (if any)
            env_vars: Environment variables to set
            
        Returns:
            Dictionary with process results:
                - stdout: Standard output from the process
                - stderr: Standard error output
                - exit_code: Process exit code
        """
        # Prepare command
        cmd = [python_exe, str(code_file)]
        
        # Prepare environment
        proc_env = os.environ.copy()
        if env_vars:
            proc_env.update(env_vars)
        
        # Prepare input
        stdin_data = None
        if input_file and input_file.exists():
            with open(input_file, 'r') as f:
                stdin_data = f.read()
        
        try:
            # Run the process with timeout
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE if stdin_data else None,
                text=True,
                cwd=str(working_dir),
                env=proc_env
            )
            
            # Wait for process with timeout
            try:
                stdout, stderr = process.communicate(
                    input=stdin_data,
                    timeout=self.execution_timeout
                )
                
                return {
                    'stdout': stdout,
                    'stderr': stderr,
                    'exit_code': process.returncode
                }
                
            except subprocess.TimeoutExpired:
                # Kill the process if it times out
                self._kill_process(process)
                
                return {
                    'stdout': '',
                    'stderr': f"Execution timed out after {self.execution_timeout} seconds",
                    'exit_code': -1
                }
                
        except Exception as e:
            logger.error(f"Error running process: {str(e)}")
            return {
                'stdout': '',
                'stderr': f"Error running process: {str(e)}",
                'exit_code': 1
            }
    
    def _kill_process(self, process: subprocess.Popen) -> None:
        """
        Kill a process and its child processes.
        
        Args:
            process: Process to kill
        """
        try:
            # Try to terminate gracefully first
            process.terminate()
            
            # Wait a moment for termination
            try:
                process.wait(timeout=2)
                return
            except subprocess.TimeoutExpired:
                pass
            
            # If still running, kill forcefully
            if process.poll() is None:
                if os.name == 'nt':  # Windows
                    subprocess.run(['taskkill', '/F', '/T', '/PID', str(process.pid)], 
                                  capture_output=True, check=False)
                else:  # Unix/Linux/Mac
                    process.kill()
                    
                    # Kill process group if available
                    try:
                        os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                    except (AttributeError, ProcessLookupError):
                        pass
        
        except Exception as e:
            logger.error(f"Error killing process: {str(e)}")
    
    def execute_file(
        self,
        file_path: Union[str, Path],
        inputs: Optional[str] = None,
        execution_dir: Optional[Union[str, Path]] = None,
        dependencies: Optional[List[str]] = None,
        env_vars: Optional[Dict[str, str]] = None,
        args: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Execute a Python file in a safe environment.
        
        Args:
            file_path: Path to the Python file to execute
            inputs: Input data to provide to the script (via stdin)
            execution_dir: Directory to run the code in (file's directory if None)
            dependencies: List of pip dependencies to install
            env_vars: Environment variables to set
            args: Command-line arguments to pass to the script
            
        Returns:
            A dictionary containing execution results
        """
        file_path = Path(file_path)
        
        # Default execution directory to file's directory
        if execution_dir is None:
            execution_dir = file_path.parent
        else:
            execution_dir = Path(execution_dir)
        
        # Check if file exists
        if not file_path.exists():
            return {
                'success': False,
                'output': '',
                'error': f"File not found: {file_path}",
                'execution_time': 0,
                'exit_code': 1
            }
        
        # Record execution start time
        start_time = time.time()
        
        try:
            # Setup virtual environment if dependencies are required
            venv_dir = None
            python_exe = sys.executable
            
            if dependencies:
                # Create a temporary directory for the venv
                temp_dir = Path(tempfile.mkdtemp(dir=self.base_dir))
                venv_dir = temp_dir / "venv"
                
                result = self._create_virtual_env(venv_dir, dependencies)
                if not result['success']:
                    return {
                        'success': False,
                        'output': '',
                        'error': f"Failed to set up virtual environment: {result['error']}",
                        'execution_time': time.time() - start_time,
                        'exit_code': 1
                    }
                python_exe = self._get_venv_python(venv_dir)
            
            # Create input file if needed
            input_file = None
            if inputs:
                input_dir = Path(tempfile.mkdtemp(dir=self.base_dir))
                input_file = input_dir / "input.txt"
                with open(input_file, 'w') as f:
                    f.write(inputs)
            
            # Prepare command
            cmd = [python_exe, str(file_path)]
            if args:
                cmd.extend(args)
            
            # Prepare environment
            proc_env = os.environ.copy()
            if env_vars:
                proc_env.update(env_vars)
            
            # Prepare input
            stdin_data = None
            if input_file and input_file.exists():
                with open(input_file, 'r') as f:
                    stdin_data = f.read()
            
            try:
                # Run the process with timeout
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    stdin=subprocess.PIPE if stdin_data else None,
                    text=True,
                    cwd=str(execution_dir),
                    env=proc_env
                )
                
                # Wait for process with timeout
                try:
                    stdout, stderr = process.communicate(
                        input=stdin_data,
                        timeout=self.execution_timeout
                    )
                    
                    end_time = time.time()
                    
                    return {
                        'success': process.returncode == 0,
                        'output': stdout,
                        'error': stderr,
                        'execution_time': end_time - start_time,
                        'exit_code': process.returncode
                    }
                    
                except subprocess.TimeoutExpired:
                    # Kill the process if it times out
                    self._kill_process(process)
                    
                    return {
                        'success': False,
                        'output': '',
                        'error': f"Execution timed out after {self.execution_timeout} seconds",
                        'execution_time': self.execution_timeout,
                        'exit_code': -1
                    }
                    
            except Exception as e:
                logger.error(f"Error running process: {str(e)}")
                return {
                    'success': False,
                    'output': '',
                    'error': f"Error running process: {str(e)}",
                    'execution_time': time.time() - start_time,
                    'exit_code': 1
                }
                
        finally:
            # Clean up temporary directories
            if venv_dir and venv_dir.parent.exists():
                try:
                    shutil.rmtree(venv_dir.parent)
                except Exception as e:
                    logger.warning(f"Failed to clean up virtual environment: {str(e)}")
            
            if input_file and input_file.parent.exists():
                try:
                    shutil.rmtree(input_file.parent)
                except Exception as e:
                    logger.warning(f"Failed to clean up input file: {str(e)}")
    
    def execute_function(
        self,
        func_code: str,
        func_name: str,
        args: List[Any] = None,
        kwargs: Dict[str, Any] = None,
        dependencies: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Execute a single Python function safely.
        
        Args:
            func_code: Python code defining the function
            func_name: Name of the function to execute
            args: Positional arguments to pass to the function
            kwargs: Keyword arguments to pass to the function
            dependencies: List of pip dependencies to install
            
        Returns:
            Dictionary with execution results:
                - success: Whether execution completed successfully
                - result: Return value of the function (if successful)
                - error: Error message (if any)
                - execution_time: Time taken to execute
        """
        # Prepare arguments
        args = args or []
        kwargs = kwargs or {}
        
        # Serialize arguments and keyword arguments to JSON
        serialized_args = json.dumps(args)
        serialized_kwargs = json.dumps(kwargs)
        
        # Create wrapper code to execute the function and return its result
        wrapper_code = f"""
{func_code}

import json
import sys
import traceback

def main():
    try:
        # Deserialize arguments
        args = json.loads('''{serialized_args}''')
        kwargs = json.loads('''{serialized_kwargs}''')
        
        # Call the function
        result = {func_name}(*args, **kwargs)
        
        # Return result
        print("##RESULT_START##")
        print(json.dumps(result))
        print("##RESULT_END##")
        
        return 0
    except Exception as e:
        print(f"Error executing function: {{str(e)}}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
"""
        
        # Execute the wrapper code
        execution_result = self.execute_code(
            wrapper_code,
            dependencies=dependencies
        )
        
        # Extract function result from output if successful
        result_value = None
        if execution_result['success']:
            output = execution_result['output']
            try:
                # Extract the result portion
                start_marker = "##RESULT_START##"
                end_marker = "##RESULT_END##"
                
                start_idx = output.find(start_marker)
                end_idx = output.find(end_marker)
                
                if start_idx != -1 and end_idx != -1:
                    result_json = output[start_idx + len(start_marker):end_idx].strip()
                    result_value = json.loads(result_json)
            except Exception as e:
                execution_result['success'] = False
                execution_result['error'] += f"\nError parsing function result: {str(e)}"
        
        return {
            'success': execution_result['success'],
            'result': result_value,
            'error': execution_result['error'],
            'execution_time': execution_result['execution_time']
        } 