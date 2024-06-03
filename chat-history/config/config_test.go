package config

import (
	"fmt"
	"os"
	"testing"
)

func TestLoadConfig(t *testing.T) {
	pth := setup(t)
	cfg, err := LoadConfig(pth)
	if err != nil {
		t.Fatal(err)
	}

	if len(cfg.DbHostname) == 0 ||
		cfg.DbHostname != "http://localhost:14240" ||
		cfg.DbPath != "chats.db" ||
		cfg.DbLogPath != "db.log" ||
		cfg.LogPath != "requestLogs.jsonl" {
		t.Fatalf("hostname is blank, %q", cfg.DbHostname)
	}
}

func setup(t *testing.T) string {
	tmp := t.TempDir()
	pth := fmt.Sprintf("%s/%s", tmp, "config.json")
	dat := `

{
    "hostname": "http://localhost:14240",
    "dbPath": "chats.db",
    "dbLogPath": "db.log",
    "logPath": "requestLogs.jsonl",
    "username": "tigergraph",
    "password": "tigergraph",
    "getToken": false,
    "default_timeout": 300,
    "default_mem_threshold": 5000,
    "default_thread_limit": 8
}`
	err := os.WriteFile(pth, []byte(dat), 0644)
	if err != nil {
		t.Fatal("error setting up config.json")
	}
	return pth
}
