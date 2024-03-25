from app.llm_services import LLM_Model
from app.supportai.extractors.BaseExtractor import BaseExtractor
from app.py_schemas import KnowledgeGraph
import json



class LLMEntityRelationshipExtractor(BaseExtractor):
    def __init__(self, llm_service: LLM_Model):
        self.llm_service = llm_service

    def _extract_kg_from_doc(self, doc, chain, parser):
        try:
            out = chain.invoke({"input": doc, "format_instructions": parser.get_format_instructions()})
        except Exception as e:
            print("Error: ", e)
            return {"nodes": [], "rels": []}
        try:
            if "```json" not in out.content:
                json_out = json.loads(out.content.strip("content="))
            else:
                json_out = json.loads(out.content.split("```")[1].strip("```").strip("json").strip())

            formatted_rels = []
            for rels in json_out["rels"]:
                if isinstance(rels["source"], str) and isinstance(rels["target"], str):
                    formatted_rels.append(rels)
                elif isinstance(rels["source"], dict) and isinstance(rels["target"], str):
                    formatted_rels.append({"source": rels["source"]["id"], "target": rels["target"], "type": rels["relation_type"].replace(" ", "_").upper(), "definition": rels["definition"]})
                elif isinstance(rels["source"], str) and isinstance(rels["target"], dict):
                    formatted_rels.append({"source": rels["source"], "target": rels["target"]["id"], "type": rels["relation_type"].replace(" ", "_").upper(), "definition": rels["definition"]})
                elif isinstance(rels["source"], dict) and isinstance(rels["target"], dict):
                    formatted_rels.append({"source": rels["source"]["id"], "target": rels["target"]["id"], "type": rels["relation_type"].replace(" ", "_").upper(), "definition": rels["definition"]})
                else:
                    raise Exception("Relationship parsing error")
            formatted_nodes = []
            for node in json_out["nodes"]:
                formatted_nodes.append({"id": node["id"], "type": node["node_type"].replace(" ", "_").capitalize(), "definition": node["definition"]})
            return {"nodes": formatted_nodes, "rels": formatted_rels}
        except:
            print("Error Processing: ", out)
        return {"nodes": [], "rels": []}
    
    def document_er_extraction(self, document):
        from langchain.prompts import ChatPromptTemplate
        from langchain.output_parsers import PydanticOutputParser
        parser = PydanticOutputParser(pydantic_object=KnowledgeGraph)
        prompt = ChatPromptTemplate.from_messages(
                            [(
                            "system", self.llm_service.entity_relationship_extraction_prompt),
                                ("human", "Tip: Make sure to answer in the correct format and do "
                                            "not include any explanations. "
                                            "Use the given format to extract information from the "
                                            "following input: {input}"),
                                ("human", "Mandatory: Make sure to answer in the correct format, specified here: {format_instructions}"),
                            ])
        chain = prompt | self.llm_service.model #| parser
        er =  self._extract_kg_from_doc(document, chain, parser)
        return er

    def extract(self, text):
        return self.document_er_extraction(text)