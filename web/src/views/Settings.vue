<script setup lang="ts">
import { ref, onMounted } from 'vue'
import axios from 'axios'

const form = ref({
  llm_provider: 'openai',
  llm_api_key: '',
  llm_model: '',
  llm_base_url: '',
  embedding_provider: 'local',
  embedding_model: '',
  image_provider: 'replicate',
  image_api_key: '',
  image_base_url: '',
  image_model: '',
  audio_provider: 'elevenlabs',
  audio_api_key: '',
  audio_base_url: '',
  audio_model: '',
  video_provider: 'replicate',
  video_api_key: '',
  video_base_url: '',
  video_model: '',
  replicate_api_token: '',
  fal_key: '',
  telegram_bot_token_1: '',
  telegram_bot_token_2: '',
  max_daily_messages: 2,
  cooldown_minutes: 10,
  quiet_hours_start: 0,
  quiet_hours_end: 7,
})

const loading = ref(true)
const saving = ref(false)
const saved = ref(false)
const restartRequired = ref(false)
const error = ref('')

onMounted(async () => {
  try {
    const { data } = await axios.get('/api/settings/')
    form.value = { ...form.value, ...data }
  } finally {
    loading.value = false
  }
})

async function handleSave() {
  saving.value = true
  error.value = ''
  saved.value = false
  restartRequired.value = false
  try {
    const { data } = await axios.put('/api/settings/', form.value)
    saved.value = true
    if (data.restart_required) {
      restartRequired.value = true
    }
    setTimeout(() => (saved.value = false), 3000)
  } catch (e: any) {
    error.value = e.response?.data?.detail || 'Save failed'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div>
    <!-- Header -->
    <div class="mb-8">
      <h2 class="text-2xl font-display font-bold text-gray-800">Settings</h2>
      <p class="text-sm text-gray-500 mt-1">Configure your Mnemosyne instance</p>
    </div>

    <!-- Loading skeleton -->
    <div v-if="loading" class="max-w-2xl space-y-5">
      <div v-for="i in 4" :key="i" class="card p-6">
        <div class="h-5 w-32 skeleton mb-4"></div>
        <div class="space-y-3">
          <div v-for="j in 3" :key="j">
            <div class="h-4 w-20 skeleton mb-1.5"></div>
            <div class="h-10 w-full skeleton rounded-xl"></div>
          </div>
        </div>
      </div>
    </div>

    <form v-else @submit.prevent="handleSave" class="max-w-2xl space-y-5 animate-fade-in">

      <!-- LLM Config -->
      <section class="card p-6 animate-slide-up">
        <h3 class="font-display font-bold text-gray-800 mb-4 flex items-center gap-2">
          <svg class="w-5 h-5 text-accent" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456zM16.894 20.567L16.5 21.75l-.394-1.183a2.25 2.25 0 00-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 001.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 001.423 1.423l1.183.394-1.183.394a2.25 2.25 0 00-1.423 1.423z" />
          </svg>
          LLM Configuration
        </h3>
        <div class="space-y-4">
          <div>
            <label class="block text-sm font-semibold text-gray-700 mb-1.5">Provider</label>
            <select v-model="form.llm_provider" class="input">
              <option value="openai">OpenAI</option>
              <option value="anthropic">Anthropic</option>
              <option value="ollama">Ollama (Local)</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-semibold text-gray-700 mb-1.5">API Key</label>
            <input v-model="form.llm_api_key" type="password" placeholder="sk-..." class="input" />
          </div>
          <div>
            <label class="block text-sm font-semibold text-gray-700 mb-1.5">Model</label>
            <input v-model="form.llm_model" type="text" placeholder="gpt-4o-mini" class="input" />
          </div>
          <div>
            <label class="block text-sm font-semibold text-gray-700 mb-1.5">
              Base URL
              <span class="text-xs font-normal text-gray-400 ml-1">(optional)</span>
            </label>
            <input v-model="form.llm_base_url" type="text" placeholder="https://api.deepseek.com" class="input" />
            <p class="text-xs text-gray-400 mt-1.5">For custom providers like DeepSeek, Moonshot, etc.</p>
          </div>
        </div>
      </section>

      <!-- Embedding -->
      <section class="card p-6 animate-slide-up" style="animation-delay: 60ms; animation-fill-mode: backwards;">
        <h3 class="font-display font-bold text-gray-800 mb-4 flex items-center gap-2">
          <svg class="w-5 h-5 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M21 7.5l-9-5.25L3 7.5m18 0l-9 5.25m9-5.25v9l-9 5.25M3 7.5l9 5.25M3 7.5v9l9 5.25m0-9v9" />
          </svg>
          Embedding Model
        </h3>
        <div class="space-y-4">
          <div>
            <label class="block text-sm font-semibold text-gray-700 mb-1.5">Provider</label>
            <select v-model="form.embedding_provider" class="input">
              <option value="local">Local (sentence-transformers)</option>
              <option value="openai">OpenAI</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-semibold text-gray-700 mb-1.5">Model</label>
            <input v-model="form.embedding_model" type="text" placeholder="BAAI/bge-m3" class="input" />
          </div>
        </div>
      </section>

      <!-- Image Generation -->
      <section class="card p-6 animate-slide-up" style="animation-delay: 120ms; animation-fill-mode: backwards;">
        <h3 class="font-display font-bold text-gray-800 mb-1 flex items-center gap-2">
          <svg class="w-5 h-5 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909M3.75 21h16.5A2.25 2.25 0 0022.5 18.75V5.25A2.25 2.25 0 0020.25 3H3.75A2.25 2.25 0 001.5 5.25v13.5A2.25 2.25 0 003.75 21z" />
          </svg>
          Image Generation
        </h3>
        <p class="text-xs text-gray-400 mb-4 ml-7">Unified API abstraction — switch providers by changing config</p>
        <div class="space-y-4">
          <div>
            <label class="block text-sm font-semibold text-gray-700 mb-1.5">Provider</label>
            <select v-model="form.image_provider" class="input">
              <option value="replicate">Replicate</option>
              <option value="fal">FAL.ai</option>
              <option value="stability">Stability AI</option>
              <option value="huggingface">Hugging Face (Free)</option>
              <option value="openai-compatible">OpenAI Compatible</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-semibold text-gray-700 mb-1.5">API Key</label>
            <input v-model="form.image_api_key" type="password" placeholder="API key for selected provider" class="input" />
          </div>
          <div>
            <label class="block text-sm font-semibold text-gray-700 mb-1.5">
              Base URL
              <span class="text-xs font-normal text-gray-400 ml-1">(optional)</span>
            </label>
            <input v-model="form.image_base_url" type="text" placeholder="https://custom-api.example.com/v1" class="input" />
            <p class="text-xs text-gray-400 mt-1.5">For self-hosted or custom endpoints</p>
          </div>
          <div>
            <label class="block text-sm font-semibold text-gray-700 mb-1.5">
              Model
              <span class="text-xs font-normal text-gray-400 ml-1">(optional)</span>
            </label>
            <input v-model="form.image_model" type="text" placeholder="Provider default if empty" class="input" />
          </div>
        </div>
      </section>

      <!-- Audio Generation -->
      <section class="card p-6 animate-slide-up" style="animation-delay: 180ms; animation-fill-mode: backwards;">
        <h3 class="font-display font-bold text-gray-800 mb-1 flex items-center gap-2">
          <svg class="w-5 h-5 text-accent" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M19.114 5.636a9 9 0 010 12.728M16.463 8.288a5.25 5.25 0 010 7.424M6.75 8.25l4.72-4.72a.75.75 0 011.28.53v15.88a.75.75 0 01-1.28.53l-4.72-4.72H4.51c-.88 0-1.704-.507-1.938-1.354A9.01 9.01 0 012.25 12c0-.83.112-1.633.322-2.396C2.806 8.756 3.63 8.25 4.51 8.25H6.75z" />
          </svg>
          Audio Generation
        </h3>
        <p class="text-xs text-gray-400 mb-4 ml-7">TTS, music, and sound effects</p>
        <div class="space-y-4">
          <div>
            <label class="block text-sm font-semibold text-gray-700 mb-1.5">Provider</label>
            <select v-model="form.audio_provider" class="input">
              <option value="elevenlabs">ElevenLabs (TTS)</option>
              <option value="huggingface">Hugging Face (Music)</option>
              <option value="openai-compatible">OpenAI Compatible (TTS)</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-semibold text-gray-700 mb-1.5">API Key</label>
            <input v-model="form.audio_api_key" type="password" placeholder="API key for selected provider" class="input" />
          </div>
          <div>
            <label class="block text-sm font-semibold text-gray-700 mb-1.5">
              Base URL
              <span class="text-xs font-normal text-gray-400 ml-1">(optional)</span>
            </label>
            <input v-model="form.audio_base_url" type="text" placeholder="https://custom-api.example.com/v1" class="input" />
          </div>
          <div>
            <label class="block text-sm font-semibold text-gray-700 mb-1.5">
              Model
              <span class="text-xs font-normal text-gray-400 ml-1">(optional)</span>
            </label>
            <input v-model="form.audio_model" type="text" placeholder="Provider default if empty" class="input" />
          </div>
        </div>
      </section>

      <!-- Video Generation -->
      <section class="card p-6 animate-slide-up" style="animation-delay: 240ms; animation-fill-mode: backwards;">
        <h3 class="font-display font-bold text-gray-800 mb-1 flex items-center gap-2">
          <svg class="w-5 h-5 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="m15.75 10.5 4.72-4.72a.75.75 0 0 1 1.28.53v11.38a.75.75 0 0 1-1.28.53l-4.72-4.72M4.5 18.75h9a2.25 2.25 0 0 0 2.25-2.25v-9a2.25 2.25 0 0 0-2.25-2.25h-9A2.25 2.25 0 0 0 2.25 7.5v9a2.25 2.25 0 0 0 2.25 2.25Z" />
          </svg>
          Video Generation
        </h3>
        <p class="text-xs text-gray-400 mb-4 ml-7">Short video clips from text prompts</p>
        <div class="space-y-4">
          <div>
            <label class="block text-sm font-semibold text-gray-700 mb-1.5">Provider</label>
            <select v-model="form.video_provider" class="input">
              <option value="replicate">Replicate</option>
              <option value="huggingface">Hugging Face</option>
              <option value="luma">Luma AI (Dream Machine)</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-semibold text-gray-700 mb-1.5">API Key</label>
            <input v-model="form.video_api_key" type="password" placeholder="API key for selected provider" class="input" />
          </div>
          <div>
            <label class="block text-sm font-semibold text-gray-700 mb-1.5">
              Base URL
              <span class="text-xs font-normal text-gray-400 ml-1">(optional)</span>
            </label>
            <input v-model="form.video_base_url" type="text" placeholder="https://custom-api.example.com/v1" class="input" />
          </div>
          <div>
            <label class="block text-sm font-semibold text-gray-700 mb-1.5">
              Model
              <span class="text-xs font-normal text-gray-400 ml-1">(optional)</span>
            </label>
            <input v-model="form.video_model" type="text" placeholder="Provider default if empty" class="input" />
          </div>
        </div>
      </section>

      <!-- Telegram -->
      <section class="card p-6 animate-slide-up" style="animation-delay: 300ms; animation-fill-mode: backwards;">
        <h3 class="font-display font-bold text-gray-800 mb-4 flex items-center gap-2">
          <svg class="w-5 h-5 text-accent" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M8.625 12a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H8.25m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H12m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 01-2.555-.337A5.972 5.972 0 015.41 20.97a5.969 5.969 0 01-.474-.065 4.48 4.48 0 00.978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25z" />
          </svg>
          Telegram Bots
        </h3>
        <div class="space-y-4">
          <div>
            <label class="block text-sm font-semibold text-gray-700 mb-1.5">Bot Token 1</label>
            <input v-model="form.telegram_bot_token_1" type="password" placeholder="123456:ABC-DEF..." class="input" />
          </div>
          <div>
            <label class="block text-sm font-semibold text-gray-700 mb-1.5">Bot Token 2</label>
            <input v-model="form.telegram_bot_token_2" type="password" placeholder="789012:GHI-JKL..." class="input" />
          </div>
        </div>
      </section>

      <!-- Trigger Settings -->
      <section class="card p-6 animate-slide-up" style="animation-delay: 360ms; animation-fill-mode: backwards;">
        <h3 class="font-display font-bold text-gray-800 mb-4 flex items-center gap-2">
          <svg class="w-5 h-5 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0" />
          </svg>
          Proactive Triggers
        </h3>
        <div class="space-y-4">
          <div>
            <label class="block text-sm font-semibold text-gray-700 mb-1.5">Max Daily Messages</label>
            <input v-model.number="form.max_daily_messages" type="number" min="0" max="10" class="input" />
          </div>
          <div>
            <label class="block text-sm font-semibold text-gray-700 mb-1.5">Cooldown (minutes)</label>
            <input v-model.number="form.cooldown_minutes" type="number" min="1" class="input" />
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-semibold text-gray-700 mb-1.5">Quiet Hours Start</label>
              <input v-model.number="form.quiet_hours_start" type="number" min="0" max="23" class="input" />
            </div>
            <div>
              <label class="block text-sm font-semibold text-gray-700 mb-1.5">Quiet Hours End</label>
              <input v-model.number="form.quiet_hours_end" type="number" min="0" max="23" class="input" />
            </div>
          </div>
        </div>
      </section>

      <!-- Submit -->
      <div class="flex items-center gap-3 pt-2 animate-slide-up" style="animation-delay: 420ms; animation-fill-mode: backwards;">
        <button type="submit" :disabled="saving" class="btn-primary">
          <svg v-if="saving" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
          </svg>
          <svg v-else class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5" />
          </svg>
          {{ saving ? 'Saving...' : 'Save Settings' }}
        </button>
        <transition
          enter-active-class="transition duration-200 ease-out"
          enter-from-class="opacity-0 -translate-x-2"
          enter-to-class="opacity-100 translate-x-0"
          leave-active-class="transition duration-150 ease-in"
          leave-from-class="opacity-100"
          leave-to-class="opacity-0"
        >
          <span v-if="saved" class="text-green-600 text-sm font-medium flex items-center gap-1">
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Saved!
          </span>
        </transition>
        <span v-if="restartRequired" class="text-amber-600 text-sm font-medium flex items-center gap-1">
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
          </svg>
          Restart server to apply
        </span>
        <span v-if="error" class="text-red-500 text-sm font-medium flex items-center gap-1">
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
          </svg>
          {{ error }}
        </span>
      </div>
    </form>
  </div>
</template>
