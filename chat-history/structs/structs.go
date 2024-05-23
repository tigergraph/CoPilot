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

//	{
//	    "GET /user/{user_id}/": [ //list of convos
//	        // order chronologically
//	        {
//	            "conversation_id": "uuid",
//	            "name": "string",
//	            "updateTS": "unix TS"
//	        }
//	    ],

type Conversation struct {
	Model
	UserId         string    `json:"user_id"`
	ConversationId uuid.UUID `json:"conversation_id" gorm:"unique;not null"`
	Name           string    `json:"name"`
}

//     "GET /conversation/{conversation_id}": [ //list of messages
//         { // message
//             "message_id": "uuid",
//             "parent_id": "uuid",
//             "model": "string",
//             "content": "string",
//             "role": "user/CoPilot",
//             "timestamp": "unixTimestamp",
//             "feedback": "thumbs up/down",
//             "comment": "string"
//         }
//     ],
//     "POST /conversation": { // what follows is the request structure
//         "conversation_id": "uuid",
//         "message": { //message
//             "message_id": "uuid",
//             "parent_id": "uuid",
//             "model": "string",
//             "content": "string",
//             "role": "user/CoPilot",
//             "timestamp": "unixTimestamp",
//             "feedback": "thumbs up/down",
//             "comment": "string"
//         }
//     }
// }
// "DELETE /conversation/{conversation_id}": [ //list of convos
//     //TODO response
// ]
