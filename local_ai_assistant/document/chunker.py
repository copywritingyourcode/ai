"""
Document chunker module for splitting documents into manageable chunks.

This module provides functions to split documents into smaller chunks
for more effective embedding and retrieval.
"""

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple
import yaml

# Local imports
from local_ai_assistant.utils.token_counter import (
    count_tokens, 
    truncate_text_to_token_limit,
    estimate_tokens_from_chunk_count
)


# Logger for this module
logger = logging.getLogger(__name__)


class DocumentChunker:
    """
    Splits documents into smaller chunks for processing.
    
    Uses various strategies to split text into chunks while preserving
    semantic coherence and minimizing context fragmentation.
    """
    
    def __init__(self, config_path: Union[str, Path]):
        """
        Initialize the document chunker.
        
        Args:
            config_path: Path to the configuration file
        """
        self.config_path = Path(config_path)
        
        # Load configuration
        with open(self.config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # Extract document settings
        doc_config = self.config['document']
        
        # Chunk settings
        self.chunk_size = doc_config['chunk_size']
        self.chunk_overlap = doc_config['chunk_overlap']
        
        # Model for token counting
        self.model_name = self.config['models']['default']
        
        logger.info(f"Document chunker initialized, chunk size: {self.chunk_size} tokens, overlap: {self.chunk_overlap} tokens")
    
    def chunk_text(self, text: str) -> List[Dict[str, Any]]:
        """
        Split text into chunks.
        
        Args:
            text: Text to split
            
        Returns:
            List of chunk dicts with text and metadata
        """
        if not text:
            logger.warning("Empty text passed to chunker")
            return []
        
        # Choose splitting strategy based on text content
        if self._is_structured_document(text):
            # Use a structured approach (by sections/pages)
            chunks = self._split_by_structure(text)
        else:
            # Use a simple recursive approach
            chunks = self._split_by_recursive(text)
        
        # Log chunking results
        logger.debug(f"Chunked text into {len(chunks)} chunks")
        
        return chunks
    
    def _is_structured_document(self, text: str) -> bool:
        """
        Check if the text appears to have clear structural elements.
        
        Args:
            text: Text to analyze
            
        Returns:
            True if the text has clear structure, False otherwise
        """
        # Check for page markers (common in PDF extractions)
        if re.search(r'Page \d+:', text):
            return True
        
        # Check for section headers (multiple instances)
        section_pattern = r'(?:\n|^)(#+\s+|\d+\.\s+)[A-Z]'
        if len(re.findall(section_pattern, text)) > 2:
            return True
        
        # Check for markdown or other common structured formats
        if text.count('##') > 3 or text.count('# ') > 3:
            return True
        
        return False
    
    def _split_by_structure(self, text: str) -> List[Dict[str, Any]]:
        """
        Split text using structural elements like pages, sections, etc.
        
        Args:
            text: Text to split
            
        Returns:
            List of chunk dicts
        """
        chunks = []
        
        # Try splitting by pages first
        page_pattern = r'(Page \d+:[\s\S]*?)(?=Page \d+:|$)'
        pages = re.findall(page_pattern, text)
        
        if pages:
            # Process each page
            for i, page_text in enumerate(pages):
                # Get page number from the text if available
                page_match = re.search(r'Page (\d+):', page_text)
                page_num = int(page_match.group(1)) if page_match else i + 1
                
                # Check if the page is too large and needs further splitting
                page_tokens = count_tokens(page_text, self.model_name)
                
                if page_tokens > self.chunk_size:
                    # Page is too large, split further
                    sub_chunks = self._split_by_recursive(page_text)
                    
                    # Add page metadata to sub-chunks
                    for j, sub_chunk in enumerate(sub_chunks):
                        sub_chunk['metadata']['page'] = page_num
                        sub_chunk['metadata']['sub_chunk'] = j + 1
                        chunks.append(sub_chunk)
                else:
                    # Page fits within chunk size
                    chunks.append({
                        'text': page_text,
                        'metadata': {
                            'page': page_num,
                            'tokens': page_tokens
                        }
                    })
        else:
            # No page structure, try sections
            section_pattern = r'(?:^|\n)(#+\s+[^\n]+|[\d\.]+\s+[^\n]+)(?:\n|$)'
            sections = re.split(section_pattern, text)
            
            # If we have a reasonable number of sections
            if len(sections) > 1:
                current_chunk = ""
                current_tokens = 0
                section_titles = []
                
                # Process each section
                for i, section in enumerate(sections):
                    if not section.strip():
                        continue
                    
                    # Check if this is a section title
                    if re.match(r'^#+\s+|^[\d\.]+\s+', section):
                        section_titles.append(section.strip())
                        continue
                    
                    section_tokens = count_tokens(section, self.model_name)
                    
                    # If adding this section would exceed chunk size, store current chunk
                    if current_tokens + section_tokens > self.chunk_size and current_chunk:
                        chunks.append({
                            'text': current_chunk,
                            'metadata': {
                                'sections': section_titles.copy(),
                                'tokens': current_tokens
                            }
                        })
                        
                        # Reset chunk, but maintain some overlap
                        overlap_point = self._find_overlap_point(current_chunk)
                        current_chunk = current_chunk[overlap_point:] if overlap_point >= 0 else ""
                        current_tokens = count_tokens(current_chunk, self.model_name)
                    
                    # Add section to current chunk
                    if section_titles:
                        current_chunk += "\n\n" + section_titles[-1] + "\n\n" + section
                    else:
                        current_chunk += ("\n\n" if current_chunk else "") + section
                    
                    current_tokens = count_tokens(current_chunk, self.model_name)
                
                # Add final chunk if not empty
                if current_chunk.strip():
                    chunks.append({
                        'text': current_chunk,
                        'metadata': {
                            'sections': section_titles.copy(),
                            'tokens': current_tokens
                        }
                    })
            else:
                # No clear sections, fall back to recursive splitting
                chunks = self._split_by_recursive(text)
        
        return chunks
    
    def _split_by_recursive(self, text: str) -> List[Dict[str, Any]]:
        """
        Split text recursively by paragraphs, sentences, etc.
        
        Args:
            text: Text to split
            
        Returns:
            List of chunk dicts
        """
        chunks = []
        
        # Count total tokens
        total_tokens = count_tokens(text, self.model_name)
        
        # If text fits in one chunk, return it
        if total_tokens <= self.chunk_size:
            return [{
                'text': text,
                'metadata': {
                    'tokens': total_tokens
                }
            }]
        
        # Split by paragraphs first (double newlines)
        paragraphs = re.split(r'\n\s*\n', text)
        
        current_chunk = ""
        current_tokens = 0
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            para_tokens = count_tokens(para, self.model_name)
            
            # If paragraph alone exceeds chunk size, split it
            if para_tokens > self.chunk_size:
                # First, add current chunk if not empty
                if current_chunk:
                    chunks.append({
                        'text': current_chunk,
                        'metadata': {
                            'tokens': current_tokens
                        }
                    })
                    current_chunk = ""
                    current_tokens = 0
                
                # Split paragraph by sentences
                sentences = re.split(r'(?<=[.!?])\s+', para)
                
                current_para_chunk = ""
                current_para_tokens = 0
                
                for sentence in sentences:
                    sentence = sentence.strip()
                    if not sentence:
                        continue
                    
                    sentence_tokens = count_tokens(sentence, self.model_name)
                    
                    # If sentence alone exceeds chunk size, split it (rare case)
                    if sentence_tokens > self.chunk_size:
                        # First, add current para chunk if not empty
                        if current_para_chunk:
                            chunks.append({
                                'text': current_para_chunk,
                                'metadata': {
                                    'tokens': current_para_tokens
                                }
                            })
                            current_para_chunk = ""
                            current_para_tokens = 0
                        
                        # Split sentence into fixed-size chunks
                        sentence_chunks = self._split_by_token_limit(sentence)
                        chunks.extend(sentence_chunks)
                        
                    # If adding this sentence would exceed chunk size
                    elif current_para_tokens + sentence_tokens > self.chunk_size:
                        # Add current para chunk
                        chunks.append({
                            'text': current_para_chunk,
                            'metadata': {
                                'tokens': current_para_tokens
                            }
                        })
                        
                        # Start new para chunk with this sentence
                        current_para_chunk = sentence
                        current_para_tokens = sentence_tokens
                        
                    else:
                        # Add sentence to current para chunk
                        separator = " " if current_para_chunk else ""
                        current_para_chunk += separator + sentence
                        current_para_tokens = count_tokens(current_para_chunk, self.model_name)
                
                # Add final para chunk if not empty
                if current_para_chunk:
                    chunks.append({
                        'text': current_para_chunk,
                        'metadata': {
                            'tokens': current_para_tokens
                        }
                    })
                
            # If adding this paragraph would exceed chunk size
            elif current_tokens + para_tokens > self.chunk_size:
                # Add current chunk
                chunks.append({
                    'text': current_chunk,
                    'metadata': {
                        'tokens': current_tokens
                    }
                })
                
                # Start new chunk with this paragraph
                current_chunk = para
                current_tokens = para_tokens
                
            else:
                # Add paragraph to current chunk
                separator = "\n\n" if current_chunk else ""
                current_chunk += separator + para
                current_tokens = count_tokens(current_chunk, self.model_name)
        
        # Add final chunk if not empty
        if current_chunk:
            chunks.append({
                'text': current_chunk,
                'metadata': {
                    'tokens': current_tokens
                }
            })
        
        return chunks
    
    def _split_by_token_limit(self, text: str) -> List[Dict[str, Any]]:
        """
        Split text into chunks of fixed token size.
        
        Args:
            text: Text to split
            
        Returns:
            List of chunk dicts
        """
        chunks = []
        
        # Calculate total tokens
        total_tokens = count_tokens(text, self.model_name)
        
        # If text fits in one chunk, return it
        if total_tokens <= self.chunk_size:
            return [{
                'text': text,
                'metadata': {
                    'tokens': total_tokens
                }
            }]
        
        # Calculate how many chunks we need (considering overlap)
        effective_chunk_size = self.chunk_size - self.chunk_overlap
        num_chunks = (total_tokens + effective_chunk_size - 1) // effective_chunk_size
        
        for i in range(num_chunks):
            # Calculate start and end positions for this chunk
            start_pos = i * effective_chunk_size
            end_pos = min(start_pos + self.chunk_size, total_tokens)
            
            # Get the chunk text
            chunk_text = truncate_text_to_token_limit(
                text, 
                end_pos - start_pos, 
                self.model_name
            )
            
            # Count actual tokens (might be slightly different due to tokenization)
            chunk_tokens = count_tokens(chunk_text, self.model_name)
            
            chunks.append({
                'text': chunk_text,
                'metadata': {
                    'chunk_index': i,
                    'tokens': chunk_tokens
                }
            })
        
        return chunks
    
    def _find_overlap_point(self, text: str) -> int:
        """
        Find a suitable point for overlap based on token count.
        
        Args:
            text: Text to analyze
            
        Returns:
            Character position where overlap should start
        """
        if not text:
            return -1
        
        # Aim for the configured overlap token count
        target_token_count = self.chunk_overlap
        
        # Get total tokens
        total_tokens = count_tokens(text, self.model_name)
        
        # If text has fewer tokens than overlap, return start of text
        if total_tokens <= target_token_count:
            return 0
        
        # Try to find a paragraph break in the latter part of the text
        text_length = len(text)
        approx_chars_per_token = text_length / total_tokens
        
        # Estimate character position for overlap
        char_pos = int(text_length - (target_token_count * approx_chars_per_token))
        
        # Look for paragraph break after this position
        para_match = re.search(r'\n\s*\n', text[char_pos:])
        if para_match:
            return char_pos + para_match.start()
        
        # Look for sentence break if no paragraph break
        sentence_match = re.search(r'(?<=[.!?])\s+', text[char_pos:])
        if sentence_match:
            return char_pos + sentence_match.start()
        
        # Fall back to character position
        return max(0, char_pos)
    
    def get_optimal_chunk_size(self, text: str, target_chunks: int = 10) -> int:
        """
        Calculate an optimal chunk size to achieve a target number of chunks.
        
        Args:
            text: Text to analyze
            target_chunks: Desired number of chunks
            
        Returns:
            Recommended chunk size in tokens
        """
        total_tokens = count_tokens(text, self.model_name)
        
        # If text is small, just use default chunk size
        if total_tokens <= self.chunk_size:
            return self.chunk_size
        
        # Calculate chunk size to achieve target_chunks
        chunk_size = total_tokens // target_chunks
        
        # Add a bit of margin for overlap
        chunk_size = int(chunk_size * 1.2)
        
        # Ensure it's not too small
        return max(100, chunk_size) 