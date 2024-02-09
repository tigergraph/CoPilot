from app.chunkers.base_chunker import BaseChunker

class CharacterChunker(BaseChunker):
    def __init__(self, chunk_size, overlap_size = 0):
        self.chunk_size = chunk_size
        self.overlap_size = overlap_size

    def chunk_string_with_overlap(self, input_string):
        chunks = []
        for i in range(0, len(input_string) - self.chunk_size + 1, self.chunk_size - self.overlap_size):
            chunk = input_string[i:i + self.chunk_size]
            chunks.append(chunk)
        return chunks