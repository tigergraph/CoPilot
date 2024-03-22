from app.supportai.chunkers.base_chunker import BaseChunker

class CharacterChunker(BaseChunker):
    def __init__(self, chunk_size, overlap_size=0):
        if chunk_size <= overlap_size:
            raise ValueError("Chunk size must be larger than overlap size")
        self.chunk_size = chunk_size
        self.overlap_size = overlap_size

    def chunk(self, input_string):
        if self.chunk_size <= 0:
            return []

        chunks = []
        i = 0
        while i < len(input_string):
            chunk = input_string[i:i + self.chunk_size]
            chunks.append(chunk)

            i += self.chunk_size - self.overlap_size
            if i + self.overlap_size >= len(input_string):
                break
        return chunks
    
    def __call__(self, input_string):
        return self.chunk(input_string)