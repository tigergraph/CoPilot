package routes

import (
	"chat-history/db"
	"chat-history/structs"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"slices"
	"strings"
)

// Get all of the conversations for a user
// "GET /user/{userId}"
func GetUserConversations(w http.ResponseWriter, r *http.Request) {
	userId := r.PathValue("userId")
	if _, code, reason, ok := auth(userId, r); !ok {
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
// "GET /conversation/{conversationId}?merge=bool"
func GetConversation(w http.ResponseWriter, r *http.Request) {
	conversationId := r.PathValue("conversationId")
	merge := strings.ToLower(r.URL.Query().Get("merge")) == "true"
	if userId, code, reason, ok := auth("", r); ok {
		conversation := db.GetUserConversationById(userId, conversationId)
		if merge {
			conversation = mergeConversationHistory(conversation)
		}
		if out, err := json.MarshalIndent(conversation, "", "  "); err == nil {
			w.Header().Add("Content-Type", "application/json")
			w.Write([]byte(out))
		} else {
			panic(err)
		}
	} else {
		w.Header().Add("Content-Type", "application/json")
		w.WriteHeader(code)
		w.Write(reason)
	}
}

// Returns a single branch of a conversation's history. The branch with the most recent message is always returned
func mergeConversationHistory(convo []structs.Message) []structs.Message {
	// TODO: report broken history (multiple nils) & cycle detection
	lookup := map[string]*structs.Message{} // store the parent of any given message, or nil if it's the first message
	var latest *structs.Message
	for _, m := range convo {
		lookup[m.MessageId.String()] = &m
		// if m is more recent than latest
		if latest == nil || latest.UpdatedAt.UnixMilli() < m.UpdatedAt.UnixMilli() {
			latest = &m
		}
	}

	merged := []structs.Message{}
	for latest != nil {
		merged = append(merged, *latest)
		if latest.ParentId == nil {
			break
		}
		latest = lookup[latest.ParentId.String()]
	}

	slices.SortFunc(merged, func(a, b structs.Message) int {
		if a.ID < b.ID {
			return -1
		} else if a.ID > b.ID {
			return 1
		}
		return 0
	})
	return merged
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
	if user, code, reason, ok := auth("", r); ok {
		userConvos := db.GetUserConversations(user)
		var conversation *structs.Conversation
		for _, c := range userConvos {
			if c.ConversationId == message.ConversationId {
				// write message to conversation
				conversation, err = db.UpdateConversationById(message)
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
		w.WriteHeader(code)
		w.Write(reason)
	}
}

// Basic auth helper
func auth(userId string, r *http.Request) (string, int, []byte, bool) {
	usr, _, ok := r.BasicAuth()
	if !ok {
		reason := []byte(`{"reason":"missing Authorization header"}`)
		return usr, 401, reason, false
	} else if userId != "" && userId != usr {
		reason := []byte(fmt.Sprintf(`{"reason":"%s is not authorized to retrieve conversations for user %s"}`, usr, userId))
		return usr, 403, reason, false
	}

	return usr, 0, nil, true
}

// executeGSQL sends a GSQL query to TigerGraph with basic authentication and returns the response
func executeGSQL(hostname, username, password, query, gsPort string) (string, error) {
	var requestURL string
	tgcloud := strings.Contains(hostname, "tgcloud")
	// Construct the URL for the GSQL query endpoint
	if tgcloud {
		requestURL = fmt.Sprintf("%s:443/gsqlserver/gsql/file", hostname)
	} else {
		requestURL = fmt.Sprintf("%s:%s/gsqlserver/gsql/file", hostname, gsPort)
	}
	// Prepare the query data
	data := url.QueryEscape(query) // Encode query using URL encoding
	reqBody := strings.NewReader(data)

	// Create the HTTP request
	req, err := http.NewRequest("POST", requestURL, reqBody)
	if err != nil {
		return "", err
	}

	// Set the required headers
	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")

	// Set up basic authentication
	auth := fmt.Sprintf("%s:%s", username, password)
	req.Header.Set("Authorization", "Basic "+base64.StdEncoding.EncodeToString([]byte(auth)))

	// Execute the request
	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	// Read and return the response body
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", err
	}

	return string(body), nil
}

// hasAdminAccess checks if the user's roles include any of the admin roles
func hasAdminAccess(userRoles []string, adminRoles []string) bool {
	for _, role := range userRoles {
		for _, adminRole := range adminRoles {
			if role == adminRole {
				return true
			}
		}
	}
	return false
}

// parseUserRoles extracts roles from the user information string
func parseUserRoles(userInfo string, userName string) []string {
	lines := strings.Split(userInfo, "\n")
	var roles []string
	var isUserSection bool

	for _, line := range lines {
		if strings.Contains(line, "Name:") {
			isUserSection = strings.Contains(line, userName)
		}
		if isUserSection && strings.Contains(line, "- Global Roles:") {
			parts := strings.Split(line, ":")
			if len(parts) > 1 {
				roles = append(roles, strings.Split(strings.TrimSpace(parts[1]), ", ")...)
			}
		}
	}

	return roles
}

// GetFeedback retrieves feedback data for conversations
// "Get /get_feedback"
func GetFeedback(hostname, gsPort string, conversationAccessRoles []string) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		usr, pass, ok := r.BasicAuth()
		if !ok {
			w.Header().Add("Content-Type", "application/json")
			w.WriteHeader(http.StatusUnauthorized)
			w.Write([]byte(`{"reason":"missing Authorization header"}`))
			return
		}

		// Verify if the user has the required role
		userInfo, err := executeGSQL(hostname, usr, pass, "SHOW USER", gsPort)
		if err != nil {
			reason := []byte(`{"reason":"failed to retrieve feedback data"}`)
			w.Header().Add("Content-Type", "application/json")
			w.WriteHeader(http.StatusInternalServerError)
			w.Write(reason)
			return
		}

		// Parse and check roles
		userRoles := parseUserRoles(userInfo, usr)
		if !hasAdminAccess(userRoles, conversationAccessRoles) {
			// Fetch chat history messages for this specific user
			conversations := db.GetUserConversations(usr)

			var allMessages []structs.Message

			for _, convo := range conversations {
				messages := db.GetUserConversationById(usr, convo.ConversationId.String())
				allMessages = append(allMessages, messages...)
			}
			// Marshal and write the response
			w.Header().Add("Content-Type", "application/json")
			w.WriteHeader(http.StatusOK)
			response, err := json.Marshal(allMessages)
			if err != nil {
				reason := []byte(`{"reason":"failed to marshal messages"}`)
				w.Header().Add("Content-Type", "application/json")
				w.WriteHeader(http.StatusInternalServerError)
				w.Write(reason)
				return
			}
			w.Write(response)
			return
		}

		// If the user has admin access, fetch all messages
		messages, err := db.GetAllMessages()
		if err != nil {
			reason := []byte(`{"reason":"failed to retrieve feedback data"}`)
			w.Header().Add("Content-Type", "application/json")
			w.WriteHeader(http.StatusInternalServerError)
			w.Write(reason)
			return
		}

		w.Header().Add("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		response, err := json.Marshal(messages)
		if err != nil {
			reason := []byte(`{"reason":"failed to marshal messages"}`)
			w.Header().Add("Content-Type", "application/json")
			w.WriteHeader(http.StatusInternalServerError)
			w.Write(reason)
			return
		}
		w.Write(response)
	}
}
