import unittest
from app.supportai.chunkers.character_chunker import CharacterChunker


class TestCharacterChunker(unittest.TestCase):
    def test_chunk_without_overlap(self):
        """Test chunking without overlap."""
        chunker = CharacterChunker(chunk_size=4)
        input_string = "abcdefghijkl"
        expected_chunks = ["abcd", "efgh", "ijkl"]
        self.assertEqual(chunker.chunk(input_string), expected_chunks)

    def test_chunk_with_overlap(self):
        """Test chunking with overlap."""
        chunker = CharacterChunker(chunk_size=4, overlap_size=2)
        input_string = "abcdefghijkl"
        expected_chunks = ["abcd", "cdef", "efgh", "ghij", "ijkl"]
        self.assertEqual(chunker.chunk(input_string), expected_chunks)

    def test_chunk_with_overlap_and_uneven(self):
        """Test chunking with overlap."""
        chunker = CharacterChunker(chunk_size=4, overlap_size=2)
        input_string = "abcdefghijklm"
        expected_chunks = ["abcd", "cdef", "efgh", "ghij", "ijkl", "klm"]
        self.assertEqual(chunker.chunk(input_string), expected_chunks)

    def test_empty_input_string(self):
        """Test handling of an empty input string."""
        chunker = CharacterChunker(chunk_size=4, overlap_size=2)
        input_string = ""
        expected_chunks = []
        self.assertEqual(chunker.chunk(input_string), expected_chunks)

    def test_input_shorter_than_chunk_size(self):
        """Test input string shorter than chunk size."""
        chunker = CharacterChunker(chunk_size=10)
        input_string = "abc"
        expected_chunks = ["abc"]
        self.assertEqual(chunker.chunk(input_string), expected_chunks)

    def test_last_chunk_shorter_than_chunk_size(self):
        """Test when the last chunk is shorter than the chunk size."""
        chunker = CharacterChunker(chunk_size=4, overlap_size=1)
        input_string = "abcdefghijklm"
        expected_chunks = ["abcd", "defg", "ghij", "jklm"]
        self.assertEqual(chunker.chunk(input_string), expected_chunks)

    def test_chunk_size_equals_overlap_size(self):
        """Test when chunk size equals overlap size."""
        with self.assertRaises(ValueError):
            CharacterChunker(chunk_size=4, overlap_size=4)

    def test_overlap_larger_than_chunk_should_raise_error(self):
        """Test initialization with overlap size larger than chunk size should raise an error."""
        with self.assertRaises(ValueError):
            CharacterChunker(chunk_size=3, overlap_size=4)

    def test_chunk_size_zero_should_raise_error(self):
        """Test initialization with a chunk size of zero should raise an error."""
        with self.assertRaises(ValueError):
            CharacterChunker(chunk_size=0, overlap_size=0)

    def test_chunk_size_negative_should_raise_error(self):
        """Test initialization with a negative chunk size."""
        with self.assertRaises(ValueError):
            CharacterChunker(chunk_size=-1)


if __name__ == "__main__":
    unittest.main()
