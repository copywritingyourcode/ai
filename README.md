# Local AI Assistant

A powerful local AI assistant that runs entirely on your machine, using Ollama for local LLMs.

## Features

- **Local LLM Integration**: Uses Ollama to run models like Gemma3:27B locally
- **Document Processing**: Load and query PDF, TXT, and RTF files
- **Persistent Memory**: Remembers conversation history using ChromaDB
- **Rich Terminal Interface**: Beautiful CLI with color and formatting
- **Debug Mode**: Analyze AI responses for issues
- **Thinking Display**: See the AI's thought process

## Requirements

- Python 3.10+
- Ollama installed and running locally
- Sufficient RAM for running large language models

## Installation

1. Clone this repository:
```bash
git clone https://github.com/yourusername/local-ai-assistant.git
cd local-ai-assistant
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Make sure Ollama is installed and running:
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags
```

## Usage

Run the assistant:
```bash
./run_assistant.sh
```

Or manually:
```bash
python3 main.py
```

### Commands

- `/help` - Show available commands
- `/use <model>` - Switch to a different model
- `/load <file>` - Load a document (PDF, TXT, RTF)
- `/debug` - Toggle debug mode
- `/thinking` - Toggle thinking display
- `/models` - List available models
- `/docs` - List loaded documents
- `/memory` - Show recent memory
- `/status` - Show system status
- `/clear` - Clear the screen
- `/quit` - Exit the assistant

## Configuration

Edit `config.yaml` to customize:
- Default model
- Embedding model
- Document settings
- Memory settings
- Debug options

## Recent Fixes

- Added support for RTF document loading (requires striprtf library)
- Fixed initialization error in CLI interface
- Improved model response when memory context isn't available
- Fixed configuration key from 'models' to 'model' to match code expectations
- Updated Ollama API handling to support both old and new API formats
- Fixed ChromaDB query issues with 'order_by' parameter
- Improved error handling in debug mode
- Enhanced document loading and indexing
- Fixed memory retrieval for conversation context
- Added mock mode support when Ollama is not available

## Project Structure

```
local_ai_assistant/
├── cli/              # Command-line interface
├── models/           # Model management
├── memory/           # Vector store and memory
├── document/         # Document handling
├── debug/            # Response analysis
├── utils/            # Utility functions
└── main.py           # Entry point
```

## Documentation

- Check `document_loading_guide.md` for detailed instructions on loading different document types

## License

MIT License