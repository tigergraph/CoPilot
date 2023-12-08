from pydantic import BaseModel
from typing import Union, Annotated, List, Dict

class NaturalLanguageQuery(BaseModel):
    query:str

class GSQLQueryInfo(BaseModel):
    query_name: str
    query_description: str
    heavy_runtime_warning: bool = False

class NaturalLanguageQueryResponse(BaseModel):
    natural_language_response: str
    answered_question: bool
    query_sources: Dict = None