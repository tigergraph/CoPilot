package db

import (
	"chat-history/middleware"
	"chat-history/structs"
	"log"
	"os"
	"strings"
	"sync"

	"github.com/google/uuid"

	"gorm.io/driver/sqlite"
	"gorm.io/gorm"
	"gorm.io/gorm/logger"
)

var (
	db *gorm.DB
	mu = sync.RWMutex{}
)

func createLogger(logPath string) logger.Interface {
	fLogger := middleware.InitLogger(logPath)
	return logger.New(
		log.New(fLogger, "\n", log.LstdFlags),
		logger.Config{Colorful: false, LogLevel: logger.Info},
	)
}

// Initialize the DB
func InitDB(dbPath, logPath string) {

	chatHistDB, err := gorm.Open(sqlite.Open(dbPath), &gorm.Config{Logger: createLogger(logPath)})
	if err != nil {
		panic("failed to connect database")
	}
	db = chatHistDB

	// Migrate the schema
	err = db.AutoMigrate(&structs.Conversation{}, &structs.Message{})
	if err != nil {
		panic(err)
	}

	// Create -- for testing only
	dev := strings.ToLower(os.Getenv("DEV")) == "true"
	if dev {
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

func GetUserConversationById(userId, conversationId string) []structs.Message {
	messages := []structs.Message{}
	convos := GetUserConversations(userId)

	// ensure that conversatonId is a convo for this user
	mu.RLock()
	defer mu.RUnlock()
	for _, c := range convos {
		// conversaton belongs to this user. get the messages
		if c.ConversationId.String() == conversationId {
			db.Where("conversation_id = ?", conversationId).Find(&messages)
			break
		}
	}
	return messages
}

func NewConversation(userId, name string, message structs.Message) (*structs.Conversation, error) {
	mu.Lock()
	defer mu.Unlock()

	convo := structs.Conversation{UserId: userId, ConversationId: message.ConversationId, Name: name}
	tx := db.Create(&convo)
	if err := tx.Error; err != nil {
		return nil, err
	}
	tx = db.Create(&message)
	if err := tx.Error; err != nil {
		return nil, err
	}

	return &convo, nil
}

func UpdateConversationById(message structs.Message) (*structs.Conversation, error) {
	mu.Lock()
	defer mu.Unlock()

	if result := db.Create(&message); result.Error != nil {
		return nil, result.Error
	}
	convo := structs.Conversation{}
	tx := db.Where("conversation_id = ?", message.ConversationId).Find(&convo)

	if err := tx.Error; err != nil {
		return nil, err
	}
	return &convo, nil
}

func populateDB() {
	mu.Lock()
	defer mu.Unlock()

	// init convos
	conv1 := uuid.MustParse("601529eb-4927-4e24-b285-bd6b9519a951")
	db.Create(&structs.Conversation{UserId: "sam_pull", ConversationId: conv1, Name: "conv1"})
	db.Create(&structs.Conversation{UserId: "sam_pull", ConversationId: uuid.New(), Name: "conv2"})
	db.Create(&structs.Conversation{UserId: "Miss_Take", ConversationId: uuid.New(), Name: "conv3"})

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
