export DEV:=true
build:
	go build -v -race

test:
	go test ./...

clean:
	-rm test.db chat-history

run: clean test build
	clear
	./chat-history


