FROM python:3.11.8-bullseye
WORKDIR /code

COPY common/requirements.txt requirements.txt
 
RUN apt-get update && apt-get upgrade -y
RUN pip install -r requirements.txt

COPY eventual-consistency-service/app /code
COPY common /code/common

ENV LLM_CONFIG="/llm_config.json"
ENV DB_CONFIG="/db_config.json"
ENV MILVUS_CONFIG="/milvus_config.json"
ENV LOGLEVEL="INFO"

EXPOSE 8001
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
