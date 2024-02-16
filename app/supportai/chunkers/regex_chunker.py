from app.supportai.chunkers.base_chunker import BaseChunker
import re
from typing import List

class RegexChunker(BaseChunker):
    def __init__(self, pattern:str):
        super().__init__()
        self.pattern = re.compile(pattern)

    def chunk(self, doc) -> List[str]:
        '''Split a document using a regex pattern.
           Returns a list of strings that are split by the pattern.
        '''
        res = self.pattern.split(doc)
        return list(filter(None, res))
    
    def __call__(self, doc):
        return self.chunk(doc)