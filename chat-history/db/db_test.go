package db

import (
	"fmt"
	"testing"

	"github.com/google/uuid"
)

const DB_NAME = "test.db"

/*
test all functions
test all functions with concurrent accesses
*/
func TestInitDB(t *testing.T) {
	tmp := t.TempDir()
	pth := fmt.Sprintf("%s/%s", tmp, DB_NAME)
	InitDB(pth)
	if db == nil {
		t.Fatalf("db must not be nil")
	}
}

func TestGetUserConversations(t *testing.T) {
	setupTest(t)

	convos := GetUserConversations("sam_pull")
	if l := len(convos); l != 2 {
		t.Fatalf("len of convos should be 2. It's: %d", l)
	}
	for _, c := range convos {
		if len(c.UserId) == 0 ||
			uuid.Validate(c.ConversationId.String()) != nil {
			t.Fatalf("convo invalid: %v", c)
		}
	}
}

func testGetUserConversationById(t *testing.T) {
	setupTest(t)
	convoId := "601529eb-4927-4e24-b285-bd6b9519a951"
	messages := GetUserConversationById("sam_pull", convoId)
	for _, m := range messages {
		if uuid.Validate(m.ConversationId.String()) != nil || // not a valid conversation id
			uuid.Validate(m.MessageId.String()) != nil || // not a valid message id
			(m.Role != "system" && m.Role != "user") || // not system or user
			m.Feedback > 2 { // not system or user
			t.Fatalf("message invalid: %v", m)
		}
	}
	convoId = "24176445-9b3a-4883-962d-b763485f2889"
	messages = GetUserConversationById("sam_pull", convoId)
	if l := len(messages); l > 0 {
		t.Fatalf("Messages should be empty. Found %d messages", l)
	}
}

func testUpdateConversationById_NewConvo(t *testing.T) {

}

// parallel tests
func atest(t *testing.T) {
	/*
	   set up a few goroutines to call the set and get funcs a bunch of times or for a set time
	   expect no errors
	   ensure that what was supposed to get written was written
	*/

}

/*
helper functions
*/
func setupTest(t *testing.T) {
	tmp := t.TempDir()
	pth := fmt.Sprintf("%s/%s", tmp, DB_NAME)
	InitDB(pth)
	populateDB()

	t.Cleanup(func() {
		db = nil
	})
}
