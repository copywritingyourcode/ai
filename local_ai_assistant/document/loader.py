"""
Document loader module for handling PDF and text files.

This module provides functions to load, process, and manage documents.
"""

import logging
import os
import json
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple
import yaml

# Try importing PyMuPDF, but don't fail if it's not available
try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

# Try importing striprtf, but don't fail if it's not available
try:
    from striprtf.striprtf import rtf_to_text
    STRIPRTF_AVAILABLE = True
except ImportError:
    STRIPRTF_AVAILABLE = False

# Logger for this module
logger = logging.getLogger(__name__)


class DocumentLoader:
    """
    Loads and manages documents for the Local AI Assistant.
    
    This class provides methods to load PDF and text files, extract
    their content, and manage document metadata.
    """
    
    def __init__(self, config_path: Union[str, Path]):
        """
        Initialize the document loader.
        
        Args:
            config_path: Path to the configuration file
        """
        self.config_path = Path(config_path)
        
        # Load configuration
        with open(self.config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # Extract document settings
        doc_config = self.config['document']
        
        # Storage directory
        self.storage_dir = Path(doc_config['storage_dir'])
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Supported formats
        self.supported_formats = doc_config.get('supported_formats', ['pdf', 'txt'])
        
        # Add rtf to supported formats if striprtf is available
        if STRIPRTF_AVAILABLE and 'rtf' not in self.supported_formats:
            self.supported_formats.append('rtf')
        
        # Max file size in MB
        self.max_file_size_mb = doc_config.get('max_file_size_mb', 50)
        
        # In-memory document storage
        self.documents = {}
        
        # Load existing documents
        self._load_documents()
        
        logger.info(f"Document loader initialized, supported formats: {self.supported_formats}")
    
    def load_document(self, file_path: Union[str, Path]) -> Optional[str]:
        """
        Load a document from a file.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            Document ID if successful, None otherwise
        """
        file_path = Path(file_path)
        
        # Check if file exists
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return None
        
        # Check file size
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        if file_size_mb > self.max_file_size_mb:
            logger.error(f"File too large: {file_size_mb:.2f} MB (max {self.max_file_size_mb} MB)")
            return None
        
        # Check file extension
        file_ext = file_path.suffix.lower().lstrip('.')
        if file_ext not in self.supported_formats:
            logger.error(f"Unsupported file format: {file_ext}")
            return None
        
        try:
            # Extract text based on file type
            if file_ext == 'pdf':
                if not PYMUPDF_AVAILABLE:
                    logger.error("PyMuPDF not available, cannot load PDF")
                    return None
                text, metadata = self._extract_pdf_text(file_path)
            elif file_ext == 'txt':
                text, metadata = self._extract_txt_text(file_path)
            elif file_ext == 'rtf':
                if not STRIPRTF_AVAILABLE:
                    logger.error("striprtf not available, cannot load RTF")
                    return None
                text, metadata = self._extract_rtf_text(file_path)
            else:
                logger.error(f"Unsupported file format: {file_ext}")
                return None
            
            # Generate document ID
            doc_id = str(uuid.uuid4())
            
            # Add file metadata
            metadata['filename'] = file_path.name
            metadata['file_path'] = str(file_path)
            metadata['file_size'] = file_path.stat().st_size
            metadata['file_type'] = file_ext
            metadata['timestamp'] = time.time()
            
            # Store document
            self.documents[doc_id] = {
                'id': doc_id,
                'text': text,
                'metadata': metadata
            }
            
            # Save documents to disk
            self._save_documents()
            
            logger.info(f"Loaded document: {file_path.name} (ID: {doc_id})")
            return doc_id
            
        except Exception as e:
            logger.error(f"Error loading document {file_path}: {str(e)}")
            return None
    
    def load_document_from_text(self, text: str, filename: str) -> Optional[str]:
        """
        Load a document from text content.
        
        Args:
            text: Document text content
            filename: Name for the document
            
        Returns:
            Document ID if successful, None otherwise
        """
        if not text:
            logger.error("Empty text content")
            return None
        
        try:
            # Generate document ID
            doc_id = str(uuid.uuid4())
            
            # Create metadata
            metadata = {
                'filename': filename,
                'file_size': len(text.encode('utf-8')),
                'file_type': 'txt',
                'timestamp': time.time(),
                'source': 'text_input'
            }
            
            # Store document
            self.documents[doc_id] = {
                'id': doc_id,
                'text': text,
                'metadata': metadata
            }
            
            # Save documents to disk
            self._save_documents()
            
            logger.info(f"Loaded document from text: {filename} (ID: {doc_id})")
            return doc_id
            
        except Exception as e:
            logger.error(f"Error loading document from text: {str(e)}")
            return None
    
    def _extract_pdf_text(self, file_path: Path) -> tuple[str, Dict[str, Any]]:
        """
        Extract text from a PDF file.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Tuple of (text_content, metadata)
        """
        if not PYMUPDF_AVAILABLE:
            raise ImportError("PyMuPDF not available")
        
        # Open PDF
        doc = fitz.open(file_path)
        
        # Extract metadata
        metadata = {
            'title': doc.metadata.get('title', ''),
            'author': doc.metadata.get('author', ''),
            'subject': doc.metadata.get('subject', ''),
            'keywords': doc.metadata.get('keywords', ''),
            'page_count': len(doc),
            'creation_date': doc.metadata.get('creationDate', '')
        }
        
        # Extract text from each page
        text_parts = []
        for i, page in enumerate(doc):
            text = page.get_text()
            text_parts.append(f"--- Page {i+1} ---\n{text}")
        
        # Combine text
        text = "\n\n".join(text_parts)
        
        # Close document
        doc.close()
        
        return text, metadata
    
    def _extract_txt_text(self, file_path: Path) -> tuple[str, Dict[str, Any]]:
        """
        Extract text from a text file.
        
        Args:
            file_path: Path to the text file
            
        Returns:
            Tuple of (text_content, metadata)
        """
        # Read text file
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            text = f.read()
        
        # Create metadata
        metadata = {
            'line_count': text.count('\n') + 1,
            'char_count': len(text),
            'word_count': len(text.split())
        }
        
        return text, metadata
    
    def _extract_rtf_text(self, file_path: Path) -> tuple[str, Dict[str, Any]]:
        """
        Extract text from an RTF file.
        
        Args:
            file_path: Path to the RTF file
            
        Returns:
            Tuple of (text_content, metadata)
        """
        if not STRIPRTF_AVAILABLE:
            raise ImportError("striprtf not available")
        
        # Read RTF file
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            rtf_content = f.read()
        
        # Convert RTF to plain text
        text = rtf_to_text(rtf_content)
        
        # Create metadata
        metadata = {
            'line_count': text.count('\n') + 1,
            'char_count': len(text),
            'word_count': len(text.split())
        }
        
        return text, metadata
    
    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a document by ID.
        
        Args:
            doc_id: Document ID
            
        Returns:
            Document dict or None if not found
        """
        return self.documents.get(doc_id)
    
    def get_document_text(self, doc_id: str) -> str:
        """
        Get the text content of a document.
        
        Args:
            doc_id: Document ID
            
        Returns:
            Document text content or empty string if not found
        """
        doc = self.get_document(doc_id)
        if doc:
            return doc.get('text', '')
        return ''
    
    def get_document_metadata(self, doc_id: str) -> Dict[str, Any]:
        """
        Get the metadata of a document.
        
        Args:
            doc_id: Document ID
            
        Returns:
            Document metadata or empty dict if not found
        """
        doc = self.get_document(doc_id)
        if doc:
            return doc.get('metadata', {})
        return {}
    
    def list_documents(self) -> List[Dict[str, Any]]:
        """
        List all loaded documents.
        
        Returns:
            List of document dicts with ID and metadata
        """
        docs = []
        for doc_id, doc in self.documents.items():
            docs.append({
                'id': doc_id,
                'metadata': doc.get('metadata', {})
            })
        return docs
    
    def delete_document(self, doc_id: str) -> bool:
        """
        Delete a document.
        
        Args:
            doc_id: Document ID
            
        Returns:
            True if deleted, False otherwise
        """
        if doc_id in self.documents:
            del self.documents[doc_id]
            self._save_documents()
            logger.info(f"Deleted document with ID: {doc_id}")
            return True
        return False
    
    def _save_documents(self):
        """Save documents to disk."""
        try:
            # Create serializable version
            serializable_docs = {}
            for doc_id, doc in self.documents.items():
                serializable_docs[doc_id] = {
                    'id': doc_id,
                    'text': doc['text'],
                    'metadata': doc['metadata']
                }
            
            # Save to file
            docs_file = self.storage_dir / 'documents.json'
            with open(docs_file, 'w') as f:
                json.dump(serializable_docs, f)
            
            logger.debug(f"Saved {len(serializable_docs)} documents to {docs_file}")
        except Exception as e:
            logger.error(f"Error saving documents: {str(e)}")
    
    def _load_documents(self):
        """Load documents from disk."""
        try:
            # Check if file exists
            docs_file = self.storage_dir / 'documents.json'
            if not docs_file.exists():
                logger.debug("No documents file found, starting with empty documents")
                return
            
            # Load from file
            with open(docs_file, 'r') as f:
                self.documents = json.load(f)
            
            logger.info(f"Loaded {len(self.documents)} documents from {docs_file}")
        except Exception as e:
            logger.error(f"Error loading documents: {str(e)}")
            self.documents = {}