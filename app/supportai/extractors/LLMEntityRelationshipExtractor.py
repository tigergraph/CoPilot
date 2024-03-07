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
                    formatted_rels.append({"source": rels["source"]["id"], "target": rels["target"], "type": rels["type"], "definition": rels["definition"]})
                elif isinstance(rels["source"], str) and isinstance(rels["target"], dict):
                    formatted_rels.append({"source": rels["source"], "target": rels["target"]["id"], "type": rels["type"], "definition": rels["definition"]})
                elif isinstance(rels["source"], dict) and isinstance(rels["target"], dict):
                    formatted_rels.append({"source": rels["source"]["id"], "target": rels["target"]["id"], "type": rels["type"], "definition": rels["definition"]})
                else:
                    raise Exception("Relationship parsing error")
            return {"nodes": json_out["nodes"], "rels": formatted_rels}
        except:
            print("Error Processing: ", out)
        return {"nodes": [], "rels": []}
    
    def document_er_extraction(self, document):
        from langchain.prompts import ChatPromptTemplate
        from langchain.output_parsers import PydanticOutputParser
        parser = PydanticOutputParser(pydantic_object=KnowledgeGraph)
        prompt = ChatPromptTemplate.from_messages(
                            [(
                            "system",
                            f"""# Knowledge Graph Instructions for GPT-4
                        ## 1. Overview
                        You are a top-tier algorithm designed for extracting information in structured formats to build a knowledge graph.
                        - **Nodes** represent entities, concepts, and properties of entities.
                        - The aim is to achieve simplicity and clarity in the knowledge graph, making it accessible for a vast audience.
                        ## 2. Labeling Nodes
                        - **Consistency**: Ensure you use basic or elementary types for node labels.
                        - For example, when you identify an entity representing a person, always label it as **"person"**. Avoid using more specific terms like "mathematician" or "scientist".
                        - **Node IDs**: Never utilize integers as node IDs. Node IDs should be names or human-readable identifiers found in the text.
                        ## 3. Handling Numerical Data and Dates
                        - Numerical data, like age or other related information, should be incorporated as attributes or properties of the respective nodes.
                        - **No Separate Nodes for Dates/Numbers**: Do not create separate nodes for dates or numerical values. Always attach them as attributes or properties of nodes.
                        - **Property Format**: Properties must be in a key-value format. Only use properties for dates and numbers, string properties should be new nodes.
                        - **Quotation Marks**: Never use escaped single or double quotes within property values.
                        - **Naming Convention**: Use camelCase for property keys, e.g., `birthDate`.
                        ## 4. Coreference Resolution
                        - **Maintain Entity Consistency**: When extracting entities, it's vital to ensure consistency.
                        If an entity, such as "John Doe", is mentioned multiple times in the text but is referred to by different names or pronouns (e.g., "Joe", "he"), 
                        always use the most complete identifier for that entity throughout the knowledge graph. In this example, use "John Doe" as the entity ID.  
                        Remember, the knowledge graph should be coherent and easily understandable, so maintaining consistency in entity references is crucial. 
                        ## 5. Strict Compliance
                        Adhere to the rules strictly. Non-compliance will result in termination, including poor formatting. 
                        ## 6. Handling Instances with No Relationships
                        If a node has no relationships, it should still be included in the knowledge graph. Simply add the node and leave the relationships section empty."""),
                                ("human", "Use the given format to extract information from the following input: {input}"),
                                ("human", "Mandatory: Make sure to answer in the correct format, specified here: {format_instructions}"),
                            ])
        chain = prompt | self.llm_service.model #| parser
        er =  self._extract_kg_from_doc(document, chain, parser)
        return er

    def extract(self, text):
        return self.document_er_extraction(text)