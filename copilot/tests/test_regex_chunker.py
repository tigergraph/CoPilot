import unittest
from common.chunkers.regex_chunker import RegexChunker


class TestRegexChunker(unittest.TestCase):
    def test_chunk_simple_pattern(self):
        """Test chunking with a simple pattern."""
        chunker = RegexChunker(r"\s+")
        doc = "This is a test document."
        expected_chunks = ["This", "is", "a", "test", "document."]
        self.assertEqual(chunker.chunk(doc), expected_chunks)

    def test_chunk_complex_pattern(self):
        """Test chunking with a more complex pattern."""
        chunker = RegexChunker(r"[,.!?]\s*")
        doc = "Hello, world! This is a test. A very simple test?"
        expected_chunks = ["Hello", "world", "This is a test", "A very simple test"]
        self.assertEqual(chunker.chunk(doc), expected_chunks)

    def test_chunk_with_no_matches(self):
        """Test chunking when there are no matches to the pattern."""
        chunker = RegexChunker(r"XYZ")
        doc = "This document does not contain the pattern."
        expected_chunks = ["This document does not contain the pattern."]
        self.assertEqual(chunker.chunk(doc), expected_chunks)

    def test_chunk_filter_empty_strings(self):
        """Test if empty strings are filtered out from the results."""
        chunker = RegexChunker(r"\s+")
        doc = "This  is   a test    document."
        expected_chunks = ["This", "is", "a", "test", "document."]
        self.assertEqual(chunker.chunk(doc), expected_chunks)


if __name__ == "__main__":
    unittest.main()
