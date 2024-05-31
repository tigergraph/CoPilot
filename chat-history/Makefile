build:
	go build -v -race

test:
	go test ./... 

t-merged:
	go clean -testcache
	go test ./routes -v -run ".*_Merged.*"

clean:
	-rm test.db chat-history

run: clean test build
	clear
	DEV=true ./chat-history


