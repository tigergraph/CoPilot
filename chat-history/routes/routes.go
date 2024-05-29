package routes

import (
	"chat-history/db"
	"chat-history/structs"
	"encoding/json"
	"fmt"
	"io"
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
		w.Header().Add("Content-Type", "application/json")
		w.Write([]byte(out))
	} else {
		panic(err)
	}
}

// Get the contents of a conversation (list of messages)
// "GET /conversation/{conversationId}"
func GetConversation(w http.ResponseWriter, r *http.Request) {
	conversationId := r.PathValue("conversationId")
	if userId, _, ok := r.BasicAuth(); ok {
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
	// extract the body
	body, err := io.ReadAll(r.Body)
	if err != nil {
		panic(err)
	}
	message := structs.Message{}
	err = json.Unmarshal(body, &message)
	if err != nil {
		panic(err)
	}

	// check if the conversation trying to be written to belongs to the user
	if user, _, ok := r.BasicAuth(); ok {
		userConvos := db.GetUserConversations(user)
		var conversation *structs.Conversation
		for _, c := range userConvos {
			if c.ConversationId == message.ConversationId {
				// write message to conversation
				conversation, err = db.UpdateConversationById(&message)
				if err != nil {
					panic(err)
				}
				break
			}
		}

		// no convsersation with that ID was found
		if conversation == nil {
			// create a new convo and write message to it
			// TODO: use an LLM to get the Name
			name := ""
			conversation, err = db.NewConversation(user, name, message)
			if err != nil {
				panic(err)
			}
		}

		if out, err := json.MarshalIndent(conversation, "", "  "); err == nil {
			// return the conversation metadata
			w.Header().Add("Content-Type", "application/json")
			w.Write([]byte(out))
		} else {
			panic(err)
		}
	} else {
		w.Header().Add("Content-Type", "application/json")
		w.WriteHeader(401)
		reason := []byte(`{"reason":"missing Authorization header"}`)
		w.Write(reason)
	}
}

// Basic auth helper
func auth(userId string, r *http.Request) (int, []byte, bool) {
	if usr, _, ok := r.BasicAuth(); !ok {
		reason := []byte(`{"reason":"missing Authorization header"}`)
		return 401, reason, false
	} else if userId != usr {
		reason := []byte(fmt.Sprintf(`{"reason":"%s is noot authorized to retrieve conversations for user %s"}`, usr, userId))
		return 403, reason, false
	}

	return 0, nil, true
}
