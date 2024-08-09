import json

from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import ChatPromptTemplate
from langchain_core.prompts import PromptTemplate

from common.llm_services import LLM_Model
from common.py_schemas import CommunitySummary

# src: https://github.com/microsoft/graphrag/blob/main/graphrag/index/graph/extractors/summarize/prompts.py
SUMMARIZE_PROMPT = PromptTemplate.from_template("""
You are a helpful assistant responsible for generating a comprehensive summary of the data provided below.
Given one or two entities, and a list of descriptions, all related to the same entity or group of entities.
Please concatenate all of these into a single, comprehensive description. Make sure to include information collected from all the descriptions.
If the provided descriptions are contradictory, please resolve the contradictions and provide a single, coherent summary.
Make sure it is written in third person, and include the entity names so we the have full context.

#######
-Data-
Entities: {entity_name}
Description List: {description_list}
#######
Output:
""")


class CommunitySummarizer:
    def __init__(
        self,
        llm_service: LLM_Model,
    ):
        self.llm_service = llm_service

    def _extract_kg_from_doc(self, doc, chain, parser):
        try:
            out = chain.invoke(
                {"input": doc, "format_instructions": parser.get_format_instructions()}
            )
        except Exception as e:
            print("Error: ", e)
            return {"nodes": [], "rels": []}
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
            return {"nodes": formatted_nodes, "rels": formatted_rels}
        except:
            print("Error Processing: ", out)
        return {"nodes": [], "rels": []}

    async def summarize(self, name: str, text: list[str]) -> CommunitySummary:
        # parser = PydanticOutputParser(pydantic_object=CommunitySummary)
        structured_llm = self.llm_service.model.with_structured_output(CommunitySummary)
        chain = SUMMARIZE_PROMPT | structured_llm
        summary = await chain.ainvoke(
            {
                "entity_name": name,
                "description_list": text,
                # "format_instructions": parser.get_format_instructions(),
            }
        )
        # summary = self._extract_kg_from_doc(text, chain, parser)
        # summary = None
        return summary.summary
