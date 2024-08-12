build:
	go build -v -race

test:
	go test ./... 

# t:
# 	go clean -testcache
# 	# go test ./routes -v -run ".*_Merged.*"
# 	go test ./db -v -run ".*Parallel.*"

clean:
	-rm chats.db chat-history logs.jsonl db.log

run: clean test build
	clear
	CONFIG_FILES="chat_config.json,db_config.json" DEV=true ./chat-history


