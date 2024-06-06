FROM python:3.11.8
WORKDIR /code

 
COPY requirements.txt requirements.txt

 
RUN apt-get update && apt-get upgrade -y
RUN pip install -r requirements.txt

COPY ./app /code/app

ENV LLM_CONFIG="/code/configs/llm_config.json"
ENV DB_CONFIG="/code/configs/db_config.json"
ENV MILVUS_CONFIG="/code/configs/milvus_config.json"
ENV LOGLEVEL="INFO"

EXPOSE 8001
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
