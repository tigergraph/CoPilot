from langchain.pydantic_v1 import BaseModel, Field
from typing import List, Dict, Type

class MapQuestionToSchemaResponse(BaseModel):
    question: str = Field(description="The question restated in terms of the graph schema")
    target_vertex_types: List[str] = Field(description="The list of vertices mentioned in the question. If there are no vertices mentioned, then use an empty list.")
    target_vertex_attributes: Dict[str, List[str]] = Field(description="The dictionary of vertex attributes mentioned in the question, formated in {'vertex_type_1': ['vertex_attribute_1', 'vertex_attribute_2'], 'vertex_type_2': ['vertex_attribute_1', 'vertex_attribute_2']}")
    target_vertex_ids: Dict[str, List[str]] = Field(description="The dictionary of vertex ids mentioned in the question, formated in {'vertex_type_1': ['vertex_id_1', 'vertex_id_2'], 'vertex_type_2': ['vertex_id_1', 'vertex_id_2']}")
    target_edge_types: List[str] = Field(description="The list of edges mentioned in the question. ")
    target_edge_attributes: Dict[str, List[str]] = Field(description="The dictionary of edge attributes mentioned in the question, formated in {'edge_type': ['edge_attribute_1', 'edge_attribute_2']}")

class AgentOutput(BaseModel):
    answer: str = Field(description="Natural language answer generated")
    function_call: str = Field(description="Function call used to generate answer")