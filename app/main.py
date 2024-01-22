from typing import Union, Annotated, List, Dict
from fastapi import FastAPI, Header, Depends, HTTPException, status, Request, WebSocket
from starlette.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import os
from pyTigerGraph import TigerGraphConnection
import json
import time
import uuid
import logging

from fastapi.security import HTTPBasic, HTTPBasicCredentials

from app.agent import TigerGraphAgent
from app.llm_services import OpenAI, AzureOpenAI, AWS_SageMaker_Endpoint, GoogleVertexAI
from app.embedding_utils.embedding_services import AzureOpenAI_Ada002, OpenAI_Embedding, VertexAI_PaLM_Embedding
from app.embedding_utils.embedding_stores import FAISS_EmbeddingStore

from app.tools import MapQuestionToSchemaException
from app.schemas.schemas import NaturalLanguageQuery, NaturalLanguageQueryResponse, GSQLQueryInfo
from app.log import req_id_cv

LLM_SERVICE = os.getenv("LLM_CONFIG")
DB_CONFIG = os.getenv("DB_CONFIG")

with open(LLM_SERVICE, "r") as f:
    llm_config = json.load(f)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


security = HTTPBasic()

logger = logging.getLogger(__name__)

if llm_config["embedding_service"]["embedding_model_service"].lower() == "openai":
    embedding_service = OpenAI_Embedding(llm_config["embedding_service"])
elif llm_config["embedding_service"]["embedding_model_service"].lower() == "azure":
    embedding_service = AzureOpenAI_Ada002(llm_config["embedding_service"])
elif llm_config["embedding_service"]["embedding_model_service"].lower() == "vertexai":
    embedding_service = VertexAI_PaLM_Embedding(llm_config["embedding_service"])
else:
    raise Exception("Embedding service not implemented")


embedding_store = FAISS_EmbeddingStore(embedding_service)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    req_id = str(uuid.uuid4())
    logger.info(f"{request.url.path} ENTRY request_id={req_id}")
    req_id_cv.set(req_id)
    start_time = time.time()
    
    response = await call_next(request)
    
    process_time = (time.time() - start_time) * 1000
    formatted_process_time = '{0:.2f}'.format(process_time)
    logger.info(f"{request.url.path} EXIT request_id={req_id} completed_in={formatted_process_time}ms status_code={response.status_code}")
    
    return response

def get_db_connection(graphname, credentials: Annotated[HTTPBasicCredentials, Depends(security)]) -> TigerGraphConnection:
    with open(DB_CONFIG, "r") as config_file:
        config = json.load(config_file)
        
    conn = TigerGraphConnection(
        host=config["hostname"],
        username = credentials.username,
        password = credentials.password,
        graphname = graphname,
    )

    if config["getToken"]:
        try:
            apiToken = conn._post(conn.restppUrl+"/requesttoken", authMode="pwd", data=str({"graph": conn.graphname}), resKey="results")["token"]
        except:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Basic"},
            )

        conn = TigerGraphConnection(
            host=config["hostname"],
            username = credentials.username,
            password = credentials.password,
            graphname = graphname,
            apiToken = apiToken
        )

    return conn

@app.get("/")
def read_root():
    return {"config": llm_config["model_name"]}


@app.post("/{graphname}/registercustomquery")
def register_query(graphname, query_info: GSQLQueryInfo, credentials: Annotated[HTTPBasicCredentials, Depends(security)]):
    logger.debug(f"/{graphname}/registercustomquery request_id={req_id_cv.get()} registering {query_info.function_header}")
    vec = embedding_service.embed_query(query_info.docstring)
    res = embedding_store.add_embeddings([(query_info.docstring, vec)], [{"function_header": query_info.function_header, 
                                                                          "description": query_info.description,
                                                                          "param_types": query_info.param_types,
                                                                          "custom_query": True}])
    return res

# TODO: RUD of CRUD with custom queries

@app.post("/{graphname}/retrievedocs")
def retrieve_docs(graphname, query: NaturalLanguageQuery, credentials: Annotated[HTTPBasicCredentials, Depends(security)], top_k:int = 3):
    # TODO: Better polishing of this response
    logger.debug_pii(f"/{graphname}/retrievedocs request_id={req_id_cv.get()} top_k={top_k} question={query.query}")
    tmp = str(embedding_store.retrieve_similar(embedding_service.embed_query(query.query), top_k=top_k))
    return tmp


@app.post("/{graphname}/query")
def retrieve_answer(graphname, query: NaturalLanguageQuery, conn: TigerGraphConnection = Depends(get_db_connection)) -> NaturalLanguageQueryResponse:
    logger.debug_pii(f"/{graphname}/query request_id={req_id_cv.get()} question={query.query}")
    with open(DB_CONFIG, "r") as config_file:
        config = json.load(config_file)

    conn.customizeHeader(timeout=config["default_timeout"]*1000, responseSize=50000000)
    logger.debug(f"/{graphname}/query request_id={req_id_cv.get()} database connection created")

    if llm_config["completion_service"]["llm_service"].lower() == "openai":
        logger.debug(f"/{graphname}/query request_id={req_id_cv.get()} llm_service=openai agent created")
        agent = TigerGraphAgent(OpenAI(llm_config["completion_service"]), conn, embedding_service, embedding_store)
    elif llm_config["completion_service"]["llm_service"].lower() == "azure":
        logger.debug(f"/{graphname}/query request_id={req_id_cv.get()} llm_service=azure agent created")
        agent = TigerGraphAgent(AzureOpenAI(llm_config["completion_service"]), conn, embedding_service, embedding_store)
    elif llm_config["completion_service"]["llm_service"].lower() == "sagemaker":
        logger.debug(f"/{graphname}/query request_id={req_id_cv.get()} llm_service=sagemaker agent created")
        agent = TigerGraphAgent(AWS_SageMaker_Endpoint(llm_config["completion_service"]), conn, embedding_service, embedding_store)
    elif llm_config["completion_service"]["llm_service"].lower() == "vertexai":
        logger.debug(f"/{graphname}/query request_id={req_id_cv.get()} llm_service=vertexai agent created")
        agent = TigerGraphAgent(GoogleVertexAI(llm_config["completion_service"]), conn, embedding_service, embedding_store)
    else:
        logger.error(f"/{graphname}/query request_id={req_id_cv.get()} agent creation failed due to invalid llm_service")
        raise Exception("LLM Completion Service Not Supported")

    resp = NaturalLanguageQueryResponse

    try:
        steps = agent.question_for_agent(query.query)
        logger.debug(f"/{graphname}/query request_id={req_id_cv.get()} agent executed")
        try:
            function_call = steps["intermediate_steps"][-1][-1].split("Function ")[1].split(" produced")[0]
            res = steps["intermediate_steps"][-1][-1].split("the result ")[-1]
            resp.natural_language_response = steps["output"]
            resp.query_sources = {"function_call": function_call,
                                "result": json.loads(res)}
            resp.answered_question = True
        except Exception as e:
            resp.natural_language_response = steps["output"]
            resp.query_sources = {"agent_history": str(steps)}
            resp.answered_question = False
            logger.warn(f"/{graphname}/query request_id={req_id_cv.get()} agent execution failed due to unknown exception")
    except MapQuestionToSchemaException as e:
        resp.natural_language_response = ""
        resp.query_sources = {}
        resp.answered_question = False
        logger.warn(f"/{graphname}/query request_id={req_id_cv.get()} agent execution failed due to MapQuestionToSchemaException")
    except Exception as e:
        resp.natural_language_response = ""
        resp.query_sources = {}
        resp.answered_question = False
        logger.warn(f"/{graphname}/query request_id={req_id_cv.get()} agent execution failed due to unknown exception")
    return resp

@app.get("/{graphname}/chat")
async def chat(graphname):
    return HTMLResponse("""
                        <!DOCTYPE html>
                        <html lang="en">
                        <head>
                            <meta charset="UTF-8">
                            <meta name="viewport" content="width=device-width, initial-scale=1.0">
                            <title>WebSocket Chat</title>
                            <style>
                                body {
                                    font-family: Arial, sans-serif;
                                    display: flex;
                                    flex-direction: column;
                                    align-items: center;
                                    height: 100vh;
                                    margin: 0;
                                }
                                .container {
                                    text-align: center;
                                    margin-bottom: 20px;
                                }
                                #chatBox {
                                    width: 400px;
                                    height: 300px;
                                    border: 1px solid #ccc;
                                    overflow: auto;
                                    padding: 10px;
                                    margin-bottom: 10px;
                                }
                                input {
                                    padding: 10px;
                                    margin: 5px;
                                }
                                button {
                                    padding: 10px;
                                    background-color: #4CAF50;
                                    color: white;
                                    border: none;
                                    cursor: pointer;
                                }
                            </style>
                        </head>
                        <body>
                            <div class="container">
                                <h2>WebSocket Chat</h2>
                                <div id="chatBox"></div>
                                <form id="authForm">
                                    <label for="username">Username:</label>
                                    <input type="text" id="username" name="username" required>
                                    <br>
                                    <label for="password">Password:</label>
                                    <input type="password" id="password" name="password" required>
                                    <br>
                                    <button type="button" onclick="authenticate()">Authenticate</button>
                                </form>
                                <form id="chatForm" style="display: none;">
                                    <label for="message">Message:</label>
                                    <input type="text" id="message" name="message" required>
                                    <br>
                                    <button type="button" onclick="sendMessage()">Send Message</button>
                                </form>
                            </div>

                            <script>
                                var websocket;

                                function authenticate() {
                                    var username = document.getElementById("username").value;
                                    var password = document.getElementById("password").value;

                                    // After authentication, establish a WebSocket connection
                                    establishWebSocket(username, password);
                                }

                                function establishWebSocket(username, password) {
                                    // Replace 'your_server_endpoint' with the actual WebSocket endpoint
                                    websocket = new WebSocket("ws://localhost:8000/chat_ws");

                                    websocket.onopen = function (event) {
                                        console.log("WebSocket connection opened");
                                        document.getElementById("authForm").style.display = "none";
                                        document.getElementById("chatForm").style.display = "block";
                                    };

                                    websocket.onmessage = function (event) {
                                        var chatBox = document.getElementById("chatBox");
                                        chatBox.innerHTML += event.data + "<br>";
                                        chatBox.scrollTop = chatBox.scrollHeight;
                                    };

                                    websocket.onclose = function (event) {
                                        console.log("WebSocket connection closed");
                                        alert("WebSocket connection closed. Please refresh the page to reconnect.");
                                    };
                                }

                                function sendMessage() {
                                    var messageInput = document.getElementById("message");
                                    var message = messageInput.value;

                                    // Send the message through the WebSocket connection
                                    websocket.send(message);

                                    // Display the sent message in the chat box
                                    var chatBox = document.getElementById("chatBox");
                                    chatBox.innerHTML += "You: " + message + "<br>";
                                    chatBox.scrollTop = chatBox.scrollHeight;

                                    // Clear the input field
                                    messageInput.value = "";
                                }
                            </script>
                        </body>
                        </html>

                        """)

@app.websocket("/{graphname}/chat_ws")
async def websocket_chat(websocket: WebSocket, graphname, conn: TigerGraphConnection = Depends(get_db_connection)):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        query = retrieve_answer(graphname, data, conn)
        await websocket.send_text(f"Message text was: {query}")