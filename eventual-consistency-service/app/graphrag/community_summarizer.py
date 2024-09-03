import re

from langchain_core.prompts import PromptTemplate

from common.llm_services import LLM_Model
from common.py_schemas import CommunitySummary

# src: https://github.com/microsoft/graphrag/blob/main/graphrag/index/graph/extractors/summarize/prompts.py
SUMMARIZE_PROMPT = PromptTemplate.from_template("""
You are a helpful assistant responsible for generating a comprehensive summary of the data provided below.
Given one or two entities, and a list of descriptions, all related to the same entity or group of entities.
Please concatenate all of these into a single, comprehensive description. Make sure to include information collected from all the descriptions.
If the provided descriptions are contradictory, please resolve the contradictions and provide a single, coherent summary, but do not add any information that is not in the description.
Make sure it is written in third person, and include the entity names so we the have full context.

#######
-Data-
Commuinty Title: {entity_name}
Description List: {description_list}
""")

id_pat = re.compile(r"[_\d]*")


class CommunitySummarizer:
    def __init__(
        self,
        llm_service: LLM_Model,
    ):
        self.llm_service = llm_service

    async def summarize(self, name: str, text: list[str]) -> CommunitySummary:
        structured_llm = self.llm_service.model.with_structured_output(CommunitySummary)
        chain = SUMMARIZE_PROMPT | structured_llm

        # remove iteration tags from name
        name = id_pat.sub("", name)
        try:
            summary = await chain.ainvoke(
                {
                    "entity_name": name,
                    "description_list": text,
                }
            )
        except Exception as e:
            return {"summary": f"Error: {e}"}
        return summary.summary
