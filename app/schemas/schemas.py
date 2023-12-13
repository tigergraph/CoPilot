from pydantic import BaseModel
from typing import Union, Annotated, List, Dict

class NaturalLanguageQuery(BaseModel):
    query:str

class GSQLQueryInfo(BaseModel):
    function_header: str
    description: str
    docstring: str
    param_types: dict = {}

class NaturalLanguageQueryResponse(BaseModel):
    natural_language_response: str
    answered_question: bool
    query_sources: Dict = None