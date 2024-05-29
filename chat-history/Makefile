build:
	go build -v -race

test:
	# go test ./... -v
	go test ./... 

clean:
	-rm test.db chat-history

run: clean test build
	clear
	DEV=true ./chat-history


