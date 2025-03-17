"""
Unit tests for the token counter utility.
"""
import unittest
from local_ai_assistant.utils.token_counter import TokenCounter

class TestTokenCounter(unittest.TestCase):
    """Test cases for the TokenCounter class."""
    
    def setUp(self):
        """Set up the test cases."""
        self.token_counter = TokenCounter()
        self.test_text = "This is a test sentence to count tokens. It should have more than 10 tokens."
    
    def test_heuristic_counting(self):
        """Test the heuristic token counting method."""
        # Test with the heuristic method
        count = self.token_counter._count_tokens_heuristic(self.test_text)
        self.assertGreater(count, 10)  # Should be more than 10 tokens
        
    def test_truncation(self):
        """Test the text truncation functionality."""
        # Test truncation with a very small limit
        truncated = self.token_counter.truncate_to_token_limit(self.test_text, 5)
        self.assertLess(len(truncated), len(self.test_text))
        
        # Test truncation with a limit larger than the text
        large_limit = 1000
        truncated = self.token_counter.truncate_to_token_limit(self.test_text, large_limit)
        self.assertEqual(truncated, self.test_text)
    
    def test_model_specific_counting(self):
        """Test counting tokens for specific models."""
        # Test counting with different models
        gpt_count = self.token_counter.count_tokens(self.test_text, "gpt-3.5-turbo")
        llama_count = self.token_counter.count_tokens(self.test_text, "llama")
        gemma_count = self.token_counter.count_tokens(self.test_text, "gemma")
        
        # All counts should be positive
        self.assertGreaterEqual(gpt_count, 0)
        self.assertGreaterEqual(llama_count, 0)
        self.assertGreaterEqual(gemma_count, 0)

if __name__ == "__main__":
    unittest.main() 