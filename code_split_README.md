# Code Splitter Tool

A utility for splitting codebases into token-limited files for AI review.

## Overview

This tool helps you prepare your codebase for review by AI tools by:

1. Concentrating your code into a single document
2. Splitting that document into multiple files that respect token limits
3. Preserving file boundaries and code structure
4. Generating metadata about the split

## Installation

No additional installation is required beyond the dependencies already in the Local AI Assistant project.

## Usage

```bash
python3 code_split.py [path] [options]
```

### Arguments

- `path`: Path to the directory or file list to process

### Options

- `-o, --output-dir`: Directory to save the split files (default: "code_splits")
- `-t, --token-limit`: Maximum tokens per file (default: 8000)
- `-m, --model`: Model name for token counting (default: "default")
- `-c, --config`: Path to config.yaml file (default: "config.yaml")
- `-r, --recursive`: Recursively process subdirectories (default: True)
- `--include-hidden`: Include hidden files and directories
- `-f, --files`: Process specific files instead of a directory
- `-v, --verbose`: Increase output verbosity

## Examples

Process a directory:
```bash
python3 code_split.py local_ai_assistant/code_tools -o code_splits -t 4000
```

Process the entire project:
```bash
python3 code_split.py local_ai_assistant -o code_splits_full
```

Process a list of files:
```bash
# Create a file with a list of paths
echo "local_ai_assistant/code_tools/concentrator.py" > files_to_process.txt
echo "local_ai_assistant/code_tools/code_splitter.py" >> files_to_process.txt

# Process the list
python3 code_split.py files_to_process.txt -f -o code_splits_selected
```

## Output

The tool generates:

1. Multiple text files containing your code, each respecting the token limit
2. A metadata JSON file with information about the split

## How It Works

1. The tool uses the `CodeConcentrator` class to gather all code files into a single document
2. It then uses the `TokenCounter` to measure token usage
3. The code is split into chunks that respect file boundaries when possible
4. Large files are split with clear part markers
5. All files are saved with consistent naming for easy sorting

## Configuration

The tool uses the same configuration file as the Local AI Assistant. The relevant sections are:

```yaml
code_tools:
  # Code concentration settings
  concentrator:
    ignored_patterns:
      - "*.pyc"
      - "__pycache__/*"
      - ".git/*"
    include_extensions:
      - "py"
      - "js"
      - "html"
    max_file_size_kb: 500
  
  # Code splitter settings
  splitter:
    token_limit: 8000
    output_dir: "code_splits"
    preserve_file_boundaries: true
``` 