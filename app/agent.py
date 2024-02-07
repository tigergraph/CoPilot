from langchain.agents import AgentType, AgentExecutor
from langchain.tools.render import render_text_description_and_args
from langchain.agents.output_parsers import (
    ReActJsonSingleInputOutputParser,
)

from langchain.agents.format_scratchpad import format_log_to_messages

from langchain_core.agents import AgentAction
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.pydantic_v1 import BaseModel, Field
from typing import List, Union
import logging

from app.tools import GenerateFunction, MapQuestionToSchema
from app.embedding_utils.embedding_services import EmbeddingModel
from app.embedding_utils.embedding_stores import EmbeddingStore

from app.llm_services.base_llm import LLM_Model

from app.log import req_id_cv

logger = logging.getLogger(__name__)

class TigerGraphAgent():
    """TigerGraph Agent Class
    
    The TigerGraph Agent Class combines the various dependencies needed for a AI Agent to reason with data in a TigerGraph database.

    Args:
        llm_provider (LLM_Model):
            a LLM_Model class that connects to an external LLM API service.
        db_connection (TigerGraphConnection):
            a PyTigerGraph TigerGraphConnection object instantiated to interact with the desired database/graph and authenticated with correct roles.
        embedding_model (EmbeddingModel):
            a EmbeddingModel class that connects to an external embedding API service.
        embedding_store (EmbeddingStore):
            a EmbeddingStore class that connects to an embedding store to retrieve pyTigerGraph and custom query documentation from.
    """
    def __init__(self, llm_provider: LLM_Model, db_connection: "TigerGraphConnection", embedding_model: EmbeddingModel, embedding_store:EmbeddingStore):
        self.conn = db_connection

        self.llm = llm_provider

        self.mq2s = MapQuestionToSchema(self.conn, self.llm.model, self.llm.map_question_schema_prompt)
        self.gen_func = GenerateFunction(self.conn, self.llm.model, self.llm.generate_function_prompt, embedding_model, embedding_store)

        self.tools = [self.mq2s, self.gen_func]

        logger.debug(f"request_id={req_id_cv.get()} agent tools created")

        system_message = f"""Answer the following questions as best you can. You can answer directly if the user is greeting you or similar.
                            Otherise, you have access to the following tools:

                            {render_text_description_and_args(self.tools).replace('{', '{{').replace('}', '}}')}

                            The way you use the tools is by specifying a json blob.
                            Specifically, this json should have a `action` key (with the name of the tool to use) and a `action_input` key (with the input to the tool going here).
                            The only values that should be in the "action" field are: {[t.name for t in self.tools]}
                            The $JSON_BLOB should only contain a SINGLE action, do NOT return a list of multiple actions. Here is an example of a valid $JSON_BLOB:
                            ```
                            {{{{
                                "action": $TOOL_NAME,
                                "action_input": $INPUT
                            }}}}
                            ```
                            ALWAYS use the following format:
                            Question: the input question you must answer
                            Thought: you should always think about what to do
                            Action:```$JSON_BLOB```
                            Observation: the result of the action... (this Thought/Action/Observation can repeat N times)
                            Thought: I now know the final answer
                            Final Answer: the final answer to the original input question

                            Begin! Reminder to always use the exact characters `Final Answer` when responding.'
                            """

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "user",
                    system_message,
                ),
                MessagesPlaceholder(variable_name="chat_history"),
                ("user", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ]
        )

        chat_model_with_stop = self.llm.model.bind(stop=["\nObservation"])
        self.agent = (
            {
                "input": lambda x: x["input"],
                "agent_scratchpad": lambda x: format_log_to_messages(x["intermediate_steps"]),
                "chat_history": lambda x: x['chat_history']
            }
            | prompt
            | chat_model_with_stop
            | ReActJsonSingleInputOutputParser()
        )


        logger.debug(f"request_id={req_id_cv.get()} agent initialized")

    def question_for_agent(self, question: str):
        """Question for Agent.

        Ask the agent a question to be answered by the database. Returns the agent resoposne or raises an exception.

        Args:
            question (str): 
                The question to ask the agent
        """
        logger.info(f"request_id={req_id_cv.get()} ENTRY question_for_agent")
        logger.debug_pii(f"request_id={req_id_cv.get()} question_for_agent question={question}")
        try:
            agent_executor = AgentExecutor(agent=self.agent, tools=self.tools, return_intermediate_steps=True)
            resp = agent_executor.invoke({"input": question, "chat_history": []})
            logger.info(f"request_id={req_id_cv.get()} EXIT question_for_agent")
            return resp
        except Exception as e:
            print(e)
            logger.error(f"request_id={req_id_cv.get()} FAILURE question_for_agent")
            raise e