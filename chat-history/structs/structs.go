package structs

import (
	"fmt"
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

func (c *Conversation) New(userId, name string, convoId uuid.UUID) {
	c.UserId = userId
	c.Name = name
	c.ConversationId = convoId
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
	MessageId      uuid.UUID       `json:"message_id" gorm:"unique;not null"`
	ParentId       *uuid.UUID      `json:"parent_id"` // pointer allows nil
	ModelName      string          `json:"model"`
	Content        string          `json:"content"`
	Role           MessagengerRole `json:"role"`
	ResponseTime   float64         `json:"response_time"`
	Feedback       Feedback        `json:"feedback"`
	Comment        string          `json:"comment"`
}

func (m Message) String() string {
	// return fmt.Sprintf("ID-%v", m.ID)
	return fmt.Sprintf(`
	ID             %v
	UpdateTS       %v
	ConversationId %v
	MessageId      %v
	ParentId       %v
		`,
		m.ID, m.UpdatedAt, m.ConversationId, m.MessageId, m.ParentId)
	return fmt.Sprintf(`
	ID             %v
	ConversationId %v
	MessageId      %v
	ParentId       %v
	ModelName      %v
	Content        %v
	Role           %v
	Feedback       %v
	Comment        %v`, m.ID, m.ConversationId, m.MessageId, m.ParentId, m.ModelName, m.Content, m.Role, m.Feedback, m.Comment)
}

type User struct {
	Model
	UserName string `json:"user_name"`
	Tkn      string `json:"tkn"`
}
