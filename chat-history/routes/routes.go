package routes

import (
	"chat-history/db"
	"encoding/json"
	"fmt"
	"net/http"
)

// Get all of the conversations for a user
// "GET /user/{userId}"
func GetUserConversations(w http.ResponseWriter, r *http.Request) {
	userId := r.PathValue("userId")
	//TODO:
	// double check that this and auth header match

	conversations := db.GetUserConversations(userId)
	if out, err := json.MarshalIndent(conversations, "", "  "); err == nil {
		w.Write([]byte(out))
	} else {
		panic(err)
	}
}

// Get the contents of a conversation (list of messages)
// "GET /conversation/{conversationId}"
func GetConversation(w http.ResponseWriter, r *http.Request) {
	conversationId := r.PathValue("conversationId")
	userId, _, ok := r.BasicAuth()
	fmt.Println(userId)
	if ok {
		conversations := db.GetUserConversationById(userId, conversationId)
		if out, err := json.MarshalIndent(conversations, "", "  "); err == nil {
			w.Write([]byte(out))
		} else {
			panic(err)
		}
	} else {
		panic("idk") //TODO:
	}
}

// Update the contents of a conversation (i.e., add a message, or update it's feedback)
// "POST /conversation"
func UpdateConversation(w http.ResponseWriter, r *http.Request) {
	conversationId := "" //TODO: get from req body
	conversations := db.UpdateConversationById(conversationId)
	if out, err := json.MarshalIndent(conversations, "", "  "); err == nil {
		w.Write([]byte(out))
	} else {
		w.WriteHeader(500)
		w.Write([]byte(""))
	}
}
