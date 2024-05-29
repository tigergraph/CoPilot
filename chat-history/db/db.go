package db

import (
	"chat-history/structs"
	"fmt"
	"os"
	"strings"
	"sync"

	"github.com/google/uuid"

	"gorm.io/driver/sqlite"
	"gorm.io/gorm"
)

var (
	db *gorm.DB
	mu = sync.RWMutex{}
)

// Initialize the DB
func InitDB(dbPath string) {
	// TODO:
	//  log db stuff to file, too (in gorm config)

	chatHistDB, err := gorm.Open(sqlite.Open(dbPath), &gorm.Config{})
	if err != nil {
		panic("failed to connect database")
	}
	db = nil
	db = chatHistDB

	// Migrate the schema
	err = db.AutoMigrate(&structs.Conversation{}, &structs.Message{})
	if err != nil {
		panic(err)
	}
	// Create -- for testing only
	dev := strings.ToLower(os.Getenv("DEV"))
	if dev == "true" {
		fmt.Print("\nRUNNING IN DEV MODE\n\n")
		populateDB()
	}
}

func GetUserConversations(userId string) []structs.Conversation {
	mu.RLock()
	defer mu.RUnlock()

	convos := []structs.Conversation{}
	db.Where("user_id = ?", userId).Find(&convos)

	return convos
}

func GetUserConversationById(userId, conversatonId string) []structs.Message {
	messages := []structs.Message{}
	mu.RLock()
	defer mu.RUnlock()

	// ensure that conversatonId is a convo for this user
	convos := GetUserConversations(userId)
	for _, c := range convos {
		// conversaton belongs to this user. get the messages
		if c.ConversationId.String() == conversatonId {
			db.Where("conversation_id = ?", conversatonId).Find(&messages)
			break
		}
	}
	return messages
}

// TODO: doesn't take an ID. takes the request body and updates based on what's in there
func UpdateConversationById(conversatonId string) []structs.Conversation {
	mu.RLock()
	defer mu.RUnlock()

	convos := []structs.Conversation{}
	// db.Where("user_id = ?", conversatonId).Find(&convos)

	return convos
}

// Delete - delete product
// db.Delete(&convo, 1)
func populateDB() {
	mu.Lock()
	defer mu.Unlock()
	// init convos
	conv1 := uuid.MustParse("601529eb-4927-4e24-b285-bd6b9519a951")
	db.Create(&structs.Conversation{UserId: "rrossmiller", ConversationId: conv1, Name: "conv1"})
	db.Create(&structs.Conversation{UserId: "rrossmiller", ConversationId: uuid.New(), Name: "conv2"})
	db.Create(&structs.Conversation{UserId: "sam_pull", ConversationId: uuid.New(), Name: "conv3"})

	// add message to convos
	message := structs.Message{
		ConversationId: conv1,
		MessageId:      uuid.New(),
		ParentId:       nil,
		ModelName:      "GPT-4o",
		Content:        "This is the first message, there is no parent",
		Role:           structs.UserRole,
		Feedback:       structs.NoFeedback,
		Comment:        "",
	}

	db.Create(&message)
	m2 := structs.Message{
		ConversationId: conv1,
		MessageId:      uuid.New(),
		ParentId:       &message.MessageId,
		ModelName:      "GPT-4o",
		Content:        "Hello, how may I help you?",
		Role:           structs.SystemRole,
		Feedback:       structs.NoFeedback,
		Comment:        "",
	}
	db.Create(&m2)
}
