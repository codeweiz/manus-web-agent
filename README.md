# Manus Web Agent

致力于提供最好的 Web Agent - 一个功能完整的 AI Agent 系统，支持浏览器自动化、Shell 命令执行、文件操作和网络搜索。

## 项目架构

项目采用 DDD (领域驱动设计) 分层架构：

```
manus-web-agent/
├── src/manus_web_agent/
│   ├── application/          # 应用层：用例实现、服务编排
│   │   ├── errors/           # 应用层异常
│   │   └── services/         # 应用服务
│   ├── core/                 # 核心层：配置管理
│   ├── domain/               # 领域层：核心业务逻辑
│   │   ├── external/         # 外部服务接口
│   │   ├── models/           # 领域模型
│   │   ├── repositories/     # 仓储接口
│   │   ├── services/         # 领域服务
│   │   │   ├── agents/       # Agent 实现
│   │   │   ├── flows/        # 流程编排
│   │   │   ├── prompts/      # 提示词模板
│   │   │   └── tools/        # 工具实现
│   │   └── utils/            # 领域工具
│   ├── infrastructure/       # 基础设施层：技术实现
│   │   ├── external/         # 外部服务实现
│   │   ├── models/           # 数据模型 (Beanie ODM)
│   │   ├── repositories/     # 仓储实现
│   │   ├── storage/          # 存储实现
│   │   └── utils/            # 基础设施工具
│   └── interfaces/           # 接口层：API 接口
│       ├── api/              # API 路由
│       ├── errors/           # 异常处理器
│       └── schemas/          # 请求/响应模型
├── tests/                    # 测试代码
├── .config.toml              # 配置文件
├── pyproject.toml            # 项目依赖
└── README.md                 # 项目文档
```

## 核心功能

### 1. 沙盒环境 (Sandbox)
- Docker 容器提供隔离的执行环境
- 支持 Shell 命令执行
- 文件上传/下载
- 浏览器自动化环境

### 2. 浏览器自动化 (Browser)
- Playwright 基于 CDP 的浏览器控制
- 支持截图、导航、点击、表单填写
- 支持多标签页管理

### 3. 工具调用 (Tools)
- **Browser**: 浏览器自动化操作
- **Shell**: 命令执行与查看
- **File IO**: 文件读写操作
- **Search**: 网络搜索集成 (Bing/Google/Baidu)
- **MCP**: Model Context Protocol 集成

### 4. Agent 系统
- 基于 Plan-Act 流程的任务执行
- 多轮对话支持
- 工具调用链
- 会话管理

### 5. VNC 可视化
- WebSocket 长连接提供远程查看沙盒环境
- 实时交互支持

## 环境要求

- Python 3.11+
- Docker
- MongoDB
- Redis

## 快速开始

### 1. 安装依赖

```bash
# 创建虚拟环境
uv venv
source .venv/bin/activate

# 安装依赖
uv sync
```

### 2. 配置

复制 `.config.toml` 并修改配置：

```toml
[llm]
provider = "deepseek"
model = "deepseek-chat"
api_key = "your-api-key"
base_url = "https://api.deepseek.com"

[mongodb]
uri = "mongodb://localhost:27017"
database = "manus_web_agent"

[redis]
host = "localhost"
port = 6379
db = 0

[sandbox]
ttl_minutes = 30

[search]
provider = "bing"
```

### 3. 启动服务

```bash
# 启动 MongoDB
docker run -d -p 27017:27017 --name mongodb mongo:latest

# 启动 Redis
docker run -d -p 6379:6379 --name redis redis:latest

# 启动应用
python -m manus_web_agent.main
```

## API 端点

### 会话管理

| 方法 | 路径 | 描述 |
|------|------|------|
| PUT | `/api/v1/sessions` | 创建会话 |
| GET | `/api/v1/sessions` | 获取所有会话 |
| GET | `/api/v1/sessions/{session_id}` | 获取会话详情 |
| DELETE | `/api/v1/sessions/{session_id}` | 删除会话 |
| POST | `/api/v1/sessions/{session_id}/stop` | 停止会话 |
| POST | `/api/v1/sessions/{session_id}/chat` | 聊天 (SSE) |

### 工具操作

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/api/v1/sessions/{session_id}/shell` | 查看 Shell 输出 |
| POST | `/api/v1/sessions/{session_id}/file` | 查看文件内容 |
| WS | `/api/v1/sessions/{session_id}/vnc` | VNC WebSocket |
| GET | `/api/v1/sessions/{session_id}/files` | 获取会话文件列表 |

### 文件管理

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/api/v1/files` | 上传文件 |
| GET | `/api/v1/files/{file_id}` | 获取文件 |
| GET | `/api/v1/files/{file_id}/download` | 下载文件 |
| DELETE | `/api/v1/files/{file_id}` | 删除文件 |

### 认证

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/api/v1/auth/login` | 登录 |
| POST | `/api/v1/auth/register` | 注册 |
| GET | `/api/v1/auth/me` | 获取当前用户 |
| POST | `/api/v1/auth/refresh` | 刷新 Token |
| POST | `/api/v1/auth/logout` | 登出 |

### 共享会话

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/api/v1/sessions/{session_id}/share` | 分享会话 |
| DELETE | `/api/v1/sessions/{session_id}/share` | 取消分享 |
| GET | `/api/v1/sessions/shared/{session_id}` | 获取共享会话 |

## 开发

### 运行测试

```bash
pytest tests/
```

### 代码检查

```bash
ruff check src/
ruff format src/
```

### 类型检查

```bash
mypy src/
```

## 配置说明

### LLM 配置

支持多种 LLM 提供商：

- DeepSeek (默认)
- OpenAI
- 其他兼容 OpenAI API 的提供商

### 搜索配置

支持多种搜索引擎：

- Bing (默认，无需 API Key)
- Google (需要 API Key 和 Engine ID)
- Baidu (无需 API Key)

### 沙箱配置

- 支持自定义 Docker 镜像
- 支持网络配置
- 支持代理设置

## 许可证

MIT License
