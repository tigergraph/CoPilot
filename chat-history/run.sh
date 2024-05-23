rm test.db
rm chat-history
echo "building"
go build -race &&
	clear &&
	./chat-history
