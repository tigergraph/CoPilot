from common.metrics.tg_proxy import TigerGraphConnectionProxy
from common.llm_services.base_llm import LLM_Model
from common.py_schemas.tool_io_schemas import ReportSections, ReportSection


from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser, StrOutputParser
from langchain.pydantic_v1 import BaseModel, Field

import logging

logger = logging.getLogger(__name__)

class Report(BaseModel):
    report: str = Field(description="A drareport based on the answers received from the data analyst. Include citations by adding `[x]` where x is the function call that was used to determine the answer.")
    citations: list[str] = Field(description="A list of citations used in the report. Each citation should be a string. The index of the citation should match the index of the `[x]` in the report.")


class TigerGraphReportAgent:
    def __init__(self,
                 db_connection: TigerGraphConnectionProxy,
                 llm_provider: LLM_Model):
        self.conn = db_connection
        self.llm = llm_provider

    def _get_schema(self):
        verts = self.conn.getVertexTypes()
        edges = self.conn.getEdgeTypes()
        vertex_schema = []
        for vert in verts:
            primary_id = self.conn.getVertexType(vert)["PrimaryId"]["AttributeName"]
            attributes = "\n\t\t".join([attr["AttributeName"] + " of type " + attr["AttributeType"]["Name"] for attr in self.conn.getVertexType(vert)["Attributes"]])
            if attributes == "":
                attributes = "No attributes"
            vertex_schema.append(f"{vert}\n\tPrimary Id Attribute: {primary_id}\n\tAttributes: \n\t\t{attributes}")

        edge_schema = []
        for edge in edges:
            from_vertex = self.conn.getEdgeType(edge)["FromVertexTypeName"]
            to_vertex = self.conn.getEdgeType(edge)["ToVertexTypeName"]
            #reverse_edge = conn.getEdgeType(edge)["Config"].get("REVERSE_EDGE")
            attributes = "\n\t\t".join([attr["AttributeName"] + " of type " + attr["AttributeType"]["Name"] for attr in self.conn.getVertexType(vert)["Attributes"]])
            if attributes == "":
                attributes = "No attributes"
            edge_schema.append(f"{edge}\n\tFrom Vertex: {from_vertex}\n\tTo Vertex: {to_vertex}\n\tAttributes: \n\t\t{attributes}") #\n\tReverse Edge: \n\t\t{reverse_edge}")

        schema_rep = f"""The schema of the graph is as follows:
        Vertex Types:
        {chr(10).join(vertex_schema)}

        Edge Types:
        {chr(10).join(edge_schema)}
        """
        return schema_rep

    def generate_sections(self,
                          persona: str,
                          topic: str,
                          message_context: list = None) -> list:
        """
        Generate sections for a report based on the persona, topic, and message context.
        
        Args:
            persona (str):
                The persona for which the report is being generated.
            topic (str):
                The topic of the report.
            message_context (list, optional):
                A list of message context objects. Defaults to None.
        Returns:
            A list of report sections.
        """
        logger.info(f"Generating sections for {persona} on {topic}.")
        section_parser = PydanticOutputParser(pydantic_object=ReportSections)
        if message_context:
            SECTION_GENERATION_PROMPT = PromptTemplate(
                template = """You are a {persona} and are writing a report on {topic}.
                            You have access to the following data: {schema_rep}
                            Generate sections for the report. Use the following messages for additional context about the topic:
                            {message_context}

                            Make sure to use the message context above to generate specifc questions for the report. 
                            E.g. ids or names of entities mentioned in the conversation history should be used in the questions.

                            Each section should have a name, description, and a list of questions to answer in the section.
                            Format your outline as described below:
                            {format_instructions}""",
                input_variables=["persona", "topic", "message_context", "schema_rep"],
                partial_variables={
                    "format_instructions": section_parser.get_format_instructions()
                }
            )
        else:
            SECTION_GENERATION_PROMPT = PromptTemplate(
                template = """You are a {persona} and are writing a report on {topic}.
                            You have access to the following data: {schema_rep}
                            Generate sections for the report.
                            Each section should have a name, description, and a list of questions to answer in the section.
                            Format your outline as described below:
                            {format_instructions}""",
                input_variables=["persona", "topic", "schema_rep"],
                partial_variables={
                    "format_instructions": section_parser.get_format_instructions()
                }
            )


        chain = SECTION_GENERATION_PROMPT | self.llm.model | section_parser

        if message_context:
            sections = chain.invoke({"persona": persona,
                                     "topic": topic,
                                     "message_context": str(message_context),
                                     "schema_rep": self._get_schema()})
        else:
            sections = chain.invoke({"persona": persona,
                                     "topic": topic,
                                     "schema_rep": self._get_schema()})
        
        return sections

    def generate_report_section(self,
                                persona,
                                topic,
                                gen_sections: list[str],
                                section: ReportSection) -> Report:
        """
        Generate a report section based on the persona, topic, and section object.

        Args:
            persona (str):
                The persona for which the report is being generated.
            topic (str):
                The topic of the report.
            section (ReportSection):
                A report section object.
        Returns:
            A report section.
        """
        logger.info(f"Generating section {section.section} for {persona} on {topic}.")
        try:
            if section.actions:
                # TODO: run queries specified in the section actions
                pass
        except:
            pass

        q_and_a = []


        QUESTION_REPHRASE_PROMPT = PromptTemplate(
            template = """You are a {persona} and are writing a report on {topic}.
                          You are writing a section about {section_name}.
                          Previously generated sections are as follows:
                            {sections}
                          The question is: {question}.
                          Rephrase the question to be more specific, including IDs or names of entities mentioned in the previous sections.
                    """,
            input_variables=["persona", "topic", "section_name", "question", "sections"],
        )

        question_rephrase_chain = QUESTION_REPHRASE_PROMPT | self.llm.model | StrOutputParser()


        for question in section.questions:
            question_text = question.question
            '''
            rephrased_q = question_rephrase_chain.invoke(
                                            {"persona": persona,
                                             "topic": topic,
                                             "section_name": section.section,
                                             "question": question_text,
                                             "sections": "\n\n".join(gen_sections)}
                                        )
            '''
            logger.info(f"Generating answer for question: {question_text}")
            resp = self.conn.ai.query(question_text)
            q_and_a.append({"question": question_text,
                            "answer": resp,
                            "question_reason": question.reasoning})
            
        SECTION_PROMPT = PromptTemplate(
            template = """You are a {persona} and are writing a report on {topic}.
                          This section is about {section_name}, which should contain {section_description}.

                          The previous sections generated are as follows:
                          {sections}

                          Include a citations section at the end of the section, which denotes what sources were used to answer the questions.
                          Here are questions and answers to write about in this section:
                          {qa_pairs}""",
            input_variables=["persona", "topic", "section_name", "section_description", "qa_pairs"],
        )

        chain = SECTION_PROMPT | self.llm.model | StrOutputParser()
        try:
            section_text = chain.invoke({"persona": persona,
                                        "topic": topic,
                                        "section_name": section.section,
                                        "section_description": section.description,
                                        "sections": "\n\n".join(gen_sections),
                                        "qa_pairs": str(q_and_a)})
        except:
            section_text = "Error generating section text."
        
        return section_text
    
    def finalize_report(self,
                        persona,
                        topic,
                        sections) -> str:
        """
        Finalize the report based on the persona and topic.

        Args:
            persona (str):
                The persona for which the report is being generated.
            topic (str):
                The topic of the report.
            sections (list):
                A list of report sections. Each section should be a string.
        Returns:
            The finalized report.
        """
        logger.info(f"Finalizing report for {persona} on {topic}.")
        report_parser = PydanticOutputParser(pydantic_object=Report)

        FINALIZE_PROMPT = PromptTemplate(
            template = """You are a {persona} and are writing a report on {topic}.
                          You have generated the following sections: {sections}.
                          Compile the sections into a finalized report.
                          Include citations at the end of the report to denote what sources were used to answer the questions.
                          Format your report as described below:
                          {format_instructions}
                     """,
            input_variables=["persona", "topic", "sections"],
            partial_variables={
                "format_instructions": report_parser.get_format_instructions()
            }
        )
            
        chain = FINALIZE_PROMPT | self.llm.model | report_parser

        try:
            report = chain.invoke({"persona": persona,
                                  "topic": topic,
                                  "sections": "\n".join([section for section in sections])})
            return report
        except:
            error_report = Report(report="Error generating report.", citations=[])
            return error_report



