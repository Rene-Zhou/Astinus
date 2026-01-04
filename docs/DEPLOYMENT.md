# Astinus 部署指南

本文档描述如何部署 Astinus TTRPG 引擎到开发和生产环境。

## 目录

- [系统要求](#系统要求)
- [开发环境](#开发环境)
- [生产部署](#生产部署)
- [环境变量](#环境变量)
- [Docker 部署](#docker-部署)
- [常见问题](#常见问题)

---

## 系统要求

### 最低配置
- Python 3.14+
- 2GB RAM
- 1GB 磁盘空间

### 推荐配置
- Python 3.14+
- 4GB RAM
- 2GB 磁盘空间
- SSD 存储（用于向量数据库）

### 依赖
- [uv](https://github.com/astral-sh/uv) - Python 包管理器
- SQLite 或 PostgreSQL（生产环境）
- OpenAI API 密钥或兼容的 LLM 服务

---

## 开发环境

### 1. 克隆仓库

```bash
git clone https://github.com/your-org/Astinus.git
cd Astinus
```

### 2. 安装 uv

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 3. 安装依赖

```bash
uv sync
```

### 4. 配置环境变量

创建 `.env` 文件：

```bash
cp .env.example .env
# 编辑 .env 文件，填入必要的配置
```

最小配置：

```env
OPENAI_API_KEY=sk-your-api-key-here
```

### 5. 运行开发服务器

```bash
# 启动后端 API
uv run python -m src.backend.main

# 或使用 uvicorn（支持热重载）
uv run uvicorn src.backend.main:app --reload --host 0.0.0.0 --port 8000
```

### 6. 启动 TUI 前端

```bash
uv run python main.py
```

### 7. 运行测试

```bash
# 运行所有测试
uv run pytest

# 运行测试并生成覆盖率报告
uv run pytest --cov=src --cov-report=html

# 只运行单元测试（不含集成测试）
uv run pytest --ignore=tests/integration
```

---

## 生产部署

### 方案一：直接部署

#### 1. 准备服务器

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y python3.14 python3.14-venv sqlite3

# 安装 uv
curl -LsSf https://astral.sh/uv/install.sh | sh
```

#### 2. 部署应用

```bash
# 克隆代码
git clone https://github.com/your-org/Astinus.git
cd Astinus

# 安装生产依赖
uv sync --no-dev

# 设置环境变量
export OPENAI_API_KEY="sk-your-production-key"
export DATABASE_URL="sqlite:///data/astinus.db"
export ENVIRONMENT="production"
```

#### 3. 使用 systemd 管理服务

创建 `/etc/systemd/system/astinus.service`：

```ini
[Unit]
Description=Astinus TTRPG Engine
After=network.target

[Service]
Type=simple
User=astinus
WorkingDirectory=/opt/astinus
Environment="OPENAI_API_KEY=sk-your-key"
Environment="DATABASE_URL=sqlite:///data/astinus.db"
Environment="ENVIRONMENT=production"
ExecStart=/home/astinus/.local/bin/uv run uvicorn src.backend.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable astinus
sudo systemctl start astinus
```

#### 4. 配置 Nginx 反向代理

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket 超时设置
        proxy_read_timeout 86400;
    }
}
```

### 方案二：Docker 部署

详见 [Docker 部署](#docker-部署) 章节。

---

## 环境变量

### 必需变量

| 变量名 | 描述 | 示例 |
|--------|------|------|
| `OPENAI_API_KEY` | OpenAI API 密钥 | `sk-...` |

### 可选变量

| 变量名 | 描述 | 默认值 |
|--------|------|--------|
| `DATABASE_URL` | 数据库连接 URL | `sqlite+aiosqlite:///data/astinus.db` |
| `ENVIRONMENT` | 运行环境 | `development` |
| `LOG_LEVEL` | 日志级别 | `INFO` |
| `LLM_MODEL` | LLM 模型名称 | `gpt-4o-mini` |
| `LLM_TEMPERATURE` | LLM 温度参数 | `0.7` |
| `CORS_ORIGINS` | 允许的 CORS 来源 | `*` |
| `HOST` | 绑定地址 | `0.0.0.0` |
| `PORT` | 绑定端口 | `8000` |
| `CHROMA_PERSIST_DIR` | ChromaDB 持久化目录 | `data/chroma` |

### 高级配置

| 变量名 | 描述 | 默认值 |
|--------|------|--------|
| `OPENAI_API_BASE` | OpenAI API 基础 URL（用于兼容服务） | `https://api.openai.com/v1` |
| `MAX_TOKENS` | LLM 最大 token 数 | `2048` |
| `VECTOR_STORE_COLLECTION` | 向量存储集合名称 | `astinus_lore` |

---

## Docker 部署

### Dockerfile

创建 `Dockerfile`：

```dockerfile
FROM python:3.14-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 安装 uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# 复制项目文件
COPY pyproject.toml uv.lock ./
COPY src/ ./src/
COPY data/ ./data/
COPY config/ ./config/
COPY locale/ ./locale/

# 安装依赖
RUN uv sync --frozen --no-dev

# 创建数据目录
RUN mkdir -p /app/data/chroma /app/logs

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uv", "run", "uvicorn", "src.backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### docker-compose.yml

```yaml
version: '3.8'

services:
  astinus:
    build: .
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - DATABASE_URL=sqlite+aiosqlite:///data/astinus.db
      - ENVIRONMENT=production
      - LOG_LEVEL=INFO
    volumes:
      - astinus-data:/app/data
      - astinus-logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  astinus-data:
  astinus-logs:
```

### 构建和运行

```bash
# 构建镜像
docker-compose build

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 生产环境 Docker Compose

创建 `docker-compose.prod.yml`：

```yaml
version: '3.8'

services:
  astinus:
    build: .
    ports:
      - "127.0.0.1:8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - DATABASE_URL=sqlite+aiosqlite:///data/astinus.db
      - ENVIRONMENT=production
      - LOG_LEVEL=WARNING
    volumes:
      - /opt/astinus/data:/app/data
      - /var/log/astinus:/app/logs
    restart: always
    deploy:
      resources:
        limits:
          memory: 2G
        reservations:
          memory: 512M
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

运行生产环境：

```bash
docker-compose -f docker-compose.prod.yml up -d
```

---

## 数据备份

### SQLite 备份

```bash
# 备份数据库
cp data/astinus.db backups/astinus_$(date +%Y%m%d_%H%M%S).db

# 使用 sqlite3 热备份
sqlite3 data/astinus.db ".backup 'backups/astinus_backup.db'"
```

### 向量数据库备份

```bash
# 备份 ChromaDB 数据
tar -czf backups/chroma_$(date +%Y%m%d_%H%M%S).tar.gz data/chroma/
```

### 自动备份脚本

创建 `/opt/astinus/backup.sh`：

```bash
#!/bin/bash
BACKUP_DIR="/opt/backups/astinus"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# 备份 SQLite
sqlite3 /opt/astinus/data/astinus.db ".backup '$BACKUP_DIR/astinus_$DATE.db'"

# 备份向量数据库
tar -czf $BACKUP_DIR/chroma_$DATE.tar.gz -C /opt/astinus/data chroma/

# 保留最近 7 天的备份
find $BACKUP_DIR -type f -mtime +7 -delete

echo "Backup completed: $DATE"
```

添加到 crontab：

```bash
# 每天凌晨 3 点执行备份
0 3 * * * /opt/astinus/backup.sh >> /var/log/astinus-backup.log 2>&1
```

---

## 监控和日志

### 日志配置

应用日志位于：
- 开发环境：控制台输出
- 生产环境：`/app/logs/` 或配置的日志目录

### 健康检查

API 提供健康检查端点：

```bash
curl http://localhost:8000/health
```

正常响应：

```json
{
  "status": "healthy",
  "version": "0.1.0",
  "agents": {
    "gm_agent": true,
    "rule_agent": true
  }
}
```

### Prometheus 指标（可选）

如需添加 Prometheus 监控，可安装 `prometheus-fastapi-instrumentator`：

```bash
uv add prometheus-fastapi-instrumentator
```

---

## 常见问题

### Q: 如何更换 LLM 提供商？

设置 `OPENAI_API_BASE` 环境变量指向兼容的 API：

```env
OPENAI_API_BASE=https://your-llm-provider.com/v1
OPENAI_API_KEY=your-provider-api-key
```

### Q: 数据库迁移失败怎么办？

1. 备份现有数据库
2. 删除数据库文件
3. 重启应用（将自动创建新数据库）
4. 如需保留数据，使用 SQLite 工具手动迁移

### Q: WebSocket 连接不稳定？

1. 检查 Nginx 配置中的超时设置
2. 确保防火墙允许 WebSocket 连接
3. 检查客户端网络环境

### Q: 向量检索性能差？

1. 确保使用 SSD 存储
2. 增加服务器内存
3. 考虑定期重建向量索引

### Q: 如何查看实时日志？

```bash
# Docker
docker-compose logs -f astinus

# systemd
journalctl -u astinus -f
```

---

## 安全建议

1. **永远不要将 API 密钥提交到代码仓库**
2. 生产环境使用环境变量或密钥管理服务存储敏感信息
3. 配置 HTTPS（使用 Let's Encrypt 免费证书）
4. 限制 CORS 来源为可信域名
5. 定期更新依赖以修复安全漏洞
6. 使用防火墙限制不必要的端口访问

---

## 联系支持

如遇到部署问题，请：

1. 查看 [GitHub Issues](https://github.com/your-org/Astinus/issues)
2. 提交新 Issue 并附上日志和环境信息
3. 参考 [GUIDE.md](./GUIDE.md) 和 [ARCHITECTURE.md](./ARCHITECTURE.md)