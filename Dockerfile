FROM continuumio/miniconda3

RUN apt-get update
RUN apt install -y build-essential

RUN conda create -n py39 python=3.9 pip
RUN echo "conda activate py39" > ~/.bashrc
ENV PATH /opt/conda/envs/env/bin:$PATH
RUN conda run -n py39 \ 
        conda install faiss-cpu -c pytorch
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

# 
CMD ["/opt/conda/envs/py39/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]