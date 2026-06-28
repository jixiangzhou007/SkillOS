# SkillOS 部署指南

## Docker

```bash
docker build -t skillos .
docker run -p 9876:9876 -v ./skills:/app/skills -v ./data:/app/data --env-file .env skillos
```

## 本地部署

```bash
pip install -e .
skillos --server-only --host 0.0.0.0 --port 9876
```

## Hermes Gateway（微信/飞书）

### 前置条件

Hermes Agent 已安装（`pip install hermes-agent`）。

### 步骤

```bash
# 1. 配置 Hermes gateway
hermes gateway

# 2. 添加 SkillOS MCP
hermes mcp add skillos --command python --args "-m" --args "skillos.mcp_server"

# 3. 测试
hermes mcp test skillos

# 4. 配置消息平台
# 微信: hermes gateway → WeChat webhook
# 飞书: hermes gateway → Feishu webhook
```

### 飞书具体配置

```bash
# 1. 飞书开放平台创建应用 → 获取 App ID / App Secret
# 2. 配置事件订阅 → 消息事件
# 3. Hermes 配置
hermes gateway add feishu \
  --app-id <APP_ID> \
  --app-secret <APP_SECRET> \
  --webhook-url <YOUR_WEBHOOK_URL>
```

### 微信具体配置

```bash
# Hermes 支持通过个人微信机器人接入
hermes gateway add wechat \
  --token <WECHAT_TOKEN> \
  --aes-key <AES_KEY>
```

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DEEPSEEK_API_KEY` | - | API 密钥 |
| `SKILLOS_MODEL` | deepseek-v4-flash | 默认模型 |
| `SKILLOS_EVOLVER_MODEL` | (同默认模型) | 进化优化用模型 |
| `SKILLOS_EXECUTOR_MODEL` | (同默认模型) | 技能执行用模型 |
| `SKILLOS_BASE_URL` | https://api.deepseek.com | API 地址 |
| `SKILLOS_SKILLS_DIR` | `<repo>/skills` | 技能主存储目录（可 `./skills`） |
| `SKILLOS_WORKSPACE_SKILLS` | (未设置) | 保存时镜像到工作区 `./skills` |
| `SKILLHUB_COMMISSION` | 0.20 | 平台佣金比例 |
| `SKILLHUB_PRIVATE` | false | 私有 Hub 模式 |
| `SKILLHUB_ADMIN_PASSWORD` | admin123 | 管理员密码 |

## 健康检查

```bash
curl http://localhost:9876/health
# → {"status": "ok", "version": "0.1.0"}

curl http://localhost:9876/api/marketplace/stats
# → {"total": N, "pending_review": N, "avg_score": N, ...}
```

## SSL / 反向代理

```nginx
server {
    listen 443 ssl;
    server_name skillos.example.com;
    location / {
        proxy_pass http://127.0.0.1:9876;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```
