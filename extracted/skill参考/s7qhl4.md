<!-- source: skill参考.md | id: s7qhl4 -->
{
  "agents": {
    "defaults": {
      "workspace": "./gateway/nanobot_workspace",
      "model": "YOUR_QWEN_MODEL_NAME",
      "provider": "YOUR_PROVIDER_NAME"
    }
  },
  "channels": {
    "sendProgress": true,
    "sendToolHints": false,
    "telegram": {
      "enabled": true,
      "token": "YOUR_TELEGRAM_BOT_TOKEN",
      "allowFrom": [
        "YOUR_TELEGRAM_USER_ID"
      ],
      "replyToMessage": true
    }
  },
  "providers": {
    "YOUR_PROVIDER_NAME": {
      "apiKey": "DUMMY_OR_REAL_API_KEY",
      "apiBase": "http://127.0.0.1:8000/v1"
    }
  },
  "gateway": {
    "host": "0.0.0.0",
    "port": 18790,
    "heartbeat": {
      "enabled": true,
      "intervalS": 1800
    }
  },
  "tools": {
    "restrictToWorkspace": false,
    "mcpServers": {
      "vision-mcp": {
        "url": "http://127.0.0.1:8101/mcp",
        "toolTimeout": 60
      },
      "memory-mcp": {
        "url": "http://127.0.0.1:8102/mcp",
        "toolTimeout": 60
      },
      "state-policy-mcp": {
        "url": "http://127.0.0.1:8103/mcp",
        "toolTimeout": 60
      },
      "ocr-device-mcp": {
        "url": "http://127.0.0.1:8104/mcp",
        "toolTimeout": 90
      }
    }
  }
}
