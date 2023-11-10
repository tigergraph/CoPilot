#!/bin/sh
export LLM_CONFIG=configs/azure_llm_config.json
python test_azure_gpt3.5_turbo_instruct.py
export LLM_CONFIG=configs/openai_llm_config.json
python test_openai_davinci-003.py
export LLM_CONFIG=configs/gcp_palm_config.json
python test_gcp_text-bison.py

