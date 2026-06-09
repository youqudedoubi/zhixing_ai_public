# 知行AI (Zhixing AI)

本地 Web AI 助手，帮助用户认识自我和改变自我。

## 链接

- 🚀 **试用链接**：[知行AI](https://golden-paletas-18dfec.netlify.app)
- 🎬 **介绍视频**：[知行AI，你的个人系统](https://www.bilibili.com/video/BV1jjL76JEHM?vd_source=eb351bfc5512ac88dbb7fca42fda1c70)

## 技术栈

- **后端**: Python + FastAPI
- **前端**: React + Vite + TypeScript
- **AI**: DeepSeek API

## 环境要求

- **Python** 3.10+
- **Node.js** 18+
- **Git**（项目运行依赖 Git 进行版本管理）

## 快速开始

### 环境准备

```bash
# 1. 安装 Python 依赖
pip install -r requirements.txt

# 2. 安装前端依赖
cd code/frontend && npm install && cd ../..

# 3. 复制配置文件，填入你的 API Key
cp code/env.example.py code/env.py
```

`env.py` 示例：

```python
from pathlib import Path

root = Path(__file__).resolve().parent.parent / "zhixing_data"
api_key = "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

### 启动

```bash
# 方式一：使用启动脚本
start.bat

# 方式二：手动启动
python -m uvicorn code.backend.main:app --host 127.0.0.1 --port 8000 --reload
cd code/frontend && npm run dev
```

前端默认运行在 `http://localhost:5173`，后端默认运行在 `http://localhost:8000`。

## 应用布局

VSCode-like：活动栏 + 主侧栏 + 内容区 + 聊天区

- **活动栏**：可点击「资源管理器」「情境模拟」
- **主侧栏**：根据活动栏显示相应内容
- **内容区**：可查看文件
- **聊天区**：与 AI 助手交互

## 核心功能

- **资源管理器**：浏览和管理文件
- **AI 对话**：对话、修改文件、阅读文件
- **命令系统**：在对话框中输入命令触发功能
- **模式识别**：识别 CBT 模式 (`/update`)
- **深度研究**：深度研究用户课题 (`/research`)
- **情境模拟**：模拟用户在特定情境下的反应

## 目录结构

```
.
├── code/
│   ├── library/                # 通用 Agent 框架
│   │   ├── agent_atoms/        # 核心抽象
│   │   ├── examples/           # 框架使用示例
│   │   └── infra/              # 基础设施（调度器）
│   ├── backend/
│   │   ├── api/                # FastAPI 路由
│   │   ├── models/             # Pydantic 数据模型
│   │   ├── services/
│   │   │   ├── chat_agent/     # 主对话Agent
│   │   │   ├── file/           # 文件读写服务
│   │   │   ├── research/       # 深度研究
│   │   │   ├── simulation/     # 情境模拟引擎
│   │   │   ├── topic/          # 话题管理
│   │   │   └── workspace/      # 工作区 Git 操作
│   │   └── utils/
│   ├── frontend/
│   │   └── src/
│   │       ├── api/            # API 调用封装
│   │       ├── components/     # React 组件
│   │       └── types/          # TypeScript 类型定义
│   ├── shared/                 # 共享工具（路径 / 校验）
│   ├── config.py               # 全局配置
│   └── env.example.py          # 配置模板（复制为 code/env.py 后使用）
├── zhixing_data/               # 数据目录（空结构，运行后填充）
├── start.bat / stop.bat        # 启动/关闭脚本
├── requirements.txt            # Python 依赖
└── README.md
```

## License

MIT
