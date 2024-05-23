package main

import (
	"chat-history/db"
	"chat-history/routes"
	"net/http"

	"fmt"

	"github.com/go-chi/chi/v5/middleware"
)

type Middleware func(http.Handler) http.Handler

func chainMiddleware(handler http.Handler, middle ...Middleware) http.Handler {
	for _, m := range middle {
		handler = m(handler)
	}

	return handler
}

func main() {
	db.InitDB()
	router := http.NewServeMux()

	// Health check endpoint
	router.HandleFunc("GET /", func(w http.ResponseWriter, r *http.Request) {
		w.Write([]byte(`{"status":"OK"}`))
	})

	router.HandleFunc("GET /user/{userId}", routes.GetUserConversations)
	router.HandleFunc("GET /conversation/{conversationId}", routes.GetConversation)
	router.HandleFunc("POST /conversation/", routes.UpdateConversation)

	// create server with middleware
	port := ":8000"
	//FIXME: auth middleware
	handler := chainMiddleware(router, middleware.Logger)
	s := http.Server{Addr: port, Handler: handler}

	fmt.Printf("Server running on port %s\n", port)
	s.ListenAndServe()
}
