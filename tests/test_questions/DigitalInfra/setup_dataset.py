from pyTigerGraph import TigerGraphConnection
import json
import os

def create_graph(conn, path = "./gsql/create_graph.gsql"):
    with open(path) as f:
        g = f.read()
    conn.gsql(g)
    conn.graphname = "DigitalInfra"


def create_schema(conn, path = "./gsql/create_schema.gsql"):
    with open(path) as f:
        schema = f.read()
    conn.gsql(schema)

def create_data_source(conn, path = "./gsql/create_data_source.gsql"):
    with open(path) as f:
        data_src = f.read()

    data_src = data_src.replace("AWS_IAM_ACCESS_KEY", os.environ.get("AWS_ACCESS_KEY"))
    data_src = data_src.replace("AWS_IAM_SECRET_KEY", os.environ.get("AWS_SECRET_KEY"))

    conn.gsql(data_src)

def create_load_job(conn, path = "./gsql/create_load_job.gsql"):
    with open(path) as f:
        load_job = f.read()

    conn.gsql(load_job)

def run_loading_jobs(conn, path = "./run_load_jobs.json"):
    with open(path) as f:
        loading_jobs = json.load(f)

    for job in loading_jobs:
        try:
            print(conn.gsql("USE GRAPH DigitalInfra RUN LOADING JOB "+job["jobName"]+ " USING "+job["fileTag"]+"="+'"'+job["filePath"]+'"'))
        except:
            pass

if __name__ == "__main__":
    with open("../"+os.environ.get("DB_CONFIG")) as cfg:
        config = json.load(cfg)

    conn = TigerGraphConnection(
        host=config["hostname"],
        username=config["username"],
        password=config["password"],
    )

    create_graph(conn)
    create_schema(conn)
    create_data_source(conn)
    create_load_job(conn)
    run_loading_jobs(conn)
