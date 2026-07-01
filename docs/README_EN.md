<div align="center">

# Mnemosyne

**Memory-driven open-source virtual companion agent framework**

*"Memory is the mirror of the soul" — Greek goddess of memory, Mnemosyne*

[English](./docs/README_EN.md) | 简体中文

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.11+-blue.svg)

</div>

---

## One-line Description

A self-hosted virtual companion framework that supports creating multiple characters with **consistent appearance, independent personality, and long-term memory**, connecting with you through Telegram and Web for ongoing emotional bonds.

## Core Features

- **Long-term Memory Engine** — Remembers everything you say, your preferences, and emotional fluctuations, persisted across conversations
- **Proactive Care** — LLM-driven proactive outreach decisions; autonomously decides when to message based on memory, emotion, and conversation gaps — like a real person
- **Visual Consistency** — Upload one reference photo, all generated images maintain the same face
- **Multi-character Support** — Create any number of companion characters, each with independent memory and personality
- **Emotion System** — Characters have real-time emotional states that respond to your behavior; mood affects reply speed and may trigger "read-not-reply"
- **Persona Compiler** — Input MBTI, attachment style, quirks, etc. and the LLM compiles a complete psychological profile
- **Multi-modal Generation** — Text, image, audio, and video generated asynchronously; text replies are never blocked by media
- **Multi-channel** — Telegram Bot + Web UI, interact anytime anywhere
- **S3 Compatible Storage** — Supports S3 object storage with automatic fallback to local filesystem
- **Smart Pagination** — Chat history with time segments and lazy loading on scroll
- **Cache Management** — Per-character media storage with selective or bulk cache clearing
- **Fully Open Source** — Self-hosted, your data stays local, privacy-friendly

## Architecture

```
                        ┌─────────────────────────┐
                        │      User Browser        │
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
│  (N Tokens)    │       │   (Unified Dispatcher) │
└────────────────┘       └───────────┬────────────┘
                                     │
              ┌──────────┬───────────┼───────────┬──────────┐
              ▼          ▼           ▼           ▼          ▼
         ┌────────┐ ┌────────┐ ┌─────────┐ ┌────────┐ ┌────────┐
         │ Dialog │ │ Memory │ │ Emotion │ │ Media  │ │Trigger │
         │ Engine │ │ Engine │ │ System  │ │ Engine │ │ Engine │
         │(LiteLLM│ │(pgvec) │ │ (Redis) │ │(Async) │ │(APSch) │
         └────┬───┘ └────┬───┘ └────┬────┘ └────┬───┘ └────┬───┘
              │          │          │           │          │
         ┌────▼──────────▼──────────▼───────────▼──────────▼───┐
         │                    PostgreSQL                         │
         │              (Main DB + pgvector)                     │
         │                    Redis                              │
         │              (Emotion + Task Queue + Cache)           │
         │                                                     │
         │        ┌─────────────────────────────┐              │
         │        │  S3 / Local File Storage     │              │
         │        │  (Images/Audio/Video/Avatar) │              │
         │        └─────────────────────────────┘              │
         └──────────────────────────────────────────────────────┘
```

## Tech Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| Language | Python 3.11+ | Most mature LLM ecosystem |
| Web Framework | FastAPI | Async-native, auto API docs |
| Frontend | Vue 3 + Vite + Tailwind CSS | Lightweight |
| LLM Gateway | LiteLLM | Unified interface, model-agnostic |
| Persona Compiler | LLM-based | Preprocesses personality traits into profiles |
| Vector Store | PostgreSQL + pgvector | No extra components needed |
| Cache/Queue | Redis | Emotion state + task queue |
| Scheduler | APScheduler | Lightweight cron |
| Telegram | python-telegram-bot v20+ | Native async |
| Image Gen | Replicate / FAL / HuggingFace / Stability | Multiple providers |
| Audio Gen | Edge TTS / ElevenLabs / HuggingFace / OpenAI-compatible | Default Edge TTS, free, no config needed |
| Video Gen | Replicate / HuggingFace / Luma | Multiple providers |
| File Storage | S3 / Local filesystem | Auto-detect, seamless fallback |
| Container | Docker Compose | One-click deploy |

## Quick Start

### Requirements

- Docker + Docker Compose (recommended)
- Or Python 3.11+ + PostgreSQL 15+ + Redis 7+ (manual)

### Docker Deploy (Recommended)

```bash
git clone https://github.com/your-username/mnemosyne.git
cd mnemosyne

# Copy and edit config
cp .env.example .env
# Edit .env with your LLM API Key

# Start
docker compose up -d

# Visit Web UI
# http://localhost:8080
```

### Windows Manual Deploy

```powershell
git clone https://github.com/your-username/mnemosyne.git
cd mnemosyne

# One-click install script
.\scripts\install.ps1

# Start services
.\scripts\start.ps1
```

### Linux / Mac Manual Deploy

```bash
git clone https://github.com/your-username/mnemosyne.git
cd mnemosyne

# One-click install script
chmod +x scripts/install.sh
./scripts/install.sh

# Start services
chmod +x scripts/start.sh
./scripts/start.sh
```

### Local Development
```powershell
.\scripts\dev.ps1

cd web
npm install
npm run dev
```

## Configuration

Copy `.env.example` to `.env` and edit:

```env
# ===== LLM =====
LLM_PROVIDER=openai              # openai / anthropic / ollama
LLM_API_KEY=sk-xxx               # Your API Key
LLM_MODEL=gpt-4o-mini            # Model name
LLM_BASE_URL=                    # Optional custom API endpoint

# ===== Database =====
DATABASE_URL=postgresql://mnemosyne:password@localhost:5432/mnemosyne
REDIS_URL=redis://localhost:6379/0

# ===== Image Generation =====
IMAGE_PROVIDER=replicate         # replicate / fal / stability / huggingface / openai-compatible
IMAGE_API_KEY=                   # Provider API Key
REPLICATE_API_TOKEN=r8_xxx       # Replicate API Token (legacy fallback)

# ===== Audio Generation (optional, default edge-tts free no config) =====
# AUDIO_PROVIDER=edge-tts        # edge-tts / elevenlabs / huggingface / openai-compatible
# AUDIO_API_KEY=

# ===== Video Generation (optional) =====
# VIDEO_PROVIDER=replicate       # replicate / huggingface / luma
# VIDEO_API_KEY=

# ===== S3 Storage (optional, falls back to local) =====
# S3_BUCKET=mnemosyne
# S3_ENDPOINT_URL=http://localhost:9000
# S3_ACCESS_KEY=minioadmin
# S3_SECRET_KEY=minioadmin

# ===== Telegram (optional) =====
# TELEGRAM_BOT_TOKEN_1=123456:ABC-DEF  # Character 1 Bot Token
# TELEGRAM_BOT_TOKEN_2=789012:GHI-JKL  # Character 2 Bot Token

# ===== Web =====
WEB_HOST=0.0.0.0
WEB_PORT=8080
SECRET_KEY=change-me-to-random-string
```

## Data Model

```sql
-- Users table (single-user mode, extensible)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Characters table (with persona compiler fields)
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
    -- Persona compiler fields
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

-- Conversations table (async media + cache management)
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

-- Memories table (long-term memory)
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

### Memory Types

| Type | Example | Purpose |
|------|---------|---------|
| `fact` | "User doesn't eat cilantro", "User's mom's surname is Li" | Long-term fact store, permanent |
| `feeling` | "User is anxious from overtime today" | Emotional state tracking, time-sensitive |
| `event` | "User has an exam next Wednesday" | Events that can trigger proactive care |

## Character Card Format

Mnemosyne supports YAML and JSON character card import/export for sharing character presets.

```yaml
# Mnemosyne Character Card v1.0
meta:
  format_version: "1.0"
  export_date: "2026-05-06"
  author: "user"

character:
  name: Xiaoyu
  personality: |
    A gentle and caring girl who speaks softly.
    Loves using sentence-ending particles, occasionally acts cute but not fake.
    Passionate about food, especially desserts.

  system_prompt: |
    You are {user_name}'s virtual companion Xiaoyu.
    Your personality: {personality}
    What you remember about {user_name}: {memories}
    Your current mood: {mood}
    Reply in a way that matches your personality, maintaining character consistency.

  mood_default: sweet
  voice_style:
    tone: "soft"
    emoji_frequency: "moderate"

  # Persona compiler fields (optional)
  mbti: INFP
  attachment_style: anxious
  tone: gentle, occasionally playful
  quirks: Uses emoticons, bites lip when nervous
```

> `base_image` is not included in exports (local photo, privacy protection)

## Emotion Reply System

Character mood affects reply behavior:

| Emotion | Reply Delay | Special Behavior |
|---------|------------|-----------------|
| sweet / happy / gentle | 1-3s | Warm, quick replies |
| shy | 3-6s | Hesitant pause |
| cool | 5-10s | Restrained |
| energetic | 0.5-2s | Instant reply |
| sad / anxious / lonely | 8-30s | May "read-not-reply" (15-30% chance, max 3 consecutive) |

## Proactive Care Strategy

LLM-driven proactive care system, no more mechanical greetings at fixed times:

- Checks every ~45 minutes, LLM autonomously decides **whether to message** and **what to say** based on full context
- LLM can see: current time, time since last conversation, current mood, events and preferences from memory, recent conversation summary
- Built-in safeguards: quiet hours, daily limit, cooldown period to avoid spam

### Examples

Decisions the LLM might make:
- "Chatted until 2am last night, let him sleep in — I'll reach out at 10am"
- "He has an exam tomorrow, I'll send an encouraging message tonight"
- "Haven't talked in 3 days, he mentioned he likes hotpot — I'll find a natural topic"
- "He just said he's feeling down, I'll send a comforting message now"
- "Just chatted 30 minutes ago, I won't bother him" (no message)

## Feature Trigger Examples

### Image Generation

| Trigger Method | Example Phrases |
|---------|---------|
| Keyword forced | "Send me a photo", "Take a selfie", "show me a pic" |
| LLM judgment | "What are you doing now?", "What are you wearing?", "Show me the weather where you are" |

### Audio Generation

| Example Phrases |
|---------|
| "Send me a voice message", "Sing a song", "What music have you been listening to?", "Say goodnight in a voice message" |

### Video Generation

| Example Phrases |
|---------|
| "Show me the sunset where you are", "Send me a video", "Let me see what you're doing" |

### Memory Extraction (Automatic, triggered after each conversation)

| Type | Trigger Content Examples |
|------|------------|
| Fact | "I like hotpot", "I have a cat", "I live in Beijing" |
| Feeling | "I'm feeling down today", "I've been stressed lately", "I miss you" |
| Event | "I have an exam next Tuesday", "Tomorrow is my birthday", "I'm going on a trip this weekend" |

### Scheduled Messages (LLM Tool Call)

| Example Phrases |
|---------|
| "Wake me up tomorrow", "I'm going to a meeting, find me in an hour", "Remind me to drink water at 3pm" |

### Emotion Changes

| Positive Triggers | Negative Triggers |
|---------|---------|
| like, love, happy, miss you, pretty, cute, thanks,辛苦 | hate, annoyed, go away, bored, angry, don't want to chat |

| Memory Triggers (Higher Intensity) |
|---------|
| breakup, divorce, passed away, exam, interview, sick, birthday, wedding, promotion, travel, fight, unemployed, moving, confession, heartbreak |

## Project Structure

```
mnemosyne/
├── README.md
├── LICENSE
├── pyproject.toml
├── docker-compose.yml
├── .env.example
├── alembic.ini
│
├── scripts/                    # Deploy scripts
│   ├── install.ps1             # Windows install
│   ├── install.sh              # Linux/Mac install
│   ├── start.ps1               # Windows start
│   └── start.sh                # Linux/Mac start
│
├── src/
│   └── mnemosyne/
│       ├── __init__.py
│       ├── config.py           # Configuration
│       ├── app.py              # FastAPI app entry
│       ├── storage.py          # Unified storage layer (S3 / Local)
│       │
│       ├── agent/              # Core dialog engine
│       │   ├── core.py         # Dialog engine + async media
│       │   ├── prompts.py      # System prompt templates
│       │   ├── tools.py        # LLM tools (image, memory, etc.)
│       │   └── persona_compiler.py  # Persona compiler
│       │
│       ├── memory/             # Memory engine
│       │   ├── extractor.py    # Post-conversation memory extraction
│       │   ├── retriever.py    # Pre-conversation memory retrieval
│       │   └── models.py       # Memory data models
│       │
│       ├── trigger/            # Proactive trigger engine
│       │   ├── scheduler.py    # LLM-driven proactive care scheduler
│       │   └── rules.py        # Context building + guard checks
│       │
│       ├── image/              # Image generation engine
│       │   └── providers.py    # Replicate / FAL / HuggingFace / Stability
│       │
│       ├── audio/              # Audio generation engine
│       │   └── providers.py    # Edge TTS / ElevenLabs / HuggingFace / OpenAI-compatible
│       │
│       ├── video/              # Video generation engine
│       │   └── providers.py    # Replicate / HuggingFace / Luma
│       │
│       ├── emotion/            # Emotion system
│       │   ├── state.py        # Redis emotion state + reply delay + read-not-reply
│       │   └── rules.py        # Emotion change rules
│       │
│       ├── channel/            # Access channels
│       │   ├── base.py         # Channel base class
│       │   ├── telegram.py     # Telegram Bot
│       │   └── bot_manager.py  # Multi-bot dispatcher
│       │
│       ├── api/                # REST API routes
│       │   ├── auth.py         # Authentication
│       │   ├── characters.py   # Character CRUD + persona compiler
│       │   ├── chat.py         # Chat API (REST + WebSocket)
│       │   ├── memories.py     # Memory management
│       │   └── settings.py     # System settings
│       │
│       └── db/                 # Database
│           ├── models.py       # SQLAlchemy models
│           ├── session.py      # Database connection
│           └── migrations/     # Alembic migrations
│
├── web/                        # Frontend (Vue 3)
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── src/
│       ├── App.vue
│       ├── main.ts
│       ├── views/
│       │   ├── Dashboard.vue       # Dashboard
│       │   ├── Characters.vue      # Character management (with persona form)
│       │   ├── CharacterDetail.vue # Character detail/edit
│       │   ├── Chat.vue            # Chat page (lazy load + time segments)
│       │   ├── CacheDialog.vue     # Cache management dialog
│       │   ├── Memories.vue        # Memory viewer (with force-directed graph)
│       │   ├── Analytics.vue       # Character analytics dashboard
│       │   └── Settings.vue        # System settings
│       ├── components/
│       └── stores/
│
└── tests/
    ├── test_memory.py
    ├── test_agent.py
    └── test_trigger.py
```

## Storage Architecture

Media files are stored per character:

```
uploads/
  characters/
    {character_id}/
      avatar.png          # Reference photo
      images/             # Generated images
      audio/              # Generated audio
      video/              # Generated video
```

When S3 is configured, files are stored in the S3 bucket and served via the `/api/storage/{path}` proxy endpoint. Falls back to local filesystem automatically when S3 is not configured.

## Development Milestones

### Phase 1: Foundation ✅
- [x] Project scaffolding
- [x] Docker Compose environment
- [x] FastAPI server framework
- [x] Database models + Alembic migrations
- [x] Basic Web UI framework

### Phase 2: Character Management ✅
- [x] Create/edit/delete characters
- [x] Upload reference avatar
- [x] Character card import/export
- [x] Telegram Token binding
- [x] Persona compiler (MBTI, attachment style, etc.)

### Phase 3: Dialog Engine ✅
- [x] LiteLLM multi-model adaptation
- [x] Web UI real-time chat (WebSocket)
- [x] Telegram Bot dialog integration
- [x] BotManager multi-bot scheduling
- [x] Chat history segments + lazy loading

### Phase 4: Memory Engine ✅
- [x] pgvector vector search
- [x] Async memory extraction
- [x] Memory injection into System Prompt
- [x] Sliding window conversation cleanup
- [x] Web UI memory viewer/management

### Phase 5: Media Engine ✅
- [x] Multi-provider image generation (Replicate / FAL / HuggingFace / Stability)
- [x] Audio generation (Edge TTS / ElevenLabs / HuggingFace / OpenAI-compatible)
- [x] Video generation (Replicate / HuggingFace / Luma)
- [x] Async media generation (non-blocking text replies)
- [x] Per-character storage + cache management

### Phase 6: Proactive Trigger + Emotion ✅
- [x] Redis emotion state management
- [x] Mood affects reply speed
- [x] "Read-not-reply" mechanism
- [x] LLM-driven proactive care decisions
- [x] Cooldown mechanism + quiet hours

### Phase 7: Storage + Polish
- [x] S3 compatible storage layer (auto-fallback to local)
- [x] Chinese and English README
- [x] One-click deploy scripts
- [x] Configuration documentation
- [x] Character card template library
- [ ] Unit test improvements

## Contributing

Contributions welcome! Please read [CONTRIBUTING.md](../CONTRIBUTING.md) first.

## License

[MIT License](../LICENSE)
