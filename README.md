# TigerGraph Natural Language Query Service

## Build the Dockerfile
```
docker build -t nlqs:0.1 .
```

## Run the Docker Image
```
docker run -d -v $(pwd)/configs/openai_gpt4_config.json:/llm_config.json -v $(pwd)/configs/db_config.json:/db_config.json --name nlqs -p 80:80 nlqs:0.1
```