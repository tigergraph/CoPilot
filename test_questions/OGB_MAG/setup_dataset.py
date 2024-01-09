from pyTigerGraph import TigerGraphConnection
from pyTigerGraph.datasets import Datasets
import os
import json

with open("../"+os.environ.get("DB_CONFIG")) as cfg:
    config = json.load(cfg)

conn = TigerGraphConnection(
    host=config["hostname"],
    username=config["username"],
    password=config["password"],
)

dataset = Datasets("OGB_MAG")
conn.ingestDataset(dataset, getToken=config["getToken"])

queries_dir = [x for x in os.listdir('./') if not(os.path.isfile('./'+x)) and x != "tmp"]

queries = [open(x+"/"+x+".gsql").read() + "\nINSTALL QUERY "+x for x in queries_dir]

queries = "USE GRAPH OGB_MAG\n" + "\n".join(queries)

conn.gsql(queries)
