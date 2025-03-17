"""
Unit tests for the document loader.
"""
import os
import unittest
import tempfile
import uuid
import yaml
from pathlib import Path
from local_ai_assistant.document.loader import DocumentLoader

class TestDocumentLoader(unittest.TestCase):
    """Test cases for the DocumentLoader class."""
    
    def setUp(self):
        """Set up the test cases."""
        # Create a temporary directory for test documents
        self.temp_dir = tempfile.TemporaryDirectory()
        self.doc_dir = Path(self.temp_dir.name)
        
        # Create storage directories
        self.storage_dir = self.doc_dir / "documents"
        self.storage_dir.mkdir(exist_ok=True)
        
        # Create a config file
        self.config_file = self.doc_dir / "config.yaml"
        config = {
            "document": {
                "storage_dir": str(self.storage_dir),
                "supported_formats": ["pdf", "txt"],
                "max_file_size_mb": 50
            }
        }
        with open(self.config_file, "w") as f:
            yaml.dump(config, f)
        
        # Initialize the document loader
        self.loader = DocumentLoader(self.config_file)
        
        # Create a test text file
        self.text_file = self.doc_dir / "test.txt"
        with open(self.text_file, "w") as f:
            f.write("This is a test document for testing the document loader.")
    
    def tearDown(self):
        """Clean up after tests."""
        self.temp_dir.cleanup()
    
    def test_load_text_file(self):
        """Test loading a text file."""
        doc_id = self.loader.load_document(str(self.text_file))
        self.assertIsNotNone(doc_id)
        
        # Check that the document is in the loaded documents
        self.assertIn(doc_id, self.loader.documents)
        
        # Check that the document has content
        doc = self.loader.documents[doc_id]
        self.assertIn("text", doc)
        self.assertIn("This is a test document", doc["text"])
    
    def test_load_from_text(self):
        """Test loading from text content."""
        text = "This is direct text content for testing."
        doc_id = self.loader.load_document_from_text(text, "test_content")
        self.assertIsNotNone(doc_id)
        
        # Check that the document is in the loaded documents
        self.assertIn(doc_id, self.loader.documents)
        
        # Check that the document has the correct content and name
        doc = self.loader.documents[doc_id]
        self.assertEqual(doc["text"], text)
        self.assertEqual(doc["metadata"]["filename"], "test_content")
    
    def test_save_and_load_documents(self):
        """Test saving and loading documents."""
        # Load a document
        doc_id = self.loader.load_document(str(self.text_file))
        
        # Save documents to disk (this is called automatically by load_document)
        self.loader._save_documents()
        
        # Create a new loader and load documents from disk
        new_loader = DocumentLoader(self.config_file)
        new_loader._load_documents()
        
        # Check that the document was loaded
        self.assertIn(doc_id, new_loader.documents)
        
        # Check that the document has the same content
        original_doc = self.loader.documents[doc_id]
        loaded_doc = new_loader.documents[doc_id]
        self.assertEqual(original_doc["text"], loaded_doc["text"])
        self.assertEqual(original_doc["metadata"]["filename"], loaded_doc["metadata"]["filename"])

if __name__ == "__main__":
    unittest.main() 