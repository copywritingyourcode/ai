"""
CLI interface for Local AI Assistant.

This module provides the command-line interface for interacting with the assistant.
"""

import logging
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import traceback
import yaml

# Add rich for better terminal formatting
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.markdown import Markdown
    from rich.table import Table
    from rich.style import Style
    from rich.text import Text
    from rich.live import Live
    from rich.spinner import Spinner
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# Local imports
from local_ai_assistant.cli.command_parser import parse_command
from local_ai_assistant.models.model_manager import ModelManager
from local_ai_assistant.memory.vector_store import VectorStore
from local_ai_assistant.document.loader import DocumentLoader
from local_ai_assistant.debug.response_analyzer import ResponseAnalyzer


# Logger for this module
logger = logging.getLogger(__name__)


class CLI:
    """
    Command-line interface for interacting with the local AI assistant.
    
    This class handles user input, command processing, and display of
    assistant responses.
    """
    
    def __init__(
        self,
        config_path: Union[str, Path],
        model_manager: ModelManager,
        vector_store: VectorStore,
        document_loader: DocumentLoader,
        debug_enabled: bool = True
    ):
        """
        Initialize the CLI interface.
        
        Args:
            config_path: Path to the configuration file
            model_manager: Model manager instance
            vector_store: Vector store instance
            document_loader: Document loader instance
            debug_enabled: Whether debug mode is enabled
        """
        self.config_path = Path(config_path)
        self.model_manager = model_manager
        self.vector_store = vector_store
        self.document_loader = document_loader
        self.debug_enabled = debug_enabled
        
        # Load configuration
        with open(self.config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # Check if Ollama is in mock mode
        self.mock_mode = not self.model_manager.ollama_available
        
        # Store active model reference
        self.active_model = self.model_manager.active_model
        
        # Command history for tracking user inputs
        self.command_history = []
        
        # Load CLI-specific configuration
        # Rich console setup
        self.rich_enabled = True
        self.console = Console()
        
        # Define color styles
        self.user_style = "blue bold"
        self.assistant_style = "green"
        self.system_style = "yellow"
        self.debug_style = "magenta"
        self.error_style = "red bold"  # Using red bold for errors
        self.special_style = "cyan"
        
        # Thinking mode is disabled by default
        self.show_thinking = False
        
        # Initialize response analyzer
        if self.debug_enabled:
            from local_ai_assistant.debug.response_analyzer import ResponseAnalyzer
            self.response_analyzer = ResponseAnalyzer(self.config_path, self.model_manager)
        else:
            self.response_analyzer = None
            
        logger.info("CLI interface initialized")
        
    def run(self) -> int:
        """
        Run the CLI interface.
        
        Returns:
            Exit code (0 for success, non-zero for error)
        """
        logger.info("Starting CLI interface")
        
        try:
            # Print welcome message
            self._print_welcome()
            
            # Main interaction loop
            while True:
                # Get user input
                try:
                    if self.rich_enabled:
                        self.console.print("\nYou: ", style=self.user_style, end="")
                        user_input = input()
                    else:
                        user_input = input("\nYou: ")
                except EOFError:
                    self._print("Exiting...", style="info")
                    break
                except KeyboardInterrupt:
                    self._print("Exiting...", style="info")
                    break
                
                # Add to history
                self.command_history.append(user_input)
                
                # Process input
                if user_input.lower() in ['exit', 'quit', '/quit', '/exit']:
                    self._print("Exiting...", style="info")
                    break
                
                # Handle special commands
                if user_input.startswith('/'):
                    self._handle_command(user_input)
                    continue
                
                # Process regular input as a question to the AI
                self._process_query(user_input)
            
            # Shutdown cleanly
            self.model_manager.shutdown()
            return 0
            
        except Exception as e:
            logger.exception(f"Error in CLI: {str(e)}")
            self._print(f"An error occurred: {str(e)}", style="error")
            return 1
    
    def _print_welcome(self):
        """Print welcome message with setup information."""
        if self.rich_enabled:
            welcome_text = f"""
# Welcome to Local AI Assistant

- Active model: {self.active_model}
- Debug mode: {'Enabled' if self.debug_enabled else 'Disabled'}
- Thinking display: {'Enabled' if self.show_thinking else 'Disabled'}

"""
            if self.mock_mode:
                welcome_text += """
⚠️ WARNING: Running in MOCK MODE - Ollama is not available
         The assistant will provide mock responses
         Install Ollama and run it before starting for full functionality
"""
            
            welcome_text += """
Type `/help` for available commands or `/quit` to exit.
"""
            
            welcome_md = Markdown(welcome_text)
            self.console.print(Panel(welcome_md, title="Local AI Assistant", border_style="blue"))
        else:
            print("\n" + "=" * 80)
            print("Welcome to Local AI Assistant")
            print("=" * 80)
            print(f"Active model: {self.active_model}")
            print(f"Debug mode: {'Enabled' if self.debug_enabled else 'Disabled'}")
            print(f"Thinking display: {'Enabled' if self.show_thinking else 'Disabled'}")
            
            if self.mock_mode:
                print("WARNING: Running in MOCK MODE - Ollama is not available")
                print("         The assistant will provide mock responses")
                print("         Install Ollama and run it before starting for full functionality")
            
            print("Type '/help' for available commands or '/quit' to exit")
            print("=" * 80)
    
    def _print(self, message: str, style: str = "default"):
        """
        Print a message with styling if rich is available.
        
        Args:
            message: Message to print
            style: Style to use (default, info, warning, error, debug)
        """
        if not self.rich_enabled:
            print(message)
            return
            
        if style == "default":
            self.console.print(message)
        elif style == "info":
            self.console.print(message, style=self.system_style)
        elif style == "warning":
            self.console.print(message, style=self.system_style)
        elif style == "error":
            self.console.print(message, style=self.error_style)
        elif style == "debug":
            self.console.print(message, style=self.debug_style)
        elif style == "user":
            self.console.print(message, style=self.user_style)
        elif style == "assistant":
            self.console.print(message, style=self.assistant_style)
    
    def _handle_command(self, command: str):
        """
        Handle special commands starting with '/'.
        
        Args:
            command: Command string
        """
        logger.debug(f"Handling command: {command}")
        
        # Parse command
        cmd_parts = command.strip().split()
        cmd = cmd_parts[0].lower()
        args = cmd_parts[1:] if len(cmd_parts) > 1 else []
        
        # Handle commands
        if cmd == '/help':
            self._show_help()
        elif cmd == '/use':
            self._switch_model(args)
        elif cmd == '/load':
            self._load_document(args)
        elif cmd == '/debug':
            self._toggle_debug(args)
        elif cmd == '/thinking':
            self._toggle_thinking(args)
        elif cmd == '/models':
            self._list_models()
        elif cmd == '/docs':
            self._list_documents()
        elif cmd == '/memory':
            self._show_memory(args)
        elif cmd == '/status':
            self._show_status()
        elif cmd == '/clear':
            self._clear_screen()
        else:
            self._print(f"Unknown command: {cmd}", style="warning")
            self._print("Type '/help' for available commands", style="info")
    
    def _show_help(self):
        """Show help information."""
        if self.rich_enabled:
            table = Table(title="Available Commands")
            table.add_column("Command", style="cyan")
            table.add_column("Description")
            
            table.add_row("/help", "Show this help message")
            table.add_row("/use <model>", "Switch to a different model")
            table.add_row("/load <file>", "Load a document")
            table.add_row("/debug [on|off]", "Enable or disable debug mode")
            table.add_row("/thinking [on|off]", "Show AI thinking process")
            table.add_row("/models", "List available models")
            table.add_row("/docs", "List loaded documents")
            table.add_row("/memory [n]", "Show recent memory (last n items)")
            table.add_row("/status", "Show system status")
            table.add_row("/clear", "Clear the screen")
            table.add_row("/quit", "Exit the assistant")
            
            self.console.print(table)
        else:
            print("\nAvailable Commands:")
            print("  /help           - Show this help message")
            print("  /use <model>    - Switch to a different model")
            print("  /load <file>    - Load a document")
            print("  /debug [on|off] - Enable or disable debug mode")
            print("  /thinking [on|off] - Show AI thinking process")
            print("  /models         - List available models")
            print("  /docs           - List loaded documents")
            print("  /memory [n]     - Show recent memory (last n items)")
            print("  /status         - Show system status")
            print("  /clear          - Clear the screen")
            print("  /quit           - Exit the assistant")
    
    def _switch_model(self, args):
        """
        Switch to a different model.
        
        Args:
            args: Command arguments (model name)
        """
        if not args:
            self._print("Please specify a model name", style="warning")
            return
        
        model_name = args[0]
        logger.info(f"Switching to model: {model_name}")
        
        # Try to switch model
        if self.rich_enabled:
            with self.console.status(f"Switching to model: {model_name}..."):
                success = self.model_manager.switch_model(model_name)
        else:
            self._print(f"Switching to model: {model_name}...", style="info")
            success = self.model_manager.switch_model(model_name)
        
        if success:
            self.active_model = model_name
            self._print(f"Switched to model: {model_name}", style="info")
        else:
            self._print(f"Failed to switch to model: {model_name}", style="error")
    
    def _toggle_thinking(self, args):
        """
        Toggle showing the AI thinking process.
        
        Args:
            args: Command arguments (on/off)
        """
        if not args:
            # Toggle current state
            self.show_thinking = not self.show_thinking
        elif args[0].lower() in ['on', 'true', '1', 'yes']:
            self.show_thinking = True
        elif args[0].lower() in ['off', 'false', '0', 'no']:
            self.show_thinking = False
        else:
            self._print("Invalid argument. Use '/thinking on' or '/thinking off'", style="warning")
            return
        
        logger.info(f"Thinking display: {self.show_thinking}")
        self._print(f"Thinking display: {'Enabled' if self.show_thinking else 'Disabled'}", style="info")
    
    def _load_document(self, args):
        """
        Load a document.
        
        Args:
            args: Command arguments (file path)
        """
        if not args:
            self._print("Please specify a file path", style="warning")
            return
        
        # Join all arguments to handle paths with spaces
        file_path = ' '.join(args)
        
        # Remove quotes if present
        if (file_path.startswith('"') and file_path.endswith('"')) or \
           (file_path.startswith("'") and file_path.endswith("'")):
            file_path = file_path[1:-1]
            
        logger.info(f"Loading document: {file_path}")
        
        # Convert to Path object to check if file exists
        path = Path(file_path)
        if not path.exists():
            self._print(f"File not found: {file_path}", style="error")
            self._print("Please check that the file exists and you have permission to access it.", style="info")
            return
            
        if path.is_dir():
            self._print(f"The path '{file_path}' is a directory, not a file.", style="error")
            self._print("Please specify a file path (PDF or TXT file).", style="info")
            return
        
        # Try to load document
        if self.rich_enabled:
            with self.console.status(f"Loading document: {path.name}..."):
                doc_id = self.document_loader.load_document(file_path)
                
                # Index the document if loaded successfully
                if doc_id:
                    # Import here to avoid circular imports
                    from local_ai_assistant.document.indexer import DocumentIndexer
                    indexer = DocumentIndexer(
                        self.config_path,
                        self.document_loader,
                        self.vector_store,
                        self.model_manager
                    )
                    self.console.print(f"Indexing document: {path.name}...", style=self.system_style)
                    indexer.index_document(doc_id)
        else:
            self._print(f"Loading document: {path.name}...", style="info")
            doc_id = self.document_loader.load_document(file_path)
            
            # Index the document if loaded successfully
            if doc_id:
                # Import here to avoid circular imports
                from local_ai_assistant.document.indexer import DocumentIndexer
                indexer = DocumentIndexer(
                    self.config_path,
                    self.document_loader,
                    self.vector_store,
                    self.model_manager
                )
                self._print(f"Indexing document: {path.name}...", style="info")
                indexer.index_document(doc_id)
        
        if doc_id:
            self._print(f"Document loaded with ID: {doc_id}", style="info")
            self._print(f"You can now ask questions about {path.name}", style="info")
        else:
            self._print(f"Failed to load document: {file_path}", style="error")
            
            # Get the file extension
            file_ext = path.suffix.lower().lstrip('.')
            if file_ext not in self.document_loader.supported_formats:
                self._print(f"Unsupported file format: {file_ext}", style="warning")
                self._print(f"Supported formats: {', '.join(self.document_loader.supported_formats)}", style="info")
            elif path.stat().st_size > (self.document_loader.max_file_size_mb * 1024 * 1024):
                self._print(f"File too large: {path.stat().st_size / (1024 * 1024):.2f} MB", style="warning")
                self._print(f"Maximum file size: {self.document_loader.max_file_size_mb} MB", style="info")
    
    def _toggle_debug(self, args):
        """
        Toggle debug mode.
        
        Args:
            args: Command arguments (on/off)
        """
        if not args:
            # Toggle current state
            self.debug_enabled = not self.debug_enabled
        elif args[0].lower() in ['on', 'true', '1', 'yes']:
            self.debug_enabled = True
        elif args[0].lower() in ['off', 'false', '0', 'no']:
            self.debug_enabled = False
        else:
            self._print("Invalid argument. Use '/debug on' or '/debug off'", style="warning")
            return
        
        # Initialize or remove response analyzer
        if self.debug_enabled and not self.response_analyzer:
            self.response_analyzer = ResponseAnalyzer(self.config_path, self.model_manager)
        elif not self.debug_enabled:
            self.response_analyzer = None
        
        logger.info(f"Debug mode: {self.debug_enabled}")
        self._print(f"Debug mode: {'Enabled' if self.debug_enabled else 'Disabled'}", style="info")
    
    def _list_models(self):
        """List available models."""
        models = self.model_manager.list_models()
        
        if not models:
            print("No models available")
            return
        
        print("\nAvailable Models:")
        for model in models:
            name = model.get('name', 'Unknown')
            is_active = name == self.active_model
            print(f"  {name} {'(active)' if is_active else ''}")
        
        if self.mock_mode:
            print("\nNOTE: Running in mock mode. These are mock model entries.")
    
    def _list_documents(self):
        """List loaded documents."""
        docs = self.document_loader.list_documents()
        
        if not docs:
            print("No documents loaded")
            return
        
        print("\nLoaded Documents:")
        for doc in docs:
            doc_id = doc.get('id', 'Unknown')
            filename = doc.get('metadata', {}).get('filename', 'Unknown')
            print(f"  {doc_id}: {filename}")
    
    def _show_memory(self, args):
        """
        Show recent memory.
        
        Args:
            args: Command arguments (number of items)
        """
        # Default to 5 items
        n = 5
        
        if args:
            try:
                n = int(args[0])
            except ValueError:
                print("Invalid argument. Number of items must be an integer.")
                return
        
        # Get recent messages
        messages = self.vector_store.get_recent_messages(n)
        
        if not messages:
            print("No memory items found")
            return
        
        print(f"\nRecent Memory ({len(messages)} items):")
        for i, msg in enumerate(messages):
            role = msg.get('metadata', {}).get('role', 'unknown')
            text = msg.get('text', '')
            timestamp = msg.get('metadata', {}).get('timestamp')
            
            # Format timestamp
            time_str = ''
            if timestamp:
                time_str = time.strftime(' [%Y-%m-%d %H:%M:%S]', time.localtime(timestamp))
            
            # Truncate long messages
            if len(text) > 100:
                text = text[:100] + "..."
            
            print(f"{i+1}. {role.capitalize()}{time_str}: {text}")
    
    def _show_status(self):
        """Show system status."""
        print("\nSystem Status:")
        print(f"  Mock mode: {'Enabled' if self.mock_mode else 'Disabled'}")
        print(f"  Debug mode: {'Enabled' if self.debug_enabled else 'Disabled'}")
        print(f"  Active model: {self.active_model}")
        
        # Vector store stats
        memory_count = len(self.vector_store.memory_items) if hasattr(self.vector_store, 'memory_items') else 'Unknown'
        print(f"  Memory items: {memory_count}")
        
        # Document stats
        doc_count = len(self.document_loader.documents) if hasattr(self.document_loader, 'documents') else 'Unknown'
        print(f"  Loaded documents: {doc_count}")
    
    def _clear_screen(self):
        """Clear the terminal screen."""
        os.system('cls' if os.name == 'nt' else 'clear')
        self._print_welcome()
    
    def _process_query(self, query: str):
        """
        Process a user query and generate a response.
        
        Args:
            query: User query string
        """
        try:
            self._print(f"You: {query}", style="user")
            
            # Get context from both conversation memory and documents
            combined_context = self.vector_store.get_combined_context(
                query_text=query,
                n_conversation=3,
                n_documents=3
            )
            
            # Format context for inclusion in prompt
            context_str = self.vector_store.format_context_for_prompt(combined_context)
            
            # Build prompt with context if available
            if context_str:
                prompt = f"""
                The following context may be helpful for answering the user's question:
                
                {context_str}
                
                User question: {query}
                
                If the context doesn't contain the information needed to answer the question, use your own knowledge to provide a helpful and accurate response.
                """
            else:
                prompt = f"""
                User question: {query}
                
                Please provide a helpful and accurate response based on your knowledge.
                """
            
            # Initialize thinking display if enabled
            thinking_displayed = False
            if self.show_thinking:
                self.console.print("[bold blue]Thinking...[/bold blue]")
                
                def update_thinking():
                    nonlocal thinking_displayed
                    if not thinking_displayed:
                        self.console.print("- Searching for relevant context...", style="dim")
                        self.console.print(f"- Found {len(combined_context)} relevant context items", style="dim")
                        self.console.print("- Generating response with Ollama model...", style="dim")
                        thinking_displayed = True
                
                # Use the console status with a string spinner name instead of a Spinner object
                with self.console.status("Generating response...", spinner="dots"):
                    # Add a slight delay to show thinking process
                    time.sleep(0.5)
                    update_thinking()
                    
                    # Generate response
                    response = self.model_manager.generate_text(prompt)
            else:
                # Generate response without thinking display
                with self.console.status("Generating response...", spinner="dots"):
                    response = self.model_manager.generate_text(prompt)
            
            # Print assistant response
            self._print(f"AI: {response}", style="assistant")
            
            # Add to memory
            self.vector_store.add_conversation_pair(query, response)
            
            # Analyze response in debug mode
            if self.debug_enabled:
                issues = self.response_analyzer.analyze_response(query, response)
                if issues:
                    self.console.print("\nDebug Info:", style=self.debug_style)
                    
                    # Handle both list/dict issues and string issues
                    if isinstance(issues, list):
                        for issue in issues:
                            if isinstance(issue, dict):
                                # Issue is a dictionary with category and message/description
                                if 'message' in issue:
                                    self.console.print(f"- {issue.get('category', 'issue')}: {issue['message']}", style=self.debug_style)
                                elif 'description' in issue:
                                    self.console.print(f"- {issue.get('category', 'issue')}: {issue['description']}", style=self.debug_style)
                                else:
                                    self.console.print(f"- {issue.get('category', 'issue')}: {str(issue)}", style=self.debug_style)
                            else:
                                # Issue is a string or other type
                                self.console.print(f"- Issue: {str(issue)}", style=self.debug_style)
                    elif isinstance(issues, str):
                        # Issues is a single string
                        self.console.print(f"- {issues}", style=self.debug_style)
                    else:
                        # Any other format
                        self.console.print(f"- Debug info: {str(issues)}", style=self.debug_style)
            
        except Exception as e:
            self.console.print(f"\nDebug Info:", style=self.debug_style)
            self.console.print(f"{traceback.format_exc()}", style=self.debug_style)
            self.console.print(f"Error generating response: {str(e)}", style=self.error_style) 