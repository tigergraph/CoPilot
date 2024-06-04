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
	DEV=true ./chat-history


