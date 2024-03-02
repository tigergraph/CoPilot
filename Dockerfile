FROM continuumio/miniconda3

RUN apt-get update && apt-get install -y build-essential

# Create conda environment and install packages
RUN conda create -n py39 python=3.9 pip && \
    /bin/bash -c "source activate py39 && \
    conda install faiss-cpu -c pytorch"
# 
WORKDIR /code

# 
COPY ./requirements.txt /code/requirements.txt

# 
RUN /opt/conda/envs/py39/bin/pip install --no-cache-dir --upgrade -r /code/requirements.txt

# 
COPY ./app /code/app

ENV LLM_CONFIG="/llm_config.json"
ENV DB_CONFIG="/db_config.json"

# INFO, DEBUG, DEBUG_PII
ENV LOGLEVEL="INFO"

EXPOSE 80

# 
CMD ["/opt/conda/envs/py39/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]