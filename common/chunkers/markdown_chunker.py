from common.chunkers.base_chunker import BaseChunker
from common.chunkers.semantic_chunker import SemanticChunker
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter
)

class MarkdownChunker(BaseChunker):
    chunker = None
    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
        ("###", "Header 3"),
        ("####", "Header 4"),
    ]
    
    def __init__(
        self,
        chunker: SemanticChunker
    ):
        self.chunker = chunker

    def chunk(self, input_string):
        md_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=self.headers_to_split_on, strip_headers=False
        )

        md_chunks = md_splitter.split_text(input_string)

        chunks = self.chunker.split_documents(md_chunks)

        return [x.page_content for x in chunks]

    def __call__(self, input_string):
        return self.chunk(input_string)
