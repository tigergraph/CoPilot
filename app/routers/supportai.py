import json
import logging
import uuid
from typing import Union

from fastapi import APIRouter, BackgroundTasks, Depends

from app.config import (embedding_service, embedding_store, get_llm_service,
                        llm_config, status_manager)
from app.log import req_id_cv
from app.metrics.tg_proxy import TigerGraphConnectionProxy
from app.py_schemas.schemas import (BatchDocumentIngest, CoPilotResponse,
                                    CreateIngestConfig,
                                    CreateVectorIndexConfig, LoadingInfo,
                                    S3BatchDocumentIngest, SupportAIQuestion)
from app.supportai.concept_management.create_concepts import (
    CommunityConceptCreator, EntityConceptCreator, HigherLevelConceptCreator,
    RelationshipConceptCreator)
from app.supportai.retrievers import (EntityRelationshipRetriever,
                                      HNSWOverlapRetriever, HNSWRetriever,
                                      HNSWSiblingRetriever)
from app.supportai.supportai_ingest import BatchIngestion
from app.util import get_db_connection, get_eventual_consistency_checker

logger = logging.getLogger(__name__)
router = APIRouter(tags=["SupportAI"])


@router.post("/{graphname}/supportai/initialize")
def initialize(graphname, conn: TigerGraphConnectionProxy = Depends(get_db_connection)):
    # need to open the file using the absolute path
    file_path = "app/gsql/supportai/SupportAI_Schema.gsql"
    with open(file_path, "r") as f:
        schema = f.read()
    schema_res = conn.gsql(
        """USE GRAPH {}\n{}\nRUN SCHEMA_CHANGE JOB add_supportai_schema""".format(
            graphname, schema
        )
    )

    file_path = "app/gsql/supportai/SupportAI_IndexCreation.gsql"
    with open(file_path) as f:
        index = f.read()
    index_res = conn.gsql(
        """USE GRAPH {}\n{}\nRUN SCHEMA_CHANGE JOB add_supportai_indexes""".format(
            graphname, index
        )
    )

    file_path = "app/gsql/supportai/Scan_For_Updates.gsql"
    with open(file_path) as f:
        scan_for_updates = f.read()
    res = conn.gsql(
        "USE GRAPH "
        + conn.graphname
        + "\n"
        + scan_for_updates
        + "\n INSTALL QUERY Scan_For_Updates"
    )

    file_path = "app/gsql/supportai/Update_Vertices_Processing_Status.gsql"
    with open(file_path) as f:
        update_vertices = f.read()
    res = conn.gsql(
        "USE GRAPH "
        + conn.graphname
        + "\n"
        + update_vertices
        + "\n INSTALL QUERY Update_Vertices_Processing_Status"
    )

    return {
        "host_name": conn._tg_connection.host,  # include host_name for debugging from client. Their pyTG conn might not have the same host as what's configured in copilot
        "schema_creation_status": json.dumps(schema_res),
        "index_creation_status": json.dumps(index_res),
    }


@router.post("/{graphname}/supportai/create_ingest")
def create_ingest(
    graphname,
    ingest_config: CreateIngestConfig,
    background_tasks: BackgroundTasks,
    conn: TigerGraphConnectionProxy = Depends(get_db_connection),
):
    background_tasks.add_task(get_eventual_consistency_checker, graphname)
    if ingest_config.file_format.lower() == "json":
        file_path = "app/gsql/supportai/SupportAI_InitialLoadJSON.gsql"

        with open(file_path) as f:
            ingest_template = f.read()
        ingest_template = ingest_template.replace("@uuid@", str(uuid.uuid4().hex))
        doc_id = ingest_config.loader_config.get("doc_id_field", "doc_id")
        doc_text = ingest_config.loader_config.get("content_field", "content")
        ingest_template = ingest_template.replace('"doc_id"', '"{}"'.format(doc_id))
        ingest_template = ingest_template.replace('"content"', '"{}"'.format(doc_text))

    if ingest_config.file_format.lower() == "csv":
        file_path = "app/gsql/supportai/SupportAI_InitialLoadCSV.gsql"

        with open(file_path) as f:
            ingest_template = f.read()
        ingest_template = ingest_template.replace("@uuid@", str(uuid.uuid4().hex))
        separator = ingest_config.get("separator", "|")
        header = ingest_config.get("header", "true")
        eol = ingest_config.get("eol", "\n")
        quote = ingest_config.get("quote", "double")
        ingest_template = ingest_template.replace('"|"', '"{}"'.format(separator))
        ingest_template = ingest_template.replace('"true"', '"{}"'.format(header))
        ingest_template = ingest_template.replace('"\\n"', '"{}"'.format(eol))
        ingest_template = ingest_template.replace('"double"', '"{}"'.format(quote))

    file_path = "app/gsql/supportai/SupportAI_DataSourceCreation.gsql"

    with open(file_path) as f:
        data_stream_conn = f.read()

    # assign unique identifier to the data stream connection

    data_stream_conn = data_stream_conn.replace(
        "@source_name@", "SupportAI_" + graphname + "_" + str(uuid.uuid4().hex)
    )

    # check the data source and create the appropriate connection
    if ingest_config.data_source.lower() == "s3":
        data_conn = ingest_config.data_source_config
        if (
            data_conn.get("aws_access_key") is None
            or data_conn.get("aws_secret_key") is None
        ):
            raise Exception("AWS credentials not provided")
        connector = {
            "type": "s3",
            "access.key": data_conn["aws_access_key"],
            "secret.key": data_conn["aws_secret_key"],
        }

        data_stream_conn = data_stream_conn.replace(
            "@source_config@", json.dumps(connector)
        )

    elif ingest_config.data_source.lower() == "azure":
        if ingest_config.data_source_config.get("account_key") is not None:
            connector = {
                "type": "abs",
                "account.key": ingest_config.data_source_config["account_key"],
            }
        elif ingest_config.data_source_config.get("client_id") is not None:
            # verify that the client secret is also provided
            if ingest_config.data_source_config.get("client_secret") is None:
                raise Exception("Client secret not provided")
            # verify that the tenant id is also provided
            if ingest_config.data_source_config.get("tenant_id") is None:
                raise Exception("Tenant id not provided")
            connector = {
                "type": "abs",
                "client.id": ingest_config.data_source_config["client_id"],
                "client.secret": ingest_config.data_source_config["client_secret"],
                "tenant.id": ingest_config.data_source_config["tenant_id"],
            }
        else:
            raise Exception("Azure credentials not provided")
        data_stream_conn = data_stream_conn.replace(
            "@source_config@", json.dumps(connector)
        )
    elif ingest_config.data_source.lower() == "gcs":
        # verify that the correct fields are provided
        if ingest_config.data_source_config.get("project_id") is None:
            raise Exception("Project id not provided")
        if ingest_config.data_source_config.get("private_key_id") is None:
            raise Exception("Private key id not provided")
        if ingest_config.data_source_config.get("private_key") is None:
            raise Exception("Private key not provided")
        if ingest_config.data_source_config.get("client_email") is None:
            raise Exception("Client email not provided")
        connector = {
            "type": "gcs",
            "project_id": ingest_config.data_source_config["project_id"],
            "private_key_id": ingest_config.data_source_config["private_key_id"],
            "private_key": ingest_config.data_source_config["private_key"],
            "client_email": ingest_config.data_source_config["client_email"],
        }
        data_stream_conn = data_stream_conn.replace(
            "@source_config@", json.dumps(connector)
        )
    else:
        raise Exception("Data source not implemented")

    load_job_created = conn.gsql("USE GRAPH {}\n".format(graphname) + ingest_template)

    data_source_created = conn.gsql(
        "USE GRAPH {}\n".format(graphname) + data_stream_conn
    )

    return {
        "load_job_id": load_job_created.split(":")[1]
        .strip(" [")
        .strip(" ")
        .strip(".")
        .strip("]"),
        "data_source_id": data_source_created.split(":")[1]
        .strip(" [")
        .strip(" ")
        .strip(".")
        .strip("]"),
    }


@router.post("/{graphname}/supportai/ingest")
def ingest(
    graphname,
    loader_info: LoadingInfo,
    background_tasks: BackgroundTasks,
    conn: TigerGraphConnectionProxy = Depends(get_db_connection),
):
    background_tasks.add_task(get_eventual_consistency_checker, graphname)
    if loader_info.file_path is None:
        raise Exception("File path not provided")
    if loader_info.load_job_id is None:
        raise Exception("Load job id not provided")
    if loader_info.data_source_id is None:
        raise Exception("Data source id not provided")

    try:
        res = conn.gsql(
            'USE GRAPH {}\nRUN LOADING JOB -noprint {} USING {}="{}"'.format(
                graphname,
                loader_info.load_job_id,
                "DocumentContent",
                "$" + loader_info.data_source_id + ":" + loader_info.file_path,
            )
        )
    except Exception as e:
        if (
            "Running the following loading job in background with '-noprint' option:"
            in str(e)
        ):
            res = str(e)
        else:
            raise e
    return {
        "job_name": loader_info.load_job_id,
        "job_id": res.split(
            "Running the following loading job in background with '-noprint' option:"
        )[1]
        .split("Jobid: ")[1]
        .split("\n")[0],
        "log_location": res.split(
            "Running the following loading job in background with '-noprint' option:"
        )[1]
        .split("Log directory: ")[1]
        .split("\n")[0],
    }


@router.post("/{graphname}/supportai/batch_ingest")
async def batch_ingest(
    graphname,
    doc_source: Union[S3BatchDocumentIngest, BatchDocumentIngest],
    background_tasks: BackgroundTasks,
    conn: TigerGraphConnectionProxy = Depends(get_db_connection),
):
    background_tasks.add_task(get_eventual_consistency_checker, graphname)
    req_id = req_id_cv.get()
    status_manager.create_status(conn.username, req_id, graphname)
    ingestion = BatchIngestion(
        embedding_service,
        get_llm_service(llm_config),
        conn,
        status_manager.get_status(req_id),
    )
    if doc_source.service.lower() == "s3":
        background_tasks.add_task(ingestion.ingest_blobs, doc_source)
    else:
        raise Exception("Document storage service not implemented")

    return {"status": "request accepted", "request_id": req_id}


@router.get("/{graphname}/supportai/ingestion_status")
async def ingestion_status(graphname, status_id: str):
    status = status_manager.get_status(status_id)

    if status:
        return {"status": status.to_dict()}
    else:
        return {"status": "not found"}


@router.post("/{graphname}/supportai/createvdb")
def create_vdb(
    graphname,
    config: CreateVectorIndexConfig,
    conn: TigerGraphConnectionProxy = Depends(get_db_connection),
):
    if (
        conn.getVertexCount(
            "HNSWEntrypoint", where='id=="{}"'.format(config.index_name)
        )
        == 0
    ):
        res = conn.runInstalledQuery(
            "HNSW_CreateEntrypoint", {"index_name": config.index_name}
        )

    res = conn.runInstalledQuery(
        "HNSW_BuildIndex",
        {
            "index_name": config.index_name,
            "v_types": config.vertex_types,
            "M": config.M,
            "ef_construction": config.ef_construction,
        },
    )
    return res


@router.get("/{graphname}/supportai/deletevdb/{index_name}")
def delete_vdb(
    graphname, index_name, conn: TigerGraphConnectionProxy = Depends(get_db_connection)
):
    return conn.runInstalledQuery("HNSW_DeleteIndex", {"index_name": index_name})


@router.post("/{graphname}/supportai/queryvdb/{index_name}")
def query_vdb(
    graphname,
    index_name,
    query: SupportAIQuestion,
    background_tasks: BackgroundTasks,
    conn: TigerGraphConnectionProxy = Depends(get_db_connection),
):
    background_tasks.add_task(get_eventual_consistency_checker, graphname)
    retriever = HNSWRetriever(
        embedding_service, embedding_store, get_llm_service(llm_config), conn
    )
    return retriever.search(
        query.question,
        index_name,
        query.method_params["top_k"],
        query.method_params["withHyDE"],
    )


@router.post("/{graphname}/supportai/search")
async def search(
    graphname,
    query: SupportAIQuestion,
    background_tasks: BackgroundTasks,
    conn: TigerGraphConnectionProxy = Depends(get_db_connection),
):
    background_tasks.add_task(get_eventual_consistency_checker, graphname)
    if query.method.lower() == "hnswoverlap":
        retriever = HNSWOverlapRetriever(
            embedding_service, embedding_store, get_llm_service(llm_config), conn
        )
        res = retriever.search(
            query.question,
            query.method_params["indices"],
            query.method_params["top_k"],
            query.method_params["num_hops"],
            query.method_params["num_seen_min"],
        )
    elif query.method.lower() == "vdb":
        if "index" not in query.method_params:
            raise Exception("Index name not provided")
        retriever = HNSWRetriever(
            embedding_service, embedding_store, get_llm_service(llm_config), conn
        )
        res = retriever.search(
            query.question,
            query.method_params["index"],
            query.method_params["top_k"],
            query.method_params["withHyDE"],
        )
    elif query.method.lower() == "sibling":
        if "index" not in query.method_params:
            raise Exception("Index name not provided")
        retriever = HNSWSiblingRetriever(
            embedding_service, embedding_store, get_llm_service(llm_config), conn
        )
        res = retriever.search(
            query.question,
            query.method_params["index"],
            query.method_params["top_k"],
            query.method_params["lookback"],
            query.method_params["lookahead"],
            query.method_params["withHyDE"],
        )
    elif query.method.lower() == "entityrelationship":
        retriever = EntityRelationshipRetriever(
            embedding_service, embedding_store, get_llm_service(llm_config), conn
        )
        res = retriever.search(query.question, query.method_params["top_k"])

    return res


@router.post("/{graphname}/supportai/answerquestion")
async def answer_question(
    graphname,
    query: SupportAIQuestion,
    background_tasks: BackgroundTasks,
    conn: TigerGraphConnectionProxy = Depends(get_db_connection),
):
    background_tasks.add_task(get_eventual_consistency_checker, graphname)
    resp = CoPilotResponse
    resp.response_type = "supportai"
    if query.method.lower() == "hnswoverlap":
        retriever = HNSWOverlapRetriever(
            embedding_service, embedding_store, get_llm_service(llm_config), conn
        )
        res = retriever.retrieve_answer(
            query.question,
            query.method_params["indices"],
            query.method_params["top_k"],
            query.method_params["num_hops"],
            query.method_params["num_seen_min"],
        )
    elif query.method.lower() == "vdb":
        if "index" not in query.method_params:
            raise Exception("Index name not provided")
        retriever = HNSWRetriever(
            embedding_service, embedding_store, get_llm_service(llm_config), conn
        )
        res = retriever.retrieve_answer(
            query.question,
            query.method_params["index"],
            query.method_params["top_k"],
            query.method_params["withHyDE"],
        )
    elif query.method.lower() == "sibling":
        if "index" not in query.method_params:
            raise Exception("Index name not provided")
        retriever = HNSWSiblingRetriever(
            embedding_service, embedding_store, get_llm_service(llm_config), conn
        )
        res = retriever.retrieve_answer(
            query.question,
            query.method_params["index"],
            query.method_params["top_k"],
            query.method_params["lookback"],
            query.method_params["lookahead"],
            query.method_params["withHyDE"],
        )
    elif query.method.lower() == "entityrelationship":
        retriever = EntityRelationshipRetriever(
            embedding_service, embedding_store, get_llm_service(llm_config), conn
        )
        res = retriever.retrieve_answer(query.question, query.method_params["top_k"])
    else:
        raise Exception("Method not implemented")

    resp.natural_language_response = res["response"]
    resp.query_sources = res["retrieved"]

    return res


@router.get("/{graphname}/supportai/buildconcepts")
async def build_concepts(
    graphname,
    background_tasks: BackgroundTasks,
    conn: TigerGraphConnectionProxy = Depends(get_db_connection),
):
    background_tasks.add_task(get_eventual_consistency_checker, graphname)
    rels_concepts = RelationshipConceptCreator(conn, llm_config, embedding_service)
    rels_concepts.create_concepts()
    ents_concepts = EntityConceptCreator(conn, llm_config, embedding_service)
    ents_concepts.create_concepts()
    comm_concepts = CommunityConceptCreator(conn, llm_config, embedding_service)
    comm_concepts.create_concepts()
    high_level_concepts = HigherLevelConceptCreator(conn, llm_config, embedding_service)
    high_level_concepts.create_concepts()

    return {"status": "success"}


@router.get("/{graphname}/supportai/forceupdate")
async def force_update(
    graphname: str, conn: TigerGraphConnectionProxy = Depends(get_db_connection)
):
    await get_eventual_consistency_checker(graphname)
    return {"status": "success"}
