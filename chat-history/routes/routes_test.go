package routes

import (
	"chat-history/db"
	"encoding/base64"
	"fmt"
	"io"
	"net/http"
	"net/http/httptest"
	"os"
	"testing"
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
