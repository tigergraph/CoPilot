package routes

import (
	"chat-history/db"
	"encoding/json"
	"net/http"
)

func GetUserConversations(w http.ResponseWriter, r *http.Request) {
	userId := r.PathValue("userId")

	conversations := db.GetUserConversations(userId)
	if out, err := json.MarshalIndent(conversations, "", "  "); err == nil {
		w.Write([]byte(out))
	} else {
		panic(err)
	}
}

func GetConversation(w http.ResponseWriter, r *http.Request) {
	conversationId := r.PathValue("conversationId")
	conversations := db.GetUserConversationById(conversationId)
	if out, err := json.MarshalIndent(conversations, "", "  "); err == nil {
		w.Write([]byte(out))
	} else {
		panic(err)
	}
}

func UpdateConversation(w http.ResponseWriter, r *http.Request) {
	panic("oops")
	conversationId := "" //TODO: get from req body
	conversations := db.UpdateConversationById(conversationId)
	if out, err := json.MarshalIndent(conversations, "", "  "); err == nil {
		w.Write([]byte(out))
	} else {
		w.WriteHeader(500)
		w.Write([]byte(""))
	}
}
