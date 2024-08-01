package config

import (
	"fmt"
	"os"
	"testing"
)

func TestLoadConfig(t *testing.T) {
	chatConfigPath, tgConfigPath := setup(t)

	cfg, err := LoadConfig(map[string]string{
		"chatdb": chatConfigPath,
		"tgdb":   tgConfigPath,
	})
	if err != nil {
		t.Fatal(err)
	}

	if cfg.ChatDbConfig.Port != "8002" ||
		cfg.ChatDbConfig.DbPath != "chats.db" ||
		cfg.ChatDbConfig.DbLogPath != "db.log" ||
		cfg.ChatDbConfig.LogPath != "requestLogs.jsonl" {
		t.Fatalf("config is wrong, %v", cfg.ChatDbConfig)
	}

	if cfg.TgDbConfig.Hostname != "https://tg-0cdef603-3760-41c3-af6f-41e95afc40de.us-east-1.i.tgcloud.io" ||
		cfg.TgDbConfig.GsPort != "14240" ||
		cfg.TgDbConfig.TgCloud != true {
		t.Fatalf("TigerGraph config is wrong, %v", cfg.TgDbConfig)
	}
}

func setup(t *testing.T) (string, string) {
	tmp := t.TempDir()

	chatConfigPath := fmt.Sprintf("%s/%s", tmp, "chat_config.json")
	chatConfigData := `
{
	"apiPort":"8002",
	"dbPath": "chats.db",
	"dbLogPath": "db.log",
	"logPath": "requestLogs.jsonl",
	"conversationAccessRoles": ["superuser", "globaldesigner"]
}`

	if err := os.WriteFile(chatConfigPath, []byte(chatConfigData), 0644); err != nil {
		t.Fatal("error setting up chat_config.json")
	}

	tgConfigPath := fmt.Sprintf("%s/%s", tmp, "db_config.json")
	tgConfigData := `
{
    "hostname": "https://tg-0cdef603-3760-41c3-af6f-41e95afc40de.us-east-1.i.tgcloud.io",
    "gsPort": "14240",
    "username": "supportai",
    "password": "supportai",
	"tgCloud": true
}`
	if err := os.WriteFile(tgConfigPath, []byte(tgConfigData), 0644); err != nil {
		t.Fatal("error setting up tg_config.json")
	}

	return chatConfigPath, tgConfigPath
}
