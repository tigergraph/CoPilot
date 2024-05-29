package routes

import (
	"bytes"
	"chat-history/db"
	"chat-history/structs"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/http/httptest"
	"os"
	"slices"
	"testing"

	"github.com/google/uuid"
)

const (
	USER     = "sam_pull"
	PASS     = "pass"
	CONVO_ID = "601529eb-4927-4e24-b285-bd6b9519a951"
)

// GetUserConversations
func TestGetUserConversations(t *testing.T) {
	// setup
	setupDB(t, false)
	mux := http.NewServeMux()
	mux.HandleFunc("GET /user/{userId}", GetUserConversations)

	// setup request
	req := httptest.NewRequest(http.MethodGet, fmt.Sprintf("/user/%s", USER), nil)
	resp := httptest.NewRecorder()
	auth := basicAuthSetup(USER, PASS)
	req.Header.Add("Authorization", fmt.Sprintf("Basic %s", auth))

	// call
	mux.ServeHTTP(resp, req)

	// assert results
	if resp.Code != 200 {
		body, _ := io.ReadAll(resp.Body)
		fmt.Println(string(body))
		t.Fatalf("Response code should be 200. It is: %v", resp.Code)
	}
}

func TestGetUserConversations_401(t *testing.T) {
	// setup
	setupDB(t, false)
	mux := http.NewServeMux()
	mux.HandleFunc("GET /user/{userId}", GetUserConversations)

	// setup request
	req := httptest.NewRequest(http.MethodGet, fmt.Sprintf("/user/%s", USER), nil)
	resp := httptest.NewRecorder()

	// call
	mux.ServeHTTP(resp, req)

	// assert results
	if resp.Code != 401 {
		body, _ := io.ReadAll(resp.Body)
		fmt.Println(string(body))
		t.Fatalf("Response code should be 401. It is: %v", resp.Code)
	}

}

func TestGetUserConversations_403(t *testing.T) {
	// setup
	setupDB(t, false)
	mux := http.NewServeMux()
	mux.HandleFunc("GET /user/{userId}", GetUserConversations)

	// setup request
	req := httptest.NewRequest(http.MethodGet, fmt.Sprintf("/user/%s", USER), nil)
	resp := httptest.NewRecorder()
	auth := basicAuthSetup("asdf", PASS)
	req.Header.Add("Authorization", fmt.Sprintf("Basic %s", auth))

	// call
	mux.ServeHTTP(resp, req)

	// assert results
	if resp.Code != 403 {
		body, _ := io.ReadAll(resp.Body)
		fmt.Println(string(body))
		t.Fatalf("Response code should be 403. It is: %v", resp.Code)
	}
}

// GetConversation
func TestGetConversation(t *testing.T) {
	// setup
	setupDB(t, true)
	mux := http.NewServeMux()
	mux.HandleFunc("GET /conversation/{conversationId}", GetConversation)

	// setup request
	req := httptest.NewRequest(http.MethodGet, fmt.Sprintf("/conversation/%s", CONVO_ID), nil)
	resp := httptest.NewRecorder()
	auth := basicAuthSetup(USER, PASS)
	req.Header.Add("Authorization", fmt.Sprintf("Basic %s", auth))

	// call
	mux.ServeHTTP(resp, req)

	// assert results
	// body, _ := io.ReadAll(resp.Body)
	// fmt.Println(string(body))
	if resp.Code != 200 {
		body, _ := io.ReadAll(resp.Body)
		fmt.Println(string(body))
		t.Fatalf("Response code should be 200. It is: %v", resp.Code)
	}
}

func TestGetConversation_401(t *testing.T) {
	// setup
	setupDB(t, false)
	mux := http.NewServeMux()
	mux.HandleFunc("GET /conversation/{conversationId}", GetConversation)

	// setup request
	req := httptest.NewRequest(http.MethodGet, fmt.Sprintf("/conversation/%s", CONVO_ID), nil)
	resp := httptest.NewRecorder()

	// call
	mux.ServeHTTP(resp, req)

	// assert results
	if resp.Code != 401 {
		body, _ := io.ReadAll(resp.Body)
		fmt.Println(string(body))
		t.Fatalf("Response code should be 401. It is: %v", resp.Code)
	}

}

// UpdateConversation
func TestUpdateConversation_FirstMessage(t *testing.T) {
	// setup
	setupDB(t, false)
	mux := http.NewServeMux()
	mux.HandleFunc("POST /conversation/", UpdateConversation)

	// setup request
	convoId := uuid.New()
	msg := structs.Message{
		ConversationId: convoId,
		MessageId:      uuid.New(),
		ParentId:       nil,
		ModelName:      "GPT-4o",
		Content:        "Hello, world",
		Role:           structs.UserRole,
		Feedback:       structs.NoFeedback,
		Comment:        "",
	}
	bmsg, err := json.Marshal(msg)
	if err != nil {
		panic(err)
	}
	req := httptest.NewRequest(http.MethodPost, "/conversation/", bytes.NewReader(bmsg))
	auth := basicAuthSetup(USER, PASS)
	req.Header.Add("Authorization", fmt.Sprintf("Basic %s", auth))
	resp := httptest.NewRecorder()

	// call
	mux.ServeHTTP(resp, req)

	// assert results
	b, _ := io.ReadAll(resp.Body)
	var c structs.Conversation
	err = json.Unmarshal(b, &c)
	if err != nil {
		panic(err)
	}
	if resp.Code != 200 {
		fmt.Println("Body:", string(b))
		t.Fatalf("Response code should be 200. It is: %v", resp.Code)
	}
	// check that the conversation has 1 messages and the latest one is the one we just wrote
	messages := db.GetUserConversationById("sam_pull", convoId.String())

	m := messages[len(messages)-1]
	if len(messages) != 1 ||
		!messageEquals(m, msg) {
		t.Fatal("the message was not stored correctly")
	}
}

func TestUpdateConversation_nthMessage(t *testing.T) {
	// setup
	setupDB(t, true)
	mux := http.NewServeMux()
	mux.HandleFunc("POST /conversation/", UpdateConversation)

	// setup request
	// get last message in convo
	messages := db.GetUserConversationById("sam_pull", CONVO_ID)
	slices.SortFunc(messages, func(a, b structs.Message) int {
		// cmp(a, b) return a negative number when a < b, a positive number when a > b and zero when a == b.
		if a.UpdatedAt.UnixMilli() < b.UpdatedAt.UnixMilli() {
			return -1
		} else if a.UpdatedAt.UnixMilli() > b.UpdatedAt.UnixMilli() {
			return 1
		}
		return 0
	})

	msg := structs.Message{
		ConversationId: uuid.MustParse(CONVO_ID),
		MessageId:      uuid.New(),
		ParentId:       &messages[len(messages)-1].MessageId,
		ModelName:      "GPT-4o",
		Content:        "Hello, how may I help you?",
		Role:           structs.UserRole,
		Feedback:       structs.ThumbsUp,
		Comment:        "This comment is not blank",
	}
	bmsg, err := json.Marshal(msg)
	if err != nil {
		panic(err)
	}
	req := httptest.NewRequest(http.MethodPost, "/conversation/", bytes.NewReader(bmsg))
	resp := httptest.NewRecorder()
	auth := basicAuthSetup(USER, PASS)
	req.Header.Add("Authorization", fmt.Sprintf("Basic %s", auth))

	// call
	mux.ServeHTTP(resp, req)

	// assert results
	b, _ := io.ReadAll(resp.Body)
	var c structs.Conversation
	err = json.Unmarshal(b, &c)
	if err != nil {
		panic(err)
	}
	if resp.Code != 200 {
		body, _ := io.ReadAll(resp.Body)
		fmt.Println(string(body))
		t.Fatalf("Response code should be 200. It is: %v", resp.Code)
	}

	// check that the conversation has 3 messages and the latest one is the one we just wrote
	messages = db.GetUserConversationById("sam_pull", CONVO_ID)
	slices.SortFunc(messages, func(a, b structs.Message) int {
		// cmp(a, b) return a negative number when a < b, a positive number when a > b and zero when a == b.
		if a.UpdatedAt.UnixMilli() < b.UpdatedAt.UnixMilli() {
			return -1
		} else if a.UpdatedAt.UnixMilli() > b.UpdatedAt.UnixMilli() {
			return 1
		}
		return 0
	})

	m := messages[len(messages)-1]
	if len(messages) != 3 ||
		!messageEquals(m, msg) {
		fmt.Println(m.ConversationId == msg.ConversationId)
		fmt.Println(m.MessageId == msg.MessageId)
		fmt.Println(m.ParentId == msg.ParentId)
		fmt.Println(m.ModelName == msg.ModelName)
		fmt.Println(m.Content == msg.Content)
		fmt.Println(m.Role == msg.Role)
		fmt.Println(m.Feedback == msg.Feedback)
		fmt.Println(m.Comment == msg.Comment)
		t.Fatal("the message was not stored correctly")
	}
}
func messageEquals(m, msg structs.Message) bool {
	if m.ConversationId == msg.ConversationId &&
		m.MessageId == msg.MessageId &&
		(m.ParentId == msg.ParentId || m.ParentId.String() == msg.ParentId.String()) &&
		m.ModelName == msg.ModelName &&
		m.Content == msg.Content &&
		m.Role == msg.Role &&
		m.Feedback == msg.Feedback &&
		m.Comment == msg.Comment {
		return true
	}
	return false
}

// func TestUpdateConversation_SplitConvo(t *testing.T) {
// 	// setup
// 	setupDB(t, true)
// 	mux := http.NewServeMux()
// 	mux.HandleFunc("POST /conversation/", UpdateConversation)
//
// 	// setup request
// 	// msg:=structs.Message{}
// 	req := httptest.NewRequest(http.MethodPost, "/conversation/%s", nil)
// 	resp := httptest.NewRecorder()
// 	auth := basicAuthSetup(USER, PASS)
// 	req.Header.Add("Authorization", fmt.Sprintf("Basic %s", auth))
//
// 	// call
// 	mux.ServeHTTP(resp, req)
//
// 	// assert results
// 	// body, _ := io.ReadAll(resp.Body)
// 	// fmt.Println(string(body))
// 	if resp.Code != 200 {
// 		body, _ := io.ReadAll(resp.Body)
// 		fmt.Println(string(body))
// 		t.Fatalf("Response code should be 200. It is: %v", resp.Code)
// 	}
// }

// helpers
func basicAuthSetup(user, pass string) string {
	return base64.StdEncoding.EncodeToString([]byte(fmt.Sprintf("%s:%s", user, pass)))
}
func setupDB(t *testing.T, populateDB bool) {
	tmp := t.TempDir()
	pth := fmt.Sprintf("%s/%s", tmp, "test.db")
	if populateDB {
		os.Setenv("DEV", "true") // populate db
	} else {
		os.Setenv("DEV", "")
	}
	db.InitDB(pth)
}
