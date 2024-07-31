package config

import (
	"fmt"
	"os"
	"testing"
)

func TestLoadConfig(t *testing.T) {
	pth := setup(t)

	// Print the path for debugging
	fmt.Println("Configuration file path:", pth)

	cfg, err := LoadConfig(pth)
	if err != nil {
		t.Fatal(err)
	}

	if cfg.Port != "8000" ||
		cfg.DbPath != "chats.db" ||
		cfg.DbLogPath != "db.log" ||
		cfg.LogPath != "requestLogs.jsonl" {
		t.Fatalf("config is wrong, %v", cfg)
	}
}

func setup(t *testing.T) string {
	tmp := t.TempDir()
	pth := fmt.Sprintf("%s/%s", tmp, "chat_config.json")
	dat := `
{
	"apiPort":"8000",
	"dbPath": "chats.db",
	"dbLogPath": "db.log",
	"logPath": "requestLogs.jsonl",
	"tgCloud": true,
	"conversationAccessRoles": ["superuser", "globaldesigner"]
	"username": "tigergraph",
	"password": "tigergraph",
}`

	if err := os.WriteFile(pth, []byte(dat), 0644); err != nil {
		t.Fatal("error setting upconfig.json")
	}

	return pth

}
