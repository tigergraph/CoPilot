package config

import (
	"encoding/json"
	"os"
)

type LLMConfig struct {
	ModelName string `json:"model_name"`
}

type ChatDbConfig struct {
	Port                    string   `json:"apiPort"`
	DbPath                  string   `json:"dbPath"`
	DbLogPath               string   `json:"dbLogPath"`
	LogPath                 string   `json:"logPath"`
	ConversationAccessRoles []string `json:"conversationAccessRoles"`
}

type TgDbConfig struct {
	Hostname string `json:"hostname"`
	Username string `json:"username"`
	Password string `json:"password"`
	GsPort   string `json:"gsPort"`
	// GetToken string `json:"getToken"`
	// DefaultTimeout       string `json:"default_timeout"`
	// DefaultMemThreshold string `json:"default_mem_threshold"`
	// DefaultThreadLimit  string `json:"default_thread_limit"`
}

type Config struct {
	ChatDbConfig
	TgDbConfig
	// LLMConfig
}

func LoadConfig(paths map[string]string) (Config, error) {
	var config Config

	// Load database config
	if dbConfigPath, ok := paths["chatdb"]; ok {
		dbConfig, err := loadChatDbConfig(dbConfigPath)
		if err != nil {
			return Config{}, err
		}
		config.ChatDbConfig = dbConfig
	}

	// Load TigerGraph config
	if tgConfigPath, ok := paths["tgdb"]; ok {
		tgConfig, err := loadTgDbConfig(tgConfigPath)
		if err != nil {
			return Config{}, err
		}
		config.TgDbConfig = tgConfig
	}

	return config, nil
}

func loadChatDbConfig(path string) (ChatDbConfig, error) {
	var dbConfig ChatDbConfig
	b, err := os.ReadFile(path)
	if err != nil {
		return ChatDbConfig{}, err
	}
	if err := json.Unmarshal(b, &dbConfig); err != nil {
		return ChatDbConfig{}, err
	}
	return dbConfig, nil
}

func loadTgDbConfig(path string) (TgDbConfig, error) {
	var tgConfig TgDbConfig
	b, err := os.ReadFile(path)
	if err != nil {
		return TgDbConfig{}, err
	}
	if err := json.Unmarshal(b, &tgConfig); err != nil {
		return TgDbConfig{}, err
	}
	return tgConfig, nil
}
