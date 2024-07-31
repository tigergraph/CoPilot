package routes

import (
	"bytes"
	"chat-history/config"
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
	"strings"
	"testing"

	"github.com/google/uuid"
)

const (
	USER     = "sam_pull"
	PASS     = "sam_pull"
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

func TestMergeMessageHistory(t *testing.T) {
	// setup
	splitConvo := createSplitConvo()
	setupDB(t, false)
	db.NewConversation(USER, "split convo", splitConvo[0])
	for _, m := range splitConvo[1:] {
		_, err := db.UpdateConversationById(m)
		if err != nil {
			panic(err)
		}
	}
	splitConvo = db.GetUserConversationById("sam_pull", CONVO_ID)
	merged := mergeConversationHistory(splitConvo)
	slices.SortFunc(merged, func(a, b structs.Message) int {
		if a.ID < b.ID {
			return -1
		} else if a.ID > b.ID {
			return 1
		}
		return 0
	})

	// assert that merged history is same as known convo path
	correctConvoIDs := []uint{1, 2, 4, 7}
	for i, m := range merged {
		if correctConvoIDs[i] != m.ID {
			t.Fatalf("The merged conversation is not correct. ID:%v != ID:%v", correctConvoIDs[i], m.ID)
		}
	}
}

func TestGetConversation_SplitMessageHistory(t *testing.T) {
	// setup
	splitConvo := createSplitConvo()
	setupDB(t, false)
	db.NewConversation(USER, "split convo", splitConvo[0])
	for _, m := range splitConvo[1:] {
		_, err := db.UpdateConversationById(m)
		if err != nil {
			panic(err)
		}
	}
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
	body, _ := io.ReadAll(resp.Body)
	fmt.Println(string(body))
	if resp.Code != 200 {
		body, _ := io.ReadAll(resp.Body)
		fmt.Println(string(body))
		t.Fatalf("Response code should be 200. It is: %v", resp.Code)
	}
}

func TestGetConversation_SplitMessageHistory_Merged(t *testing.T) {
	// setup
	splitConvo := createSplitConvo()
	setupDB(t, false)
	db.NewConversation(USER, "split convo", splitConvo[0])
	for _, m := range splitConvo[1:] {
		_, err := db.UpdateConversationById(m)
		if err != nil {
			panic(err)
		}
	}

	mux := http.NewServeMux()
	mux.HandleFunc("GET /conversation/{conversationId}", GetConversation)

	// setup request
	req := httptest.NewRequest(http.MethodGet, fmt.Sprintf("/conversation/%s?merge=true", CONVO_ID), nil)
	resp := httptest.NewRecorder()
	auth := basicAuthSetup(USER, PASS)
	req.Header.Add("Authorization", fmt.Sprintf("Basic %s", auth))

	// call
	mux.ServeHTTP(resp, req)

	// assert results
	body, _ := io.ReadAll(resp.Body)
	fmt.Println(string(body))
	if resp.Code != 200 {
		body, _ := io.ReadAll(resp.Body)
		fmt.Println(string(body))
		t.Fatalf("Response code should be 200. It is: %v", resp.Code)
	}
	// assert that merged history is same as known convo path
	var merged []structs.Message
	err := json.Unmarshal(body, &merged)
	if err != nil {
		panic(err)
	}
	correctConvoIDs := []uint{1, 2, 4, 7}
	for i, m := range merged {
		if correctConvoIDs[i] != m.ID {
			t.Fatalf("The merged conversation is not correct. ID:%v != ID:%v", correctConvoIDs[i], m.ID)
		}
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
		ParentId:       &messages[len(messages)-1].MessageId, // set the latest message as this message's parent
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

func TestExecuteGSQL(t *testing.T) {

	os.Setenv("CONFIG_FILES", "../chat_config.json,../db_config.json")

	configPath := os.Getenv("CONFIG_FILES")
	// Split the paths into a slice
	configPaths := strings.Split(configPath, ",")

	cfg, err := config.LoadConfig(configPaths...)
	if err != nil {
		panic(err)
	}
	query := "SHOW USER"

	response, err := executeGSQL(cfg.TgDbHost, cfg.Username, cfg.Password, query, cfg.TgCloud)
	if err != nil {
		t.Fatalf("Failed to execute GSQL query: %v", err)
	}

	// Check for common errors or issues in the response
	if strings.Contains(response, "400 Bad Request") {
		t.Error("Received '400 Bad Request' error. Please check the query and server configuration.")
	}

	if strings.Contains(response, "401 Unauthorized") {
		t.Error("Received '401 Unauthorized' error. Please check the credentials and access permissions.")
	}

	if strings.Contains(response, "403 Forbidden") {
		t.Error("Received '403 Forbidden' error. The user may not have sufficient permissions to execute the query.")
	}

	if strings.Contains(response, "500 Internal Server Error") {
		t.Error("Received '500 Internal Server Error'. This indicates a server-side issue.")
	}

	// Add any additional checks on the response
	if response == "" {
		t.Error("Received empty response from GSQL query")
	}

	// Check if the response contains "Name" and "Global Roles"
	if !strings.Contains(response, "Name") {
		t.Error("Response does not contain 'Name'.")
	}

	if !strings.Contains(response, "Global Roles") {
		t.Error("Response does not contain 'Global Roles'.")
	}
}

func TestParseUserRoles(t *testing.T) {
	userInfo := `
  - Name: feedbackauthtest
    - Global Roles: globalobserver
    - Graph 'EarningsCallRAG' Roles: queryreader
    - Graph 'Transaction_Fraud' Roles: designer, queryreader
    - Graph 'pyTigerGraphRAG' Roles: queryreader, querywriter
    - Secret: ad9****v7p
      - Alias: AUTO_GENERATED_ALIAS_suv6mm5
      - GraphName: Transaction_Fraud
    - LastSuccessLogin: Mon Jul 22 06:57:29 UTC 2024
    - NextValidLogin: Mon Jul 22 06:57:29 UTC 2024
    - FailedAttempts: 0
    - ShowAlterPasswordWarning: false

  - Name: Lu Zhou
    - Global Roles: globalobserver
    - LastSuccessLogin: Tue Jul 23 16:35:45 UTC 2024
    - NextValidLogin: Tue Jul 23 16:35:45 UTC 2024
    - FailedAttempts: 0
    - ShowAlterPasswordWarning: false
	`

	expectedRoles := []string{"globalobserver"}

	roles := parseUserRoles(userInfo, "feedbackauthtest")

	fmt.Println("Extracted Roles:", roles)

	if len(roles) != len(expectedRoles) {
		t.Fatalf("expected %d roles, got %d", len(expectedRoles), len(roles))
	}

	for i, role := range expectedRoles {
		if roles[i] != role {
			t.Errorf("expected role %s, got %s", role, roles[i])
		}
	}
}

func TestGetFeedback(t *testing.T) {

	os.Setenv("CONFIG_FILES", "../chat_config.json,../db_config.json")

	setupDB(t, true)

	configPath := os.Getenv("CONFIG_FILES")
	// Split the paths into a slice
	configPaths := strings.Split(configPath, ",")

	cfg, err := config.LoadConfig(configPaths...)
	if err != nil {
		panic(err)
	}
	// Create a request with Basic Auth
	req, err := http.NewRequest("GET", "/get_feedback", nil)
	if err != nil {
		t.Fatal(err)
	}
	req.SetBasicAuth(cfg.Username, cfg.Password)

	// Record the response
	rr := httptest.NewRecorder()
	handler := http.HandlerFunc(GetFeedback(cfg.TgDbHost, cfg.ConversationAccessRoles, cfg.TgCloud))

	// Serve the request
	handler.ServeHTTP(rr, req)

	// Check the response status code
	if status := rr.Code; status != http.StatusOK {
		t.Errorf("handler returned wrong status code: got %v want %v", status, http.StatusOK)
	}

	// Check the response body for expected messages
	var messages []structs.Message
	if err := json.Unmarshal(rr.Body.Bytes(), &messages); err != nil {
		t.Errorf("Failed to parse response body: %v", err)
	}

	// Print the messages for debugging
	fmt.Println("Retrieved messages:", messages)
	// Validate that the messages are as expected
	expectedMessagesCount := 2 // Based on populateDB function
	if len(messages) != expectedMessagesCount {
		t.Errorf("Expected %d messages, got %d", expectedMessagesCount, len(messages))
	}

	// Additional checks to ensure the response contains the correct data
	if len(messages) > 0 {
		if messages[0].Content != "This is the first message, there is no parent" {
			t.Errorf("Unexpected message content: %v", messages[0].Content)
		}
	}
}

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
	log := fmt.Sprintf("%s/test.log", tmp)
	db.InitDB(pth, log)
}

func createSplitConvo() []structs.Message {
	/*
			       - 3
			   - 1 2 3
		x - 0 ↕︎
			   - 1 2
	*/
	msg := structs.Message{
		ConversationId: uuid.MustParse(CONVO_ID),
		MessageId:      uuid.New(),
		ParentId:       nil,
		ModelName:      "GPT-4o",
		Content:        "message 0",
		Role:           structs.UserRole,
		Feedback:       structs.NoFeedback,
		Comment:        "",
	}
	msg.ID = 0
	convo := []structs.Message{msg}
	tmp := msg.MessageId.String()
	// branch 1
	for i := 1; i < 4; i++ {
		parent := uuid.MustParse(tmp)
		msg = structs.Message{
			ConversationId: uuid.MustParse(CONVO_ID),
			MessageId:      uuid.New(),
			ParentId:       &parent,
			ModelName:      "GPT-4o",
			Content:        fmt.Sprintf("message %d", i),
			Role:           structs.UserRole,
			Feedback:       structs.NoFeedback,
			Comment:        "branch 1",
		}
		msg.ID = uint(i)
		convo = append(convo, msg)
		tmp = msg.MessageId.String()
	}

	// branch 3 (off of branch 1)
	parent := uuid.MustParse(convo[len(convo)-2].MessageId.String())
	msg = structs.Message{
		ConversationId: uuid.MustParse(CONVO_ID),
		MessageId:      uuid.New(),
		ParentId:       &parent,
		ModelName:      "GPT-4o",
		Content:        fmt.Sprintf("message %d", 3),
		Role:           structs.UserRole,
		Feedback:       structs.NoFeedback,
		Comment:        "branch 3 latest message",
	}
	msg.ID = uint(4)
	convo = append(convo, msg)

	// branch 2
	tmp = convo[0].MessageId.String()
	for i := 1; i < 3; i++ {
		parent := uuid.MustParse(tmp)
		msg = structs.Message{
			ConversationId: uuid.MustParse(CONVO_ID),
			MessageId:      uuid.New(),
			ParentId:       &parent,
			ModelName:      "GPT-4o",
			Content:        fmt.Sprintf("message %d", i),
			Role:           structs.UserRole,
			Feedback:       structs.NoFeedback,
			Comment:        "branch 2",
		}
		msg.ID = uint(i)
		convo = append(convo, msg)
		tmp = msg.MessageId.String()
	}

	slices.SortFunc(convo, func(a, b structs.Message) int {
		if a.ID < b.ID {
			return -1
		} else if a.ID > b.ID {
			return 1
		}
		return 0
	})

	for i, m := range convo {
		m.Model = structs.Model{} // reset db metadata info
		convo[i] = m
	}
	return convo
}

func PrintMsgTree(convo []structs.Message) {
	adjList := map[string][]string{}
	for _, c := range convo {
		if c.ParentId == nil {
			continue
		}
		parent := c.ParentId.String()

		// if the parent exists in the map, append c, else create
		if v, prs := adjList[parent]; prs {
			adjList[parent] = append(v, c.MessageId.String())
		} else {
			adjList[parent] = []string{c.MessageId.String()}
		}
	}

	for k, v := range adjList {
		fmt.Println(k, v)
	}

}
