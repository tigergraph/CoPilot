package structs

import (
	"time"

	"github.com/google/uuid"
	"gorm.io/gorm"
)

// overwrite gorm.Model for better json output
type Model struct {
	ID        uint           `json:"id" gorm:"primarykey"`
	CreatedAt time.Time      `json:"create_ts"`
	UpdatedAt time.Time      `json:"update_ts"`
	DeletedAt gorm.DeletedAt `json:"delete_ts" gorm:"index"`
}

type Conversation struct {
	Model
	UserId         string    `json:"user_id" gorm:"not null"`
	ConversationId uuid.UUID `json:"conversation_id" gorm:"unique;not null"`
	Name           string    `json:"name"`
}

type MessagengerRole string

type Feedback uint

const (
	SystemRole MessagengerRole = "system"
	UserRole   MessagengerRole = "user"
)
const (
	NoFeedback = iota
	ThumbsUp
	ThumbsDown
)

type Message struct {
	Model
	ConversationId uuid.UUID       `json:"conversation_id" gorm:"not null"`
	MessageId      uuid.UUID       `json:"message_id" gorm:"not null"`
	ParentId       *uuid.UUID      `json:"parent_id"` // pointer allows nil
	ModelName      string          `json:"model"`
	Content        string          `json:"content"`
	Role           MessagengerRole `json:"role"`
	Feedback       Feedback        `json:"feedback"`
	Comment        string          `json:"comment"`
}

type User struct {
	Model
	UserName string `json:"user_name"`
	Tkn      string `json:"tkn"`
}
