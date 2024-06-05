#!/bin/bash
export DB_CONFIG=./configs/db_config.json
export MILVUS_CONFIG=./configs/milvus_config.json
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

# Define the m.ing of Python script names to JSON config file names
azure_gpt35_script="test_azure_gpt35_turbo_instruct.py"
azure_gpt35_config="./configs/azure_llm_config.json"

openai_gpt35_script="test_openai_gpt35-turbo.py"
openai_gpt35_config="./configs/openai_gpt3.5-turbo_config.json"

openai_gpt4_script="test_openai_gpt4.py"
openai_gpt4_config="./configs/openai_gpt4_config.json"

huggingface_phi3_script="test_huggingface_phi3.py"
huggingface_phi3_config="./configs/huggingface_severless_endpoint_phi3_config.json"

openai_gpt4o_script="test_openai_gpt4o.py"
openai_gpt4o_config="./configs/openai_gpt4o_config.json"

gcp_textbison_script="test_gcp_text-bison.py"
gcp_textbison_config="./configs/gcp_text-bison_config.json"

groq_mixtral_script="test_groq_mixtral8x7b.py"
groq_mixtral_config="./configs/groq_mixtral_config.json"

aws_bedrock_script="test_bedrock.py"
aws_bedrock_config="./configs/bedrock_config.json"

huggingface_llama3_script="test_huggingface_llama70b.py"
huggingface_llama3_config="./configs/huggingface_llama70b_config.json"

# Function to execute a service
execute_service() {
	local service="$1"
	local config_file="$2"
	cp $service test_service.py parse_test_config.py app

	# Export the path to the config file as an environment variable
	export LLM_CONFIG="$config_file"

	if [ $use_wandb = "true" ]; then
		python app/$service --schema $schema
	else
		python app/$service --schema $schema --no-wandb
	fi

	# Unset the environment variable after the Python script execution
	unset CONFIG_FILE_PATH
	rm app/$service app/test_service.py app/parse_test_config.py
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
"openai_gpt4o")
	execute_service "$openai_gpt4o_script" "$openai_gpt4o_config"
	;;
"gcp_textbison")
	execute_service "$gcp_textbison_script" "$gcp_textbison_config"
	;;
"huggingface_phi3")
	execute_service "$huggingface_phi3_script" "$huggingface_phi3_config"
	;;
"groq_mixtral")
	execute_service "$groq_mixtral_script" "$groq_mixtral_config"
	;;
"aws_bedrock")
	execute_service "$aws_bedrock_script" "$aws_bedrock_config"
	;;
"huggingface_llama3")
	execute_service "$huggingface_llama3_script" "$huggingface_llama3_config"
	;;
"all")
	echo "Executing all services..."
	for service_script_pair in "$azure_gpt35_script $azure_gpt35_config" \
		"$openai_gpt35_script $openai_gpt35_config" \
		"$openai_gpt4_script $openai_gpt4_config" \
		"$gcp_textbison_script $gcp_textbison_config" \
		"$groq_mixtral_script $groq_mixtral_config" \
		"$aws_bedrock_script $aws_bedrock_config" \
		"$openai_gpt4o_script $openai_gpt4o_config" \
		"$huggingface_llama3_script $huggingface_llama3_config" \
		"$huggingface_phi3_script $huggingface_phi3_config"; do
		execute_service $service_script_pair
	done
	;;
*)
	echo "Unknown llm_service: $llm_service"
	exit 1
	;;
esac

python create_wandb_report.py
