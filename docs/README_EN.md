# Mnemosyne

**Memory-driven open-source virtual companion agent framework**

*Self-hosted virtual companions with persistent memory, consistent appearance, and proactive care.*

[简体中文](../README.md) | English

## Features

- **Long-term Memory** — Remembers conversations, preferences, and emotions across sessions
- **Proactive Care** — Sends caring messages based on memory and time triggers
- **Visual Consistency** — Upload one reference photo, all generated images maintain the same face
- **Multi-character** — Create multiple companions, each with independent memory and personality
- **Emotion System** — Real-time emotional states that respond to your interactions; mood affects reply speed and may trigger "read-not-reply"
- **Persona Compiler** — Input MBTI, attachment style, quirks, etc. and the LLM compiles a complete psychological profile
- **Async Media Generation** — Text, image, audio, and video generated asynchronously; text replies are never blocked by media
- **Multi-channel** — Telegram Bot + Web UI
- **S3 Compatible Storage** — S3 object storage with automatic fallback to local filesystem
- **Smart Pagination** — Chat history with time segments and lazy loading on scroll
- **Cache Management** — Per-character media storage with selective or bulk cache clearing
- **Fully Open Source** — Self-hosted, your data stays local

## Quick Start

```bash
git clone https://github.com/your-username/mnemosyne.git
cd mnemosyne
cp .env.example .env
# Edit .env with your API keys
docker compose up -d
# Visit http://localhost:8080
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
| Audio Gen | ElevenLabs / HuggingFace / OpenAI-compatible | Multiple providers |
| Video Gen | Replicate / HuggingFace / Luma | Multiple providers |
| File Storage | S3 / Local filesystem | Auto-detect, seamless fallback |

## Configuration

Copy `.env.example` to `.env` and edit:

```env
# ===== LLM =====
LLM_PROVIDER=openai              # openai / anthropic / ollama
LLM_API_KEY=sk-xxx
LLM_MODEL=gpt-4o-mini
LLM_BASE_URL=                    # optional custom API endpoint

# ===== Database =====
DATABASE_URL=postgresql://mnemosyne:password@localhost:5432/mnemosyne
REDIS_URL=redis://localhost:6379/0

# ===== Image Generation =====
IMAGE_PROVIDER=replicate         # replicate / fal / stability / huggingface / openai-compatible
IMAGE_API_KEY=

# ===== Audio Generation (optional) =====
# AUDIO_PROVIDER=elevenlabs      # elevenlabs / huggingface / openai-compatible
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
# TELEGRAM_BOT_TOKEN_1=123456:ABC-DEF
# TELEGRAM_BOT_TOKEN_2=789012:GHI-JKL

# ===== Web =====
WEB_HOST=0.0.0.0
WEB_PORT=8080
SECRET_KEY=change-me-to-random-string
```

## Emotion Reply System

Character mood affects reply behavior:

| Emotion | Reply Delay | Special Behavior |
|---------|------------|-----------------|
| sweet / happy / gentle | 1-3s | Warm, quick replies |
| shy | 3-6s | Hesitant pause |
| cool | 5-10s | Restrained |
| energetic | 0.5-2s | Instant reply |
| sad / anxious / lonely | 8-30s | May "read-not-reply" (15-30% chance, max 3 consecutive) |

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

## Character Card Format

Supports YAML and JSON import/export for sharing character presets:

```yaml
meta:
  format_version: "1.0"

character:
  name: Xiaoyu
  personality: |
    A gentle and caring girl who speaks softly.
    Loves food, especially desserts.

  mood_default: sweet
  mbti: INFP
  attachment_style: anxious
  tone: gentle, occasionally playful
```

See [README.md](../README.md) for full documentation in Chinese.
