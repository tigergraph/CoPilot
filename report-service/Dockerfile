FROM python:3.11.9
WORKDIR /code

COPY report-service/requirements.txt requirements.txt
 
RUN apt-get update && apt-get upgrade -y
RUN pip install -r requirements.txt
 
COPY report-service/app /code
COPY common /code/common

ENV LLM_CONFIG="/llm_config.json"
ENV DB_CONFIG="/db_config.json"
ENV MILVUS_CONFIG="/milvus_config.json"
ENV LOGLEVEL="INFO"

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]
