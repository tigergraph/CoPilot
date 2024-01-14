#!/bin/sh
export DB_CONFIG=../configs/db_config.json
export LOGLEVEL=INFO

# Set default values
llm_service="all"
schema="all"
use_wandb="true"

# Check if llm_service argument is provided
if [ "$#" -ge 1 ]; then
    llm_service="$1"
fi

# Check if schema argument is provided
if [ "$#" -ge 2 ]; then
    schema="$2"
fi

# Check if use_wandb argument is provided
if [ "$#" -ge 3 ]; then
    use_wandb="$3"
fi

# Define the mapping of Python script names to JSON config file names
azure_gpt35_script="test_azure_gpt35_turbo_instruct.py"
azure_gpt35_config="../configs/azure_llm_config.json"
    
openai_gpt35_script="test_openai_gpt35-turbo.py"
openai_gpt35_config="../configs/openai_gpt3.5-turbo_config.json"

openai_gpt4_script="test_openai_gpt4.py"
openai_gpt4_config="../configs/openai_gpt4_config.json"

gcp_textbison_script="test_gcp_text-bison.py"
gcp_textbison_config="../configs/gcp_text-bison_config.json"

# Function to execute a service
execute_service() {
    local service="$1"
    local config_file="$2"

    # Export the path to the config file as an environment variable
    export LLM_CONFIG="$config_file"

    if [ "$use_wandb" = "true" ]; then
        python "$service" --schema "$schema"
    else
        python "$service" --schema "$schema" --no-wandb
    fi

    # Unset the environment variable after the Python script execution
    unset CONFIG_FILE_PATH
}

# Check the value of llm_service and execute the corresponding Python script(s)
case "$llm_service" in
    "azure_gpt35")
        execute_service "$azure_gpt35_script" "$azure_gpt35_config"
        ;;
    "openai_gpt35")
        execute_service "$openai_gpt35_script" "$openai_gpt35_config"
        ;;
    "openai_gpt4")
        execute_service "$openai_gpt4_script" "$openai_gpt4_config"
        ;;
    "gcp_textbison")
        execute_service "$gcp_textbison_script" "$gcp_textbison_config"
        ;;
    "all")
        echo "Executing all services..."
        for service_script_pair in "$azure_gpt35_script $azure_gpt35_config" "$openai_gpt35_script $openai_gpt35_config" "$openai_gpt4_script $openai_gpt4_config" "$gcp_textbison_script $gcp_textbison_config"; do
            execute_service $service_script_pair
        done
        ;;
    *)
        echo "Unknown llm_service: $llm_service"
        exit 1
        ;;
esac

python create_wandb_report.py

