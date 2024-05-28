rm test.db
rm chat-history
clear
# go test ./... -v ||
go test ./...  ||
	exit 1
# exit 0
export DEV='true'
echo "building"
go build -race &&
	clear &&
	./chat-history
