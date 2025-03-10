import json
import uuid

from pyTigerGraph import TigerGraphConnection

from common.py_schemas.schemas import (
    # CoPilotResponse,
    CreateIngestConfig,
    # LoadingInfo,
    # SupportAIInitConfig,
    # SupportAIMethod,
    # SupportAIQuestion,
)


def init_supportai(conn: TigerGraphConnection, graphname: str) -> tuple[dict, dict]:
    # need to open the file using the absolute path
    ver = conn.getVer().split(".")
    file_path = "common/gsql/supportai/SupportAI_Schema.gsql"
    with open(file_path, "r") as f:
        schema = f.read()
    schema_res = conn.gsql(
        """USE GRAPH {}\n{}\nRUN SCHEMA_CHANGE JOB add_supportai_schema""".format(
            graphname, schema
        )
    )
    if int(ver[0]) >= 4 and int(ver[1]) >= 2:
        file_path = "common/gsql/supportai/SupportAI_Schema_Native_Vector.gsql"
        with open(file_path, "r") as f:
            schema = f.read()
        schema_res = conn.gsql(
            """USE GRAPH {}\n{}\nRUN SCHEMA_CHANGE JOB add_supportai_vector""".format(
                graphname, schema
            )
        )

    file_path = "common/gsql/supportai/SupportAI_IndexCreation.gsql"
    with open(file_path) as f:
        index = f.read()
    index_res = conn.gsql(
        """USE GRAPH {}\n{}\nRUN SCHEMA_CHANGE JOB add_supportai_indexes""".format(
            graphname, index
        )
    )

    file_path = "common/gsql/supportai/Scan_For_Updates.gsql"
    with open(file_path) as f:
        scan_for_updates = f.read()
    res = conn.gsql(
        "USE GRAPH "
        + conn.graphname
        + "\n"
        + scan_for_updates
        + "\n INSTALL QUERY Scan_For_Updates"
    )

    file_path = "common/gsql/supportai/Update_Vertices_Processing_Status.gsql"
    with open(file_path) as f:
        update_vertices = f.read()
    res = conn.gsql(
        "USE GRAPH "
        + conn.graphname
        + "\n"
        + update_vertices
        + "\n INSTALL QUERY Update_Vertices_Processing_Status"
    )

    return schema_res, index_res


def create_ingest(
    graphname: str,
    ingest_config: CreateIngestConfig,
    conn: TigerGraphConnection,
):
    if ingest_config.file_format.lower() == "json":
        file_path = "common/gsql/supportai/SupportAI_InitialLoadJSON.gsql"

        with open(file_path) as f:
            ingest_template = f.read()
        ingest_template = ingest_template.replace("@uuid@", str(uuid.uuid4().hex))
        doc_id = ingest_config.loader_config.get("doc_id_field", "doc_id")
        doc_text = ingest_config.loader_config.get("content_field", "content")
        ingest_template = ingest_template.replace('"doc_id"', '"{}"'.format(doc_id))
        ingest_template = ingest_template.replace('"content"', '"{}"'.format(doc_text))

    if ingest_config.file_format.lower() == "csv":
        file_path = "common/gsql/supportai/SupportAI_InitialLoadCSV.gsql"

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

    file_path = "common/gsql/supportai/SupportAI_DataSourceCreation.gsql"

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
