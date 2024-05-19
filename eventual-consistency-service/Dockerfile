FROM python:3.11.8
WORKDIR /code

 
COPY ./requirements.txt /code/requirements.txt

 
RUN apt-get update && apt-get upgrade -y
RUN pip install -r /code/requirements.txt

 
COPY ./app /code/app

ENV LLM_CONFIG="/llm_config.json"
ENV DB_CONFIG="/db_config.json"
ENV MILVUS_CONFIG="/milvus_config.json"

# INFO, DEBUG, DEBUG_PII
ENV LOGLEVEL="INFO"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
