package db

import (
	"chat-history/middleware"
	"chat-history/structs"
	"errors"
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

	// Find the existing message by conversation ID and message ID
	var existingMessage structs.Message
	tx := db.Where("conversation_id = ? AND message_id = ? ", message.ConversationId, message.MessageId).First(&existingMessage)
	if tx.Error != nil {
		if errors.Is(tx.Error, gorm.ErrRecordNotFound) {
			if result := db.Create(&message); result.Error != nil {
				return nil, result.Error
			}
		} else {
			return nil, tx.Error
		}
	} else {
		// Update only the feedback and comments fields if the message exists
		if result := db.Model(&existingMessage).Select("Feedback", "Comment").Updates(
			structs.Message{
				Feedback: message.Feedback,
				Comment:  message.Comment,
			}); result.Error != nil {
			return nil, result.Error
		}
	}

	// Retrieve the updated conversation
	convo := structs.Conversation{}
	tx = db.Where("conversation_id = ?", message.ConversationId).Find(&convo)

	if err := tx.Error; err != nil {
		return nil, err
	}
	return &convo, nil
}

// GetAllMessages retrieves all messages from the database
func GetAllMessages() ([]structs.Message, error) {
	var messages []structs.Message

	// Use GORM to query all messages
	if err := db.Find(&messages).Error; err != nil {
		return nil, err
	}

	return messages, nil
}

func populateDB() {
	mu.Lock()
	defer mu.Unlock()

	// init convos
	conv1 := uuid.MustParse("601529eb-4927-4e24-b285-bd6b9519a951")
	conv2 := uuid.MustParse("601529eb-4927-4e24-b285-bd6b9519a952")
	db.Create(&structs.Conversation{UserId: "sam_pull", ConversationId: conv1, Name: "conv1"})
	db.Create(&structs.Conversation{UserId: "Miss_Take", ConversationId: conv2, Name: "conv2"})
	// db.Create(&structs.Conversation{UserId: "Miss_Take", ConversationId: uuid.New(), Name: "conv3"})

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

	m3 := structs.Message{
		ConversationId: conv2,
		MessageId:      uuid.New(),
		ParentId:       &message.MessageId,
		ModelName:      "GPT-4o",
		Content:        "How many transactions?",
		Role:           structs.SystemRole,
		Feedback:       structs.NoFeedback,
		Comment:        "",
	}
	db.Create(&m3)
}
