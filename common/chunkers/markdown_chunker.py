from common.chunkers.base_chunker import BaseChunker
from langchain_text_splitters import (
    Language,
    RecursiveCharacterTextSplitter
)

class MarkdownChunker(BaseChunker):
    
    def __init__(
        self,
        chunk_size: int = 1024,
        chunk_overlap: int = 0
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk(self, input_string):
        md_splitter = RecursiveCharacterTextSplitter.from_language(
            language=Language.MARKDOWN, chunk_size=self.chunk_size, chunk_overlap=self.chunk_overlap
        )
        md_chunks = md_splitter.create_documents([input_string])

        return [x.page_content for x in md_chunks]

    def __call__(self, input_string):
        return self.chunk(input_string)
