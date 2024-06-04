export LLM_CONFIG="./configs/llm_config.json"
export DB_CONFIG="./configs/db_config.json"
export MILVUS_CONFIG="./configs/milvus_config.json"
export LOGLEVEL="INFO"
export MILVUS_HOST="milvus-standalone"
export PATH_PREFIX=""
rm -rf ./tmp

clear
cd copilot/app
uvicorn main:app --reload
# uvicorn app.main:app --host 0.0.0.0

# docker compose build copilot
# docker rm -f copilot-copilot-1
# docker compose up -d
# docker logs copilot-copilot-1 -f
# docker compose stop
