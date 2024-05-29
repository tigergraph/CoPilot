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
	if code, reason, ok := auth(userId, r); !ok {
		w.Header().Add("Content-Type", "application/json")
		w.WriteHeader(code)
		w.Write(reason)
		return
	}

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
	if ok {
		conversations := db.GetUserConversationById(userId, conversationId)
		if out, err := json.MarshalIndent(conversations, "", "  "); err == nil {
			w.Header().Add("Content-Type", "application/json")
			w.Write([]byte(out))
		} else {
			panic(err)
		}
	} else {
		reason := []byte(`{"reason":"user is not authorized"}`)
		w.Header().Add("Content-Type", "application/json")
		w.WriteHeader(401)
		w.Write(reason)
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

func auth(userId string, r *http.Request) (int, []byte, bool) {
	if usr, _, ok := r.BasicAuth(); !ok {
		reason := []byte(`{"reason":"user is not authorized"}`)
		return 401, reason, false
	} else if userId != usr {
		reason := []byte(fmt.Sprintf(`{"reason":"Not authorized to retrieve conversations for user %s"}`, userId))
		return 403, reason, false
	}

	return 0, nil, true
}
