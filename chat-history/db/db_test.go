package db

import (
	"chat-history/structs"
	"fmt"
	"slices"
	"sync"
	"testing"

	"github.com/google/uuid"
)

const (
	DB_NAME = "test.db"

	USER = "sam_pull"
)

/*
test all functions
test all functions with concurrent accesses
*/
func TestInitDB(t *testing.T) {
	tmp := t.TempDir()
	pth := fmt.Sprintf("%s/%s", tmp, DB_NAME)
	InitDB(pth, fmt.Sprintf("%s/test.log", tmp))
	if db == nil {
		t.Fatalf("db must not be nil")
	}
}

func TestGetUserConversations(t *testing.T) {
	setupTest(t, true)

	convos := GetUserConversations(USER)
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

func TestGetUserConversationById(t *testing.T) {
	setupTest(t, true)
	convoId := "601529eb-4927-4e24-b285-bd6b9519a951"
	messages := GetUserConversationById(USER, convoId)
	for _, m := range messages {
		if uuid.Validate(m.ConversationId.String()) != nil || // not a valid conversation id
			uuid.Validate(m.MessageId.String()) != nil || // not a valid message id
			(m.Role != "system" && m.Role != "user") || // not system or user
			m.Feedback > 2 { // not system or user
			t.Fatalf("message invalid: %v", m)
		}
	}
	convoId = "24176445-9b3a-4883-962d-b763485f2889"
	messages = GetUserConversationById(USER, convoId)
	if l := len(messages); l > 0 {
		t.Fatalf("Messages should be empty. Found %d messages", l)
	}
}

// parallel tests
func TestParallelWrites(t *testing.T) {
	/*
			   set up a few goroutines to call the set and get funcs a bunch of times or for a set time
			   expect no errors
			   ensure that what was supposed to get written was written

		n workers writing 100 messages to 5 conversations each
	*/
	setupTest(t, false)

	var wg sync.WaitGroup
	n := 10

	// init n convos
	convoIds := make(chan string, n)
	wg.Add(n)
	for range n {
		go func(ch chan string) {
			defer wg.Done()
			convoId := uuid.New()
			convoIds <- convoId.String()

			var prev *structs.Message
			for i := range 100 {
				var parentID *uuid.UUID
				if prev != nil {
					parentID = &prev.MessageId
				}
				msg := structs.Message{
					ConversationId: convoId,
					MessageId:      uuid.New(),
					ParentId:       parentID,
					ModelName:      "GPT-4o",
					Content:        "Hello, how may I help you?",
					Role:           structs.UserRole,
					Feedback:       structs.ThumbsUp,
					Comment:        "This comment is not blank",
				}
				if i == 0 {
					_, err := NewConversation(USER, "", msg)
					if err != nil {
						panic(err)
					}
				} else if _, err := UpdateConversationById(msg); err != nil {
					panic(err)
				}
				prev = &msg
			}
		}(convoIds)
	}
	wg.Wait()
	close(convoIds)
	// check each convo
	for c := range convoIds {
		convo := GetUserConversationById(USER, c)
		// sort the convo and make sure it is linear
		slices.SortFunc(convo, func(a, b structs.Message) int {
			if a.ID < b.ID {
				return -1
			} else if a.ID > b.ID {
				return 1
			}
			return 0
		})

		// fmt.Println("..", convo[0])
		if convo[0].ParentId != nil {
			t.Fatal("conversation history is incorrect. First message should not have a parent")
		}
		// make sure that current message's parent is the previous message
		prev := convo[0].MessageId
		for _, m := range convo[1:] {
			// fmt.Println("..", m)
			// if m.ParentId.String() != prev.MessageId.String() {
			if m.ParentId.String() != prev.String() {
				t.Fatal("conversation history is incorrect ")
			}
			prev = m.MessageId
		}
	}
}

/*
helper functions
*/
func setupTest(t *testing.T, pop bool) {
	tmp := t.TempDir()
	pth := fmt.Sprintf("%s/%s", tmp, DB_NAME)
	InitDB(pth, fmt.Sprintf("%s/test.log", tmp))
	if pop {
		populateDB()
	}

	t.Cleanup(func() {
		db = nil
	})
}
