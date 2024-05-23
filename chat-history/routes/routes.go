package routes

import (
	"chat-history/db"
	"encoding/json"
	"net/http"
)

// TODO: test what happens if it panics here. Does the server fail or return error?
// FIXME: don't panic if json errs, respond
func GetUserConversations(w http.ResponseWriter, r *http.Request) {
	userId := r.PathValue("userId")

	conversations := db.GetUserConversations(userId)
	out, err := json.MarshalIndent(conversations, "", "  ")
	if err != nil {
		panic(err)
	}
	w.Write([]byte(out))
}

func GetConversation(w http.ResponseWriter, r *http.Request) {
	conversationId := r.PathValue("conversationId")
	conversations := db.GetUserConversationById(conversationId)
	out, err := json.MarshalIndent(conversations, "", "  ")
	if err != nil {
		panic(err)
	}
	w.Write([]byte(out))
}

func UpdateConversation(w http.ResponseWriter, r *http.Request) {
	conversationId := "" //TODO: get from req body
	conversations := db.UpdateConversationById(conversationId)
	out, err := json.MarshalIndent(conversations, "", "  ")
	if err != nil {
		panic(err)
	}
	w.Write([]byte(out))
}
