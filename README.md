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
- **情感系统** —— 角色有实时情绪状态，会因为你的态度而开心或失落；不同心情影响回复速度，甚至可能"已读不回"
- **人格编译器** —— 输入 MBTI、依恋风格、口头禅等，LLM 自动编译为完整人格 profile
- **多模态生成** —— 文本、图片、音频、视频异步生成，文本回复不被媒体阻塞
- **多通道接入** —— Telegram Bot + Web UI，随时随地互动
- **S3 兼容存储** —— 支持 S3 对象存储，自动回退本地文件系统
- **智能分页** —— 聊天记录按时间分段显示，向上滚动懒加载历史消息
- **缓存管理** —— 按角色独立存储媒体文件，支持清除指定或全部缓存
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
         │ Dialog │ │ Memory │ │ Emotion │ │ Media  │ │Trigger │
         │ Engine │ │ Engine │ │ System  │ │ Engine │ │ Engine │
         │(LiteLLM│ │(pgvec) │ │ (Redis) │ │(异步生成)│ │(APSch) │
         └────┬───┘ └────┬───┘ └────┬────┘ └────┬───┘ └────┬───┘
              │          │          │           │          │
         ┌────▼──────────▼──────────▼───────────▼──────────▼───┐
         │                    PostgreSQL                         │
         │              (主库 + pgvector 向量存储)                │
         │                    Redis                              │
         │              (情绪状态 + 任务队列 + 缓存)              │
         │                                                     │
         │        ┌─────────────────────────────┐              │
         │        │  S3 / Local 文件存储          │              │
         │        │  (图片/音频/视频/头像)         │              │
         │        └─────────────────────────────┘              │
         └──────────────────────────────────────────────────────┘
```

## 技术栈

| 层级 | 技术选型 | 说明 |
|------|---------|------|
| 语言 | Python 3.11+ | LLM 生态最成熟 |
| Web 框架 | FastAPI | 异步原生，自动 API 文档 |
| 前端 | Vue 3 + Vite + Tailwind CSS | 轻量简洁 |
| LLM 调用 | LiteLLM | 统一接口，模型无关 |
| 人格编译 | Persona Compiler | LLM 驱动的人格预处理 |
| 向量存储 | PostgreSQL + pgvector | 无需额外组件 |
| 缓存/队列 | Redis | 情绪状态 + 任务队列 |
| 定时任务 | APScheduler | 轻量级调度 |
| Telegram | python-telegram-bot v20+ | 原生异步 |
| 图像生成 | Replicate / FAL / HuggingFace / Stability | 多 Provider 可选 |
| 音频生成 | ElevenLabs / HuggingFace / OpenAI 兼容 | 多 Provider 可选 |
| 视频生成 | Replicate / HuggingFace / Luma | 多 Provider 可选 |
| 文件存储 | S3 / 本地文件系统 | 自动检测，无缝回退 |
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
```powershell
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

# ===== 图像生成 =====
IMAGE_PROVIDER=replicate         # replicate / fal / stability / huggingface / openai-compatible
IMAGE_API_KEY=                   # Provider API Key
REPLICATE_API_TOKEN=r8_xxx       # Replicate API Token (legacy fallback)

# ===== 音频生成（可选）=====
# AUDIO_PROVIDER=elevenlabs      # elevenlabs / huggingface / openai-compatible
# AUDIO_API_KEY=

# ===== 视频生成（可选）=====
# VIDEO_PROVIDER=replicate       # replicate / huggingface / luma
# VIDEO_API_KEY=

# ===== S3 存储（可选，不配置则使用本地存储）=====
# S3_BUCKET=mnemosyne
# S3_ENDPOINT_URL=http://localhost:9000
# S3_ACCESS_KEY=minioadmin
# S3_SECRET_KEY=minioadmin

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

-- 角色表（含人格编译字段）
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
    -- 人格编译器字段
    gender VARCHAR(20),
    age VARCHAR(20),
    occupation VARCHAR(100),
    mbti VARCHAR(10),
    zodiac VARCHAR(20),
    attachment_style VARCHAR(50),
    core_vulnerability TEXT,
    tone VARCHAR(100),
    quirks TEXT,
    emoji_usage VARCHAR(50),
    visual_style TEXT,
    physical_attributes TEXT,
    processed_personality TEXT,
    interaction_rules JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 对话表（支持异步媒体 + 缓存管理）
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    character_id UUID REFERENCES characters(id) ON DELETE CASCADE,
    role VARCHAR(10) NOT NULL,
    content TEXT NOT NULL,
    has_image BOOLEAN DEFAULT FALSE,
    image_url TEXT,
    audio_url TEXT,
    video_url TEXT,
    media_status VARCHAR(20),    -- pending / ready / cleared / read_only
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

  # 人格编译器字段（可选）
  mbti: INFP
  attachment_style: anxious
  tone: 温柔、撒娇、偶尔任性
  quirks: 喜欢用颜文字，紧张时会咬嘴唇

  triggers:
    morning_greeting: "08:30"
    night_greeting: "22:30"
    max_daily_messages: 2
```

> `base_image` 不包含在导出文件中（用户本地照片，隐私保护）

## 情感回复系统

角色的当前心情会影响回复行为：

| 情绪 | 回复延迟 | 特殊行为 |
|------|---------|---------|
| sweet / happy / gentle | 1-3 秒 | 温暖快速回复 |
| shy | 3-6 秒 | 犹豫片刻 |
| cool | 5-10 秒 | 克制冷静 |
| energetic | 0.5-2 秒 | 活泼秒回 |
| sad / anxious / lonely | 8-30 秒 | 可能"已读不回"（概率 15-30%，连续不超过 3 次）|

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
│       ├── storage.py          # 统一存储抽象层（S3 / Local）
│       │
│       ├── agent/              # 核心对话编排
│       │   ├── core.py         # 对话引擎 + 异步媒体生成
│       │   ├── prompts.py      # System Prompt 模板
│       │   ├── tools.py        # LLM 工具（生图、记事等）
│       │   └── persona_compiler.py  # 人格编译器
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
│       ├── image/              # 图像生成引擎
│       │   └── providers.py    # Replicate / FAL / HuggingFace / Stability
│       │
│       ├── audio/              # 音频生成引擎
│       │   └── providers.py    # ElevenLabs / HuggingFace / OpenAI 兼容
│       │
│       ├── video/              # 视频生成引擎
│       │   └── providers.py    # Replicate / HuggingFace / Luma
│       │
│       ├── emotion/            # 情感系统
│       │   ├── state.py        # Redis 情绪状态 + 回复延迟 + 已读不回
│       │   └── rules.py        # 情绪变化规则
│       │
│       ├── channel/            # 接入通道
│       │   ├── base.py         # 通道抽象基类
│       │   ├── telegram.py     # Telegram Bot
│       │   └── bot_manager.py  # 多 Bot 调度
│       │
│       ├── api/                # REST API 路由
│       │   ├── auth.py         # 认证
│       │   ├── characters.py   # 角色 CRUD + 人格编译
│       │   ├── chat.py         # 对话接口（REST + WebSocket）
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
│       │   ├── Characters.vue      # 角色管理（含人格编译表单）
│       │   ├── CharacterDetail.vue # 角色详情/编辑
│       │   ├── Chat.vue            # 对话页面（懒加载 + 时间分段）
│       │   ├── CacheDialog.vue     # 缓存管理弹窗
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

## 存储架构

媒体文件按角色独立存储：

```
uploads/
  characters/
    {character_id}/
      avatar.png          # 基准照片
      images/             # 对话生成的图片
      audio/              # 对话生成的音频
      video/              # 对话生成的视频
```

配置 S3 后，文件自动存储到 S3 bucket，前端通过 `/api/storage/{path}` 代理端点访问。未配置 S3 时自动回退到本地文件系统。

## 开发里程碑

### Phase 1：基础骨架 ✅
- [x] 项目脚手架初始化
- [x] Docker Compose 环境
- [x] FastAPI 服务框架
- [x] 数据库模型 + Alembic 迁移
- [x] 基础 Web UI 框架

### Phase 2：角色管理 ✅
- [x] 创建/编辑/删除角色
- [x] 上传基准形象照
- [x] 角色卡导入/导出
- [x] Telegram Token 绑定
- [x] 人格编译器（MBTI、依恋风格等）

### Phase 3：对话引擎 ✅
- [x] LiteLLM 多模型适配
- [x] Web UI 实时聊天（WebSocket）
- [x] Telegram Bot 对话接入
- [x] BotManager 多 Bot 调度
- [x] 聊天记录分段 + 懒加载

### Phase 4：记忆引擎 ✅
- [x] pgvector 向量检索
- [x] 异步记忆提取
- [x] 记忆注入 System Prompt
- [x] 滑动窗口对话清理
- [x] Web UI 记忆查看/管理

### Phase 5：媒体引擎 ✅
- [x] 多 Provider 图像生成（Replicate / FAL / HuggingFace / Stability）
- [x] 音频生成（ElevenLabs / HuggingFace / OpenAI 兼容）
- [x] 视频生成（Replicate / HuggingFace / Luma）
- [x] 异步媒体生成（不阻塞文本回复）
- [x] 按角色独立存储 + 缓存管理

### Phase 6：主动触发 + 情感 ✅
- [x] Redis 情绪状态管理
- [x] 心情影响回复速度
- [x] "已读不回"机制
- [x] APScheduler 定时巡检
- [x] 触发规则引擎
- [x] 冷却机制 + 免打扰

### Phase 7：存储 + 打磨
- [x] S3 兼容存储层（自动回退本地）
- [x] 中英文 README
- [x] 一键部署脚本
- [x] 配置文档
- [ ] 角色卡示例库
- [ ] 单元测试完善

## 贡献

欢迎贡献！请先阅读 [CONTRIBUTING.md](./CONTRIBUTING.md)。

## 许可证

[MIT License](./LICENSE)
