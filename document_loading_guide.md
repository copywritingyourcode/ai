# Document Loading Guide for Local AI Assistant

This guide explains how to load different file formats into the Local AI Assistant for knowledge retrieval.

## Supported File Formats

The Local AI Assistant currently supports the following file formats:

- **PDF** (`.pdf`) - Requires PyMuPDF/fitz library
- **Text** (`.txt`) - Plain text files
- **RTF** (`.rtf`) - Rich Text Format files, requires striprtf library

## Prerequisites

To ensure all document formats are supported, make sure you have the required libraries installed:

```bash
# Install required packages
pip install -r requirements.txt

# If striprtf is missing (for RTF support), install it directly
pip install striprtf>=0.0.24
```

## How to Load Documents

### Using the Command Line Interface

1. Start the Local AI Assistant:
   ```bash
   python main.py
   ```

2. Use the `/load` command followed by the file path:
   ```
   /load path/to/your/document.pdf
   ```
   
   Examples:
   ```
   /load sample_document.txt
   /load data/important_info.pdf
   /load documents/notes.rtf
   ```

3. To view all loaded documents, use the `/docs` command:
   ```
   /docs
   ```

### Loading Process

When you load a document:

1. The system checks if the file exists and is of a supported format
2. The file content is extracted based on the file type:
   - PDF files: Text is extracted from all pages
   - TXT files: Content is read directly
   - RTF files: RTF markup is stripped to extract plain text
3. The document is chunked and stored in the system's memory
4. A unique document ID is assigned for future reference

### Troubleshooting

If you encounter issues loading documents:

1. **File Not Found**: Ensure the file path is correct
2. **Unsupported Format**: Check that the file has one of the supported extensions
3. **Missing Dependencies**:
   - For PDF files: `pip install pymupdf`
   - For RTF files: `pip install striprtf`
4. **File Too Large**: Files are limited to 50MB by default (configurable in config.yaml)

## Creating and Loading Test Documents

For testing purposes, you can create simple test documents:

### Text File Example
```bash
echo "This is a test document." > test_document.txt
echo "It contains important information." >> test_document.txt
echo "**TEST_MARKER**" >> test_document.txt
```

### RTF File Example
```bash
cat > test_document.rtf << 'EOF'
{\rtf1\ansi\ansicpg1252
{\fonttbl\f0\fswiss\fcharset0 Helvetica;}
{\colortbl;\red255\green255\blue255;}
\f0\fs24 \cf0 This is a test RTF document.\
\
**RTF_TEST_MARKER**\
\
This document tests RTF loading functionality.
}
EOF
```

Then load them:
```
/load test_document.txt
/load test_document.rtf
```

## Retrieving Document Information

After loading documents, you can:

1. List all documents with `/docs`
2. Ask questions about the document content
3. View memory context with `/memory`

The assistant will automatically use the document content when answering questions related to the loaded documents. 