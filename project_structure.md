# Local AI Assistant Project Structure

```
local_ai_assistant/
├── README.md                  # Project documentation
├── requirements.txt           # Python dependencies
├── config.yaml                # Configuration parameters
├── main.py                    # Entry point script
├── cli/
│   ├── __init__.py
│   ├── interface.py           # CLI user interface
│   └── command_parser.py      # Command handling logic
├── models/
│   ├── __init__.py
│   ├── model_manager.py       # Ollama model loading/unloading
│   └── embeddings.py          # Vector embedding generation
├── memory/
│   ├── __init__.py
│   ├── vector_store.py        # ChromaDB integration
│   └── retrieval.py           # Memory search and retrieval
├── document/
│   ├── __init__.py
│   ├── loader.py              # PDF/TXT loading
│   ├── chunker.py             # Text chunking strategies
│   └── indexer.py             # Document indexing
├── debug/
│   ├── __init__.py
│   ├── response_analyzer.py   # AI response evaluation
│   ├── code_sandbox.py        # Safe code execution
│   └── issue_logger.py        # Logging and recommendations
├── code_tools/
│   ├── __init__.py
│   ├── concentrator.py        # Code gathering
│   └── splitter.py            # Code chunking
├── utils/
│   ├── __init__.py
│   ├── token_counter.py       # Token counting utilities
│   └── logging_setup.py       # Logging configuration
└── tests/
    ├── __init__.py
    ├── unit/                  # Unit tests for components
    ├── integration/           # Integration tests
    └── fixtures/              # Test data
``` 