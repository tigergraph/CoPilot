import logging

from fastapi.responses import FileResponse, JSONResponse
from fastapi.security.http import HTTPBase
from fastapi import APIRouter, Request, Depends, Response
from typing import Annotated

from common.config import llm_config, get_llm_service
from common.py_schemas import ReportCreationRequest

from report_agent.agent import TigerGraphReportAgent

import concurrent.futures

logger = logging.getLogger(__name__)
router = APIRouter()
security = HTTPBase(scheme="basic", auto_error=False)


@router.get("/")
def read_root():
    return {"config": llm_config["model_name"]}


@router.get("/health")
async def health():
    return {
        "status": "healthy",
        "llm_completion_model": llm_config["completion_service"]["llm_model"],
        "embedding_service": llm_config["embedding_service"][
            "embedding_model_service"
        ],
    }

def retrieve_template(template_name: str):
    # TODO: Implement this function - it should retrieve the template from the database
    return template_name

@router.post("/{graphname}/create_report")
def create_report(graphname: str,
                  create_report_request: ReportCreationRequest, 
                  conn: Request, credentials: Annotated[HTTPBase, Depends(security)]):
    
    agent = TigerGraphReportAgent(conn.state.conn, get_llm_service(llm_config))
    sections = create_report_request.sections
    if isinstance(sections, str):
        sections = retrieve_template(sections)
    if isinstance(sections, list):
        if sections == []:
            sections = agent.generate_sections(create_report_request.persona,
                                               create_report_request.topic,
                                               create_report_request.message_context).sections
        else:
            # TODO: Add copilot fortify if needed
            generate_sections = False
    else:
        return JSONResponse(status_code=400, content={"error": """Invalid sections data type.
                                                               Must be an empty list (if sections are to be generated) 
                                                               or a string of a report template name, or a list of sections."""})
    gen_sections = []
    for section in sections:
        res = agent.generate_report_section(create_report_request.persona,
                                            create_report_request.topic,
                                            gen_sections,
                                            section)
        gen_sections.append(res)
        
    
    report = agent.finalize_report(create_report_request.persona,
                                   create_report_request.topic,
                                   gen_sections)

    return {"report": report.dict()}


@router.get("/metrics")
async def metrics():
    from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@router.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse("static/favicon.ico")
