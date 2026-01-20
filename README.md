# Manus Web Agent

致力于提供最好的 Web Agent

## 项目架构

项目采用 DDD 领域驱动设计架构，遵循单一职责：

```
manus-web-agent/
├── src/
│   ├── manus_web_agent/        # 项目包
│   │   ├── application/        # 应用层
│   │   ├── core/               # 核心层
│   │   ├── domain/             # 领域层：包含核心业务逻辑
│   │   ├── infrastructure/     # 基础设施层：提供技术实现
│   │   ├── interfaces/         # 接口层：定义系统对外接口
│   │   ├── main.py             # 入口文件
│   │   └── __init__.py         # 包初始化
├── tests/                      # 测试代码
├── .gitignore                  # git 忽略文件
├── .python-version             # python 版本
├── pyproject.toml              # 项目依赖
└── README.md                   # 项目文档
```

## 核心功能

1. 沙盒环境：沙箱提供隔离的执行环境
2. VNC 可视化：WebSocket 长连接提供远程查看沙盒环境
3. 工具调用：
    - Playwright 浏览器自动化操作
    - Shell 命令执行与查看
    - File IO 文件读写操作
    - Search 网络搜索集成
4. MCP 集成

## 环境要求

- Python 3.11+
- Docker
- MongoDB
- Redis

## 快速开始

```bash
uv venv
source .venv/bin/activate

uv sync
```
