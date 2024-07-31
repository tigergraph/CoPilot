package main

import (
	"chat-history/config"
	"chat-history/db"
	"chat-history/middleware"
	"chat-history/routes"
	"fmt"
	"net/http"
	"os"
	"strings"
)

func main() {
	configPath := os.Getenv("CONFIG")
	config, err := config.LoadConfig(configPath)
	if err != nil {
		panic(err)
	}
	db.InitDB(config.DbPath, config.DbLogPath)

	// make router
	router := http.NewServeMux()

	// Health check endpoint
	router.HandleFunc("GET /", func(w http.ResponseWriter, r *http.Request) {
		w.Write([]byte(`{"status":"OK"}`))
	})

	router.HandleFunc("GET /user/{userId}", routes.GetUserConversations)
	router.HandleFunc("GET /conversation/{conversationId}", routes.GetConversation)
	router.HandleFunc("POST /conversation", routes.UpdateConversation)
	router.HandleFunc("GET /get_feedback", routes.GetFeedback(config.TgDbHost, config.ConversationAccessRoles, config.TgCloud))

	// create server with middleware
	dev := strings.ToLower(os.Getenv("DEV")) == "true"
	var port string
	if dev {
		port = fmt.Sprintf("localhost:%s", config.Port)
	} else {
		port = fmt.Sprintf(":%s", config.Port)
	}

	handler := middleware.ChainMiddleware(router,
		middleware.Logger(), // recoverer already included from RequestLogger by default
		// middleware.Auth, // TODO: need auth server. --> go-chi/oauth can make server
	)
	s := http.Server{Addr: port, Handler: handler}

	fmt.Printf("Server running on port %s\n", port)
	s.ListenAndServe()
}
