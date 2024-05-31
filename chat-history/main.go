package main

import (
	"chat-history/db"
	"chat-history/middleware"
	"chat-history/routes"
	"fmt"
	"net/http"
)

func main() {
	//init
	// config := config.LoadConfig()
	db.InitDB("chats.db", "db.log")

	// make router
	router := http.NewServeMux()

	// Health check endpoint
	router.HandleFunc("GET /", func(w http.ResponseWriter, r *http.Request) {
		w.Write([]byte(`{"status":"OK"}`))
	})

	router.HandleFunc("GET /user/{userId}", routes.GetUserConversations)
	router.HandleFunc("GET /conversation/{conversationId}", routes.GetConversation)
	router.HandleFunc("POST /conversation", routes.UpdateConversation)

	// create server with middleware
	port := "localhost:8000"

	handler := middleware.ChainMiddleware(router,
		middleware.Logger(), // recoverer already included from RequestLogger by default
		// middleware.Auth, // TODO: need auth server. --> go-chi/oauth can make server
	)
	s := http.Server{Addr: port, Handler: handler}

	fmt.Printf("Server running on port %s\n", port)
	s.ListenAndServe()
}
