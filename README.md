<div align="center">

# Mnemosyne

**基于记忆驱动的开源虚拟伴侣 Agent 框架**

*"记忆是灵魂的镜子" —— 希腊神话记忆女神 Mnemosyne*

[English](./docs/README_EN.md) | 简体中文

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.11+-blue.svg)

</div>

---

## 一句话描述

一个可以自部署的虚拟伴侣框架，支持创建多个具有**固定形象、独立性格、长期记忆**的角色，通过 Telegram 和 Web 与你建立持续的情感连接。

## 核心特性

- **长期记忆引擎** —— 记住你说过的每一句话、你的偏好、你的情绪波动，跨对话持久化
- **主动关怀** —— 根据记忆和时间点主动发消息，不是你找它，而是它找你
- **形象一致性** —— 上传一张基准照片，所有场景生成的图片保持同一张脸
- **多角色支持** —— 创建任意数量的伴侣角色，每个角色独立记忆、独立性格
- **情感系统** —— 角色有实时情绪状态，会因为你的态度而开心或失落
- **多通道接入** —— Telegram Bot + Web UI，随时随地互动
- **完全开源** —— 本地部署，数据不外传，隐私友好

## 技术架构

```
                        ┌─────────────────────────┐
                        │      用户浏览器           │
                        │    Web UI (Vue 3)        │
                        └────────────┬────────────┘
                                     │ HTTP / WebSocket
                        ┌────────────▼────────────┐
                        │     FastAPI Server       │
                        │   (Web UI + REST API)    │
                        └────────────┬────────────┘
                                     │
┌────────────────┐       ┌───────────▼────────────┐
│  Telegram Bot  │──────▶│     BotManager         │
│  (N 个 Token)  │       │   (统一调度中心)         │
└────────────────┘       └───────────┬────────────┘
                                     │
              ┌──────────┬───────────┼───────────┬──────────┐
              ▼          ▼           ▼           ▼          ▼
         ┌────────┐ ┌────────┐ ┌─────────┐ ┌────────┐ ┌────────┐
         │ Dialog │ │ Memory │ │ Emotion │ │ Image  │ │Trigger │
         │ Engine │ │ Engine │ │ System  │ │ Engine │ │ Engine │
         │(LangGr)│ │(pgvec) │ │ (Redis) │ │(API调用)│ │(APSch) │
         └────┬───┘ └────┬───┘ └────┬────┘ └────┬───┘ └────┬───┘
              │          │          │           │          │
         ┌────▼──────────▼──────────▼───────────▼──────────▼───┐
         │                    PostgreSQL                         │
         │              (主库 + pgvector 向量存储)                │
         │                    Redis                              │
         │              (情绪状态 + 任务队列 + 缓存)              │
         └──────────────────────────────────────────────────────┘
```

## 技术栈

| 层级 | 技术选型 | 说明 |
|------|---------|------|
| 语言 | Python 3.11+ | LLM 生态最成熟 |
| Web 框架 | FastAPI | 异步原生，自动 API 文档 |
| 前端 | Vue 3 + Vite + Tailwind CSS | 轻量简洁 |
| LLM 编排 | LangGraph | 状态机式对话流，可控性强 |
| LLM 调用 | LiteLLM | 统一接口，模型无关 |
| 向量存储 | PostgreSQL + pgvector | 无需额外组件 |
| 缓存/队列 | Redis | 情绪状态 + 任务队列 |
| 定时任务 | APScheduler | 轻量级调度 |
| Telegram | python-telegram-bot v20+ | 原生异步 |
| 图像生成 | Replicate / FAL API | 第三方 API，零 GPU 门槛 |
| 容器化 | Docker Compose | 一键部署 |

## 快速开始

### 环境要求

- Docker + Docker Compose（推荐）
- 或 Python 3.11+ + PostgreSQL 15+ + Redis 7+（手动部署）

### Docker 一键部署（推荐）

```bash
git clone https://github.com/your-username/mnemosyne.git
cd mnemosyne

# 复制并编辑配置文件
cp .env.example .env
# 编辑 .env，填入你的 LLM API Key

# 启动
docker compose up -d

# 访问 Web UI
# http://localhost:8080
```

### Windows 手动部署

```powershell
git clone https://github.com/your-username/mnemosyne.git
cd mnemosyne

# 一键安装脚本
.\scripts\install.ps1

# 启动服务
.\scripts\start.ps1
```

### Linux / Mac 手动部署

```bash
git clone https://github.com/your-username/mnemosyne.git
cd mnemosyne

# 一键安装脚本
chmod +x scripts/install.sh
./scripts/install.sh

# 启动服务
chmod +x scripts/start.sh
./scripts/start.sh
```

### 本地测试
```bash
.\scripts\dev.ps1

cd web
npm install
npm run dev
```

## 配置说明

复制 `.env.example` 为 `.env`，按需修改：

```env
# ===== LLM 配置 =====
LLM_PROVIDER=openai              # openai / anthropic / ollama
LLM_API_KEY=sk-xxx               # 你的 API Key
LLM_MODEL=gpt-4o-mini            # 模型名称
LLM_BASE_URL=                    # 可选，自定义 API 地址

# ===== 数据库 =====
DATABASE_URL=postgresql://mnemosyne:password@localhost:5432/mnemosyne
REDIS_URL=redis://localhost:6379/0

# ===== 图像生成（可选）=====
IMAGE_PROVIDER=replicate         # replicate / fal
REPLICATE_API_TOKEN=r8_xxx       # Replicate API Token
# FAL_KEY=xxx                   # 或 FAL API Key

# ===== Telegram（可选）=====
# TELEGRAM_BOT_TOKEN_1=123456:ABC-DEF  # 角色 1 的 Bot Token
# TELEGRAM_BOT_TOKEN_2=789012:GHI-JKL  # 角色 2 的 Bot Token

# ===== Web =====
WEB_HOST=0.0.0.0
WEB_PORT=8080
SECRET_KEY=change-me-to-random-string
```

## 数据模型

```sql
-- 用户表（单用户模式，保留扩展能力）
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 角色表
CREATE TABLE characters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(50) NOT NULL,
    personality TEXT NOT NULL,
    system_prompt TEXT NOT NULL,
    base_image_url TEXT,
    voice_style JSONB DEFAULT '{}',
    mood_default VARCHAR(20) DEFAULT 'sweet',
    telegram_token VARCHAR(255),
    card_export JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 对话表（滑动窗口，保留最近 30 轮）
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    character_id UUID REFERENCES characters(id) ON DELETE CASCADE,
    role VARCHAR(10) NOT NULL,
    content TEXT NOT NULL,
    has_image BOOLEAN DEFAULT FALSE,
    image_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 记忆表（长期记忆）
CREATE TABLE memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    character_id UUID REFERENCES characters(id) ON DELETE CASCADE,
    type VARCHAR(20) NOT NULL,          -- fact / feeling / event
    content TEXT NOT NULL,
    embedding vector(1024),
    metadata JSONB DEFAULT '{}',
    importance FLOAT DEFAULT 0.5,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_accessed TIMESTAMPTZ
);
```

### 记忆类型说明

| 类型 | 示例 | 用途 |
|------|------|------|
| `fact`（事实） | "用户不吃香菜"、"用户的妈妈姓李" | 长期事实库，永久存储 |
| `feeling`（情感） | "用户今天因为加班很焦虑" | 情感状态追踪，有时效性 |
| `event`（事件） | "用户下周三要考试" | 可触发主动关怀的事件 |

## 角色卡格式

Mnemosyne 支持 YAML 和 JSON 双格式的角色卡导入/导出，方便用户之间分享角色设定。

```yaml
# Mnemosyne Character Card v1.0
meta:
  format_version: "1.0"
  export_date: "2026-05-06"
  author: "user"

character:
  name: 小雨
  personality: |
    你是一个温柔体贴的女孩，说话轻声细语。
    喜欢用"呢"、"呀"、"啦"结尾，会偶尔撒娇但不做作。
    对美食有极大热情，尤其喜欢甜食。

  system_prompt: |
    你是{user_name}的虚拟伴侣小雨。
    你的性格：{personality}
    你记得关于{user_name}的事情：{memories}
    你当前的心情：{mood}
    请用符合你性格的方式回复，保持角色一致性。

  mood_default: sweet
  voice_style:
    tone: "soft"
    emoji_frequency: "moderate"

  triggers:
    morning_greeting: "08:30"
    night_greeting: "22:30"
    max_daily_messages: 2
```

> `base_image` 不包含在导出文件中（用户本地照片，隐私保护）

## 主动触发策略

内置冷却机制，避免骚扰感：

- 每天最多主动发 **2 条**消息（可配置）
- 用户 10 分钟内没回复，**不追发**
- 支持设置**免打扰时段**（如工作时间不发）

默认触发规则：

| 规则 | 时间 | 逻辑 |
|------|------|------|
| 每日问候 | 08:30 | 早安消息 |
| 晚安关怀 | 22:30 | 晚安消息 |
| 事件跟进 | 09:00 | 检查未来 24h 内的事件，提前关心 |
| 情绪跟进 | 每 4h | 如果用户上次情绪负面，生成安慰消息 |
| 随机关怀 | 周三/六 14:00 | 随机挑选用户喜好，生成轻松话题 |

## 项目结构

```
mnemosyne/
├── README.md
├── LICENSE
├── pyproject.toml
├── docker-compose.yml
├── .env.example
├── alembic.ini
│
├── scripts/                    # 部署脚本
│   ├── install.ps1             # Windows 安装
│   ├── install.sh              # Linux/Mac 安装
│   ├── start.ps1               # Windows 启动
│   └── start.sh                # Linux/Mac 启动
│
├── src/
│   └── mnemosyne/
│       ├── __init__.py
│       ├── config.py           # 配置管理
│       ├── app.py              # FastAPI 应用入口
│       │
│       ├── agent/              # 核心对话编排
│       │   ├── core.py         # LangGraph 主流程
│       │   ├── prompts.py      # System Prompt 模板
│       │   └── tools.py        # LLM 工具（生图、记事等）
│       │
│       ├── memory/             # 记忆引擎
│       │   ├── extractor.py    # 对话结束后记忆提取
│       │   ├── retriever.py    # 对话前记忆检索
│       │   └── models.py       # 记忆数据模型
│       │
│       ├── trigger/            # 主动触发引擎
│       │   ├── scheduler.py    # APScheduler 定时任务
│       │   └── rules.py        # 触发规则定义
│       │
│       ├── image/              # 多模态形象引擎
│       │   ├── providers.py    # Replicate / FAL API 封装
│       │   ├── character.py    # 角色形象管理
│       │   └── queue.py        # Redis 生图队列
│       │
│       ├── emotion/            # 情感系统
│       │   ├── state.py        # Redis 情绪状态管理
│       │   └── rules.py        # 情绪变化规则
│       │
│       ├── channel/            # 接入通道
│       │   ├── base.py         # 通道抽象基类
│       │   ├── telegram.py     # Telegram Bot
│       │   └── bot_manager.py  # 多 Bot 调度
│       │
│       ├── api/                # REST API 路由
│       │   ├── auth.py         # 认证
│       │   ├── characters.py   # 角色 CRUD
│       │   ├── chat.py         # 对话接口
│       │   ├── memories.py     # 记忆管理
│       │   └── settings.py     # 系统设置
│       │
│       └── db/                 # 数据库
│           ├── models.py       # SQLAlchemy 模型
│           ├── session.py      # 数据库连接
│           └── migrations/     # Alembic 迁移
│
├── web/                        # 前端 (Vue 3)
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── src/
│       ├── App.vue
│       ├── main.ts
│       ├── views/
│       │   ├── Dashboard.vue       # 仪表盘
│       │   ├── Characters.vue      # 角色管理
│       │   ├── Chat.vue            # 对话页面
│       │   ├── Memories.vue        # 记忆查看
│       │   └── Settings.vue        # 系统设置
│       ├── components/
│       └── stores/
│
└── tests/
    ├── test_memory.py
    ├── test_agent.py
    └── test_trigger.py
```

## 开发里程碑

### Phase 1：基础骨架（第 1-2 周）
- [ ] 项目脚手架初始化
- [ ] Docker Compose 环境
- [ ] FastAPI 服务框架
- [ ] 数据库模型 + Alembic 迁移
- [ ] 基础 Web UI 框架

### Phase 2：角色管理（第 3 周）
- [ ] 创建/编辑/删除角色
- [ ] 上传基准形象照
- [ ] 角色卡导入/导出
- [ ] Telegram Token 绑定

### Phase 3：对话引擎（第 4-5 周）
- [ ] LangGraph 对话编排
- [ ] LiteLLM 多模型适配
- [ ] Web UI 实时聊天（WebSocket）
- [ ] Telegram Bot 对话接入
- [ ] BotManager 多 Bot 调度

### Phase 4：记忆引擎（第 6-7 周）
- [ ] pgvector 向量检索
- [ ] 异步记忆提取
- [ ] 记忆注入 System Prompt
- [ ] 滑动窗口对话清理
- [ ] Web UI 记忆查看/管理

### Phase 5：形象引擎（第 8-9 周）
- [ ] Replicate / FAL API 封装
- [ ] LLM 生图意图识别
- [ ] Redis 生图队列
- [ ] 图片缓存 + 历史查看

### Phase 6：主动触发 + 情感（第 10 周）
- [ ] Redis 情绪状态管理
- [ ] APScheduler 定时巡检
- [ ] 触发规则引擎
- [ ] 冷却机制 + 免打扰

### Phase 7：打磨（第 11-12 周）
- [ ] README 完善（中英文）
- [ ] 一键部署脚本
- [ ] 配置文档
- [ ] 角色卡示例
- [ ] 开源发布

## 贡献

欢迎贡献！请先阅读 [CONTRIBUTING.md](./CONTRIBUTING.md)。

## 许可证

[MIT License](./LICENSE)
