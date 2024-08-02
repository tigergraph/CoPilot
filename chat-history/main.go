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
	configPath := os.Getenv("CONFIG_FILES")
	// Split the paths into a slice
	configPaths := strings.Split(configPath, ",")

	cfg, err := config.LoadConfig(map[string]string{
		"chatdb": configPaths[0],
		"tgdb":   configPaths[1],
	})
	if err != nil {
		panic(err)
	}
	db.InitDB(cfg.ChatDbConfig.DbPath, cfg.ChatDbConfig.DbLogPath)

	// make router
	router := http.NewServeMux()

	// Health check endpoint
	router.HandleFunc("GET /", func(w http.ResponseWriter, r *http.Request) {
		w.Write([]byte(`{"status":"OK"}`))
	})

	router.HandleFunc("GET /user/{userId}", routes.GetUserConversations)
	router.HandleFunc("GET /conversation/{conversationId}", routes.GetConversation)
	router.HandleFunc("POST /conversation", routes.UpdateConversation)
	router.HandleFunc("GET /get_feedback", routes.GetFeedback(cfg.TgDbConfig.Hostname, cfg.TgDbConfig.GsPort, cfg.ChatDbConfig.ConversationAccessRoles, cfg.TgDbConfig.TgCloud))

	// create server with middleware
	dev := strings.ToLower(os.Getenv("DEV")) == "true"
	var port string
	if dev {
		port = fmt.Sprintf("localhost:%s", cfg.ChatDbConfig.Port)
	} else {
		port = fmt.Sprintf(":%s", cfg.ChatDbConfig.Port)
	}

	handler := middleware.ChainMiddleware(router,
		middleware.Logger(), // recoverer already included from RequestLogger by default
		// middleware.Auth, // TODO: need auth server. --> go-chi/oauth can make server
	)
	s := http.Server{Addr: port, Handler: handler}

	fmt.Printf("Server running on port %s\n", port)
	s.ListenAndServe()
}
