from langchain.pydantic_v1 import BaseModel, Field
from typing import Optional
from langchain_community.graphs.graph_document import (
    Node as BaseNode,
    Relationship as BaseRelationship,
)
from typing import List, Dict, Type


class MapQuestionToSchemaResponse(BaseModel):
    question: str = Field(
        description="The question restated in terms of the graph schema"
    )
    target_vertex_types: List[str] = Field(
        description="The list of vertices mentioned in the question. If there are no vertices mentioned, then use an empty list."
    )
    target_vertex_attributes: Optional[Dict[str, List[str]]] = Field(
        description="The dictionary of vertex attributes mentioned in the question, formated in {'vertex_type_1': ['vertex_attribute_1', 'vertex_attribute_2'], 'vertex_type_2': ['vertex_attribute_1', 'vertex_attribute_2']}"
    )
    target_vertex_ids: Optional[Dict[str, List[str]]] = Field(
        description="The dictionary of vertex ids mentioned in the question. If there are no vertex ids mentioned, then use an empty dict. formated in {'vertex_type_1': ['vertex_id_1', 'vertex_id_2'], 'vertex_type_2': ['vertex_id_1', 'vertex_id_2']}"
    )
    target_edge_types: Optional[List[str]] = Field(
        description="The list of edges mentioned in the question"
    )
    target_edge_attributes: Optional[Dict[str, List[str]]] = Field(
        description="The dictionary of edge attributes mentioned in the question, formated in {'edge_type': ['edge_attribute_1', 'edge_attribute_2']}"
    )


class AgentOutput(BaseModel):
    answer: str = Field(description="Natural language answer generated")
    function_call: str = Field(description="Function call used to generate answer")


class MapAttributeToAttributeResponse(BaseModel):
    attr_map: Optional[Dict[str, str]] = Field(
        description="The dictionary of the form {'source_attribute': 'output_attribute'}"
    )


class GenerateFunctionResponse(BaseModel):
    connection_func_call: str = Field(
        description="The function call to make to answer the question. Must start with conn."
    )
    func_call_reasoning: str = Field(
        description="The reason why the function call was generated to answer the question."
    )


class Node(BaseNode):
    node_type: str = Field(
        description="Type of the node. Describe what the entity is. Ensure you use basic or elementary types for node labels.\n"
        "For example, when you identify an entity representing a person, "
        "always label it as 'Person'. Avoid using more specific terms "
        "like 'Mathematician' or 'Scientist'"
    )
    definition: str = Field(
        description="Definition of the node. Describe what the entity is."
    )


class Relationship(BaseRelationship):
    relation_type: str = Field(
        description="Type of the relationship. Describe what the relationship is. Instead of using specific and momentary types such as "
        "'BECAME_PROFESSOR', use more general and timeless relationship types like "
        "'PROFESSOR'. However, do not sacrifice any accuracy for generality"
    )
    source: Node = Field(description="The source node of the relationship.")
    target: Node = Field(description="The target node of the relationship.")
    definition: str = Field(
        description="Definition of the relationship. Describe what the relationship is."
    )


class KnowledgeGraph(BaseModel):
    """Generate a knowledge graph with entities and relationships."""

    nodes: List[Node] = Field(..., description="List of nodes in the knowledge graph")
    rels: List[Relationship] = Field(
        ..., description="List of relationships in the knowledge graph"
    )

class ReportQuestion(BaseModel):
    question: str = Field("The question to be asked")
    reasoning: str = Field("The reasoning behind the question")

class ReportSection(BaseModel):
    section: str = Field("Name of the section")
    description: str = Field("Description of the section")
    questions: List[ReportQuestion] = Field("List of questions and reasoning for the section")

class ReportSections(BaseModel):
    sections: List[ReportSection] = Field("List of sections for the report")