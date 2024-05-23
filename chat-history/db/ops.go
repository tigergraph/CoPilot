package db

import (
	"chat-history/structs"
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
func InitDB() {
	//TODO:
	// read db config from a file
	// remove create block to init dummy data
	chatHistDB, err := gorm.Open(sqlite.Open("test.db"), &gorm.Config{})
	if err != nil {
		panic("failed to connect database")
	}
	db = chatHistDB

	// Migrate the schema
	err = db.AutoMigrate(&structs.Conversation{})
	if err != nil {
		panic(err)
	}
	// Create
	mu.Lock()
	defer mu.Unlock()
	db.Create(&structs.Conversation{UserId: "rrossmiller", ConversationId: uuid.New(), Name: "conv1"})
	db.Create(&structs.Conversation{UserId: "rrossmiller", ConversationId: uuid.New(), Name: "conv2"})
	db.Create(&structs.Conversation{UserId: "sam_pull", ConversationId: uuid.New(), Name: "conv3"})
}

func GetUserConversations(userId string) []structs.Conversation {
	mu.RLock()
	defer mu.RUnlock()

	convos := []structs.Conversation{}
	db.Where("user_id = ?", userId).Find(&convos)

	return convos
}

func GetUserConversationById(conversatonId string) []structs.Conversation {
	mu.RLock()
	defer mu.RUnlock()

	convos := []structs.Conversation{}
	// db.Where("user_id = ?", conversatonId).Find(&convos)

	return convos
}

// TODO: doesn't take an ID. takes the request body and updates based on what's in there
func UpdateConversationById(conversatonId string) []structs.Conversation {
	mu.RLock()
	defer mu.RUnlock()

	convos := []structs.Conversation{}
	// db.Where("user_id = ?", conversatonId).Find(&convos)

	return convos
}

// // Create
// db.Create(&structs.Conversation{ConversationId: uuid.New(), Name: "Rob Rossmiller"})
// db.Create(&structs.Conversation{ConversationId: uuid.New(), Name: "Joe Schmo"})
//
// // Read
// var convo1 structs.Conversation
// var convo structs.Conversation
// db.First(&convo1, 2)
// fmt.Println(convo1)
//
// db.First(&convo, "name = ?", "Rob Rossmiller")
//
// db.Model(&convo).Update("Name", "RKR")
// Update - update multiple fields
// db.Model(&convo).Updates(Product{Price: 200, Code: "F42"}) // non-zero fields
// db.Model(&convo).Updates(map[string]interface{}{"Price": 200, "Code": "F42"})

// Delete - delete product
// db.Delete(&convo, 1)
