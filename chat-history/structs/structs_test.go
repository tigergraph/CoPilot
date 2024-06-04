package structs

import (
	"testing"
)

func TestRole(t *testing.T) {
	if SystemRole != "system" {
		t.Fatalf("System == %s, not system", SystemRole)
	}
	if UserRole != "user" {
		t.Fatalf("User == %s, not user", UserRole)
	}
}

func TestFeedback(t *testing.T) {
	if NoFeedback != 0 {
		t.Fatalf("NoFeedback == %d, not 0", NoFeedback)
	}
	if ThumbsUp != 1 {
		t.Fatalf("ThumbsUp == %d, not 1", ThumbsUp)
	}
	if ThumbsDown != 2 {
		t.Fatalf("ThumbsDown == %d, not 2", ThumbsDown)
	}
}
