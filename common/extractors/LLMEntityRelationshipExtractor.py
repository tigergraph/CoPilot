import json
from typing import List

from common.extractors.BaseExtractor import BaseExtractor
from common.llm_services import LLM_Model
from common.py_schemas import KnowledgeGraph
from langchain_community.graphs.graph_document import Node, Relationship, GraphDocument
from langchain_core.documents import Document

class LLMEntityRelationshipExtractor(BaseExtractor):
    def __init__(
        self,
        llm_service: LLM_Model,
        allowed_entity_types: List[str] = None,
        allowed_relationship_types: List[str] = None,
        strict_mode: bool = False,
    ):
        self.llm_service = llm_service
        self.allowed_vertex_types = allowed_entity_types
        self.allowed_edge_types = allowed_relationship_types
        self.strict_mode = strict_mode

    async def _aextract_kg_from_doc(self, doc, chain, parser) -> list[GraphDocument]:
        try:
            out = await chain.ainvoke(
                {"input": doc, "format_instructions": parser.get_format_instructions()}
            )
        except Exception as e:
            return [GraphDocument(nodes=[], relationships=[], source=Document(page_content=doc))]
        try:
            if "```json" not in out.content:
                json_out = json.loads(out.content.strip("content="))
            else:
                json_out = json.loads(
                    out.content.split("```")[1].strip("```").strip("json").strip()
                )

            formatted_rels = []
            for rels in json_out["rels"]:
                if isinstance(rels["source"], str) and isinstance(rels["target"], str):
                    formatted_rels.append(
                        {
                            "source": rels["source"],
                            "target": rels["target"],
                            "type": rels["relation_type"].replace(" ", "_").upper(),
                            "definition": rels["definition"],
                        }
                    )
                elif isinstance(rels["source"], dict) and isinstance(
                    rels["target"], str
                ):
                    formatted_rels.append(
                        {
                            "source": rels["source"]["id"],
                            "target": rels["target"],
                            "type": rels["relation_type"].replace(" ", "_").upper(),
                            "definition": rels["definition"],
                        }
                    )
                elif isinstance(rels["source"], str) and isinstance(
                    rels["target"], dict
                ):
                    formatted_rels.append(
                        {
                            "source": rels["source"],
                            "target": rels["target"]["id"],
                            "type": rels["relation_type"].replace(" ", "_").upper(),
                            "definition": rels["definition"],
                        }
                    )
                elif isinstance(rels["source"], dict) and isinstance(
                    rels["target"], dict
                ):
                    formatted_rels.append(
                        {
                            "source": rels["source"]["id"],
                            "target": rels["target"]["id"],
                            "type": rels["relation_type"].replace(" ", "_").upper(),
                            "definition": rels["definition"],
                        }
                    )
                else:
                    raise Exception("Relationship parsing error")
            formatted_nodes = []
            for node in json_out["nodes"]:
                formatted_nodes.append(
                    {
                        "id": node["id"],
                        "type": node["node_type"].replace(" ", "_").capitalize(),
                        "definition": node["definition"],
                    }
                )

            # filter relationships and nodes based on allowed types
            if self.strict_mode:
                if self.allowed_vertex_types:
                    formatted_nodes = [
                        node
                        for node in formatted_nodes
                        if node["type"] in self.allowed_vertex_types
                    ]
                if self.allowed_edge_types:
                    formatted_rels = [
                        rel
                        for rel in formatted_rels
                        if rel["type"] in self.allowed_edge_types
                    ]
        
            nodes = []
            for node in formatted_nodes:
                nodes.append(Node(id=node["id"],
                                  type=node["type"],
                                  properties={"description": node["definition"]}))
            relationships = []
            for rel in formatted_rels:
                relationships.append(Relationship(source=Node(id=rel["source"], type=rel["source"],
                                                  properties={"description": rel["definition"]}),
                                                  target=Node(id=rel["target"], type=rel["target"],
                                                  properties={"description": rel["definition"]}), type=rel["type"]))

            return [GraphDocument(nodes=nodes, relationships=relationships, source=Document(page_content=doc))]

        except:
            return [GraphDocument(nodes=[], relationships=[], source=Document(page_content=doc))]
        
    def _extract_kg_from_doc(self, doc, chain, parser) -> list[GraphDocument]:
        try:
            out = chain.invoke(
                {"input": doc, "format_instructions": parser.get_format_instructions()}
            )
        except Exception as e:
            return [GraphDocument(nodes=[], relationships=[], source=Document(page_content=doc))]
        try:
            if "```json" not in out.content:
                json_out = json.loads(out.content.strip("content="))
            else:
                json_out = json.loads(
                    out.content.split("```")[1].strip("```").strip("json").strip()
                )

            formatted_rels = []
            for rels in json_out["rels"]:
                if isinstance(rels["source"], str) and isinstance(rels["target"], str):
                    formatted_rels.append(
                        {
                            "source": rels["source"],
                            "target": rels["target"],
                            "type": rels["relation_type"].replace(" ", "_").upper(),
                            "definition": rels["definition"],
                        }
                    )
                elif isinstance(rels["source"], dict) and isinstance(
                    rels["target"], str
                ):
                    formatted_rels.append(
                        {
                            "source": rels["source"]["id"],
                            "target": rels["target"],
                            "type": rels["relation_type"].replace(" ", "_").upper(),
                            "definition": rels["definition"],
                        }
                    )
                elif isinstance(rels["source"], str) and isinstance(
                    rels["target"], dict
                ):
                    formatted_rels.append(
                        {
                            "source": rels["source"],
                            "target": rels["target"]["id"],
                            "type": rels["relation_type"].replace(" ", "_").upper(),
                            "definition": rels["definition"],
                        }
                    )
                elif isinstance(rels["source"], dict) and isinstance(
                    rels["target"], dict
                ):
                    formatted_rels.append(
                        {
                            "source": rels["source"]["id"],
                            "target": rels["target"]["id"],
                            "type": rels["relation_type"].replace(" ", "_").upper(),
                            "definition": rels["definition"],
                        }
                    )
                else:
                    raise Exception("Relationship parsing error")
            formatted_nodes = []
            for node in json_out["nodes"]:
                formatted_nodes.append(
                    {
                        "id": node["id"],
                        "type": node["node_type"].replace(" ", "_").capitalize(),
                        "definition": node["definition"],
                    }
                )

            # filter relationships and nodes based on allowed types
            if self.strict_mode:
                if self.allowed_vertex_types:
                    formatted_nodes = [
                        node
                        for node in formatted_nodes
                        if node["type"] in self.allowed_vertex_types
                    ]
                if self.allowed_edge_types:
                    formatted_rels = [
                        rel
                        for rel in formatted_rels
                        if rel["type"] in self.allowed_edge_types
                    ]
        
            nodes = []
            for node in formatted_nodes:
                nodes.append(Node(id=node["id"],
                                  type=node["type"],
                                  properties={"description": node["definition"]}))
            relationships = []
            for rel in formatted_rels:
                relationships.append(Relationship(source=Node(id=rel["source"], type=rel["source"],
                                                  properties={"description": rel["definition"]}),
                                                  target=Node(id=rel["target"], type=rel["target"],
                                                  properties={"description": rel["definition"]}), type=rel["type"]))

            return [GraphDocument(nodes=nodes, relationships=relationships, source=Document(page_content=doc))]

        except:
            return [GraphDocument(nodes=[], relationships=[], source=Document(page_content=doc))]
        
    async def adocument_er_extraction(self, document):
        from langchain.prompts import ChatPromptTemplate
        from langchain.output_parsers import PydanticOutputParser

    
        parser = PydanticOutputParser(pydantic_object=KnowledgeGraph)
        prompt = [
            ("system", self.llm_service.entity_relationship_extraction_prompt),
            (
                "human",
                "Tip: Make sure to answer in the correct format and do "
                "not include any explanations. "
                "Use the given format to extract information from the "
                "following input: {input}",
            ),
            (
                "human",
                "Mandatory: Make sure to answer in the correct format, specified here: {format_instructions}",
            ),
        ]
        if self.allowed_vertex_types or self.allowed_edge_types:
            prompt.append(
                (
                    "human",
                    "Tip: Make sure to use the following types if they are applicable. "
                    "If the input does not contain any of the types, you may create your own.",
                )
            )
        if self.allowed_vertex_types:
            prompt.append(("human", f"Allowed Node Types: {self.allowed_vertex_types}"))
        if self.allowed_edge_types:
            prompt.append(("human", f"Allowed Edge Types: {self.allowed_edge_types}"))
        prompt = ChatPromptTemplate.from_messages(prompt)
        chain = prompt | self.llm_service.model  # | parser
        er = await self._aextract_kg_from_doc(document, chain, parser)
        return er


    def document_er_extraction(self, document):
        from langchain.prompts import ChatPromptTemplate
        from langchain.output_parsers import PydanticOutputParser

    
        parser = PydanticOutputParser(pydantic_object=KnowledgeGraph)
        prompt = [
            ("system", self.llm_service.entity_relationship_extraction_prompt),
            (
                "human",
                "Tip: Make sure to answer in the correct format and do "
                "not include any explanations. "
                "Use the given format to extract information from the "
                "following input: {input}",
            ),
            (
                "human",
                "Mandatory: Make sure to answer in the correct format, specified here: {format_instructions}",
            ),
        ]
        if self.allowed_vertex_types or self.allowed_edge_types:
            prompt.append(
                (
                    "human",
                    "Tip: Make sure to use the following types if they are applicable. "
                    "If the input does not contain any of the types, you may create your own.",
                )
            )
        if self.allowed_vertex_types:
            prompt.append(("human", f"Allowed Node Types: {self.allowed_vertex_types}"))
        if self.allowed_edge_types:
            prompt.append(("human", f"Allowed Edge Types: {self.allowed_edge_types}"))
        prompt = ChatPromptTemplate.from_messages(prompt)
        chain = prompt | self.llm_service.model  # | parser
        er = self._extract_kg_from_doc(document, chain, parser)
        return er

    def extract(self, text):
        return self.document_er_extraction(text)
    
    async def aextract(self, text) -> list[GraphDocument]:
        return await self.adocument_er_extraction(text)
    

