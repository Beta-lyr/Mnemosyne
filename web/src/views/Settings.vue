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
  <div class="max-w-2xl">
    <h2 class="text-2xl font-bold mb-6">Settings</h2>

    <div v-if="loading" class="text-gray-500">Loading...</div>

    <form v-else @submit.prevent="handleSave" class="space-y-6">
      <!-- LLM Config -->
      <section class="bg-white rounded-xl border p-6">
        <h3 class="text-lg font-semibold mb-4">LLM Configuration</h3>
        <div class="space-y-3">
          <div>
            <label class="block text-sm font-medium mb-1">Provider</label>
            <select v-model="form.llm_provider"
              class="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-purple-500 focus:outline-none">
              <option value="openai">OpenAI</option>
              <option value="anthropic">Anthropic</option>
              <option value="ollama">Ollama (Local)</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium mb-1">API Key</label>
            <input v-model="form.llm_api_key" type="password" placeholder="sk-..."
              class="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-purple-500 focus:outline-none" />
          </div>
          <div>
            <label class="block text-sm font-medium mb-1">Model</label>
            <input v-model="form.llm_model" type="text" placeholder="gpt-4o-mini"
              class="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-purple-500 focus:outline-none" />
          </div>
          <div>
            <label class="block text-sm font-medium mb-1">Base URL (optional)</label>
            <input v-model="form.llm_base_url" type="text" placeholder="https://api.deepseek.com/v1"
              class="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-purple-500 focus:outline-none" />
            <p class="text-xs text-gray-400 mt-1">For custom providers like DeepSeek, Moonshot, etc.</p>
          </div>
        </div>
      </section>

      <!-- Embedding -->
      <section class="bg-white rounded-xl border p-6">
        <h3 class="text-lg font-semibold mb-4">Embedding Model</h3>
        <div class="space-y-3">
          <div>
            <label class="block text-sm font-medium mb-1">Provider</label>
            <select v-model="form.embedding_provider"
              class="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-purple-500 focus:outline-none">
              <option value="local">Local (sentence-transformers)</option>
              <option value="openai">OpenAI</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium mb-1">Model</label>
            <input v-model="form.embedding_model" type="text" placeholder="BAAI/bge-m3"
              class="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-purple-500 focus:outline-none" />
          </div>
        </div>
      </section>

      <!-- Image Generation -->
      <section class="bg-white rounded-xl border p-6">
        <h3 class="text-lg font-semibold mb-4">Image Generation</h3>
        <div class="space-y-3">
          <div>
            <label class="block text-sm font-medium mb-1">Provider</label>
            <select v-model="form.image_provider"
              class="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-purple-500 focus:outline-none">
              <option value="replicate">Replicate</option>
              <option value="fal">FAL.ai</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium mb-1">Replicate API Token</label>
            <input v-model="form.replicate_api_token" type="password" placeholder="r8_..."
              class="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-purple-500 focus:outline-none" />
          </div>
          <div>
            <label class="block text-sm font-medium mb-1">FAL API Key</label>
            <input v-model="form.fal_key" type="password" placeholder="..."
              class="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-purple-500 focus:outline-none" />
          </div>
        </div>
      </section>

      <!-- Telegram -->
      <section class="bg-white rounded-xl border p-6">
        <h3 class="text-lg font-semibold mb-4">Telegram Bots</h3>
        <div class="space-y-3">
          <div>
            <label class="block text-sm font-medium mb-1">Bot Token 1</label>
            <input v-model="form.telegram_bot_token_1" type="password" placeholder="123456:ABC-DEF..."
              class="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-purple-500 focus:outline-none" />
          </div>
          <div>
            <label class="block text-sm font-medium mb-1">Bot Token 2</label>
            <input v-model="form.telegram_bot_token_2" type="password" placeholder="789012:GHI-JKL..."
              class="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-purple-500 focus:outline-none" />
          </div>
        </div>
      </section>

      <!-- Trigger Settings -->
      <section class="bg-white rounded-xl border p-6">
        <h3 class="text-lg font-semibold mb-4">Proactive Triggers</h3>
        <div class="space-y-3">
          <div>
            <label class="block text-sm font-medium mb-1">Max Daily Messages</label>
            <input v-model.number="form.max_daily_messages" type="number" min="0" max="10"
              class="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-purple-500 focus:outline-none" />
          </div>
          <div>
            <label class="block text-sm font-medium mb-1">Cooldown (minutes)</label>
            <input v-model.number="form.cooldown_minutes" type="number" min="1"
              class="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-purple-500 focus:outline-none" />
          </div>
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-sm font-medium mb-1">Quiet Hours Start</label>
              <input v-model.number="form.quiet_hours_start" type="number" min="0" max="23"
                class="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-purple-500 focus:outline-none" />
            </div>
            <div>
              <label class="block text-sm font-medium mb-1">Quiet Hours End</label>
              <input v-model.number="form.quiet_hours_end" type="number" min="0" max="23"
                class="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-purple-500 focus:outline-none" />
            </div>
          </div>
        </div>
      </section>

      <!-- Submit -->
      <div class="flex items-center gap-3">
        <button type="submit" :disabled="saving"
          class="bg-purple-600 text-white px-6 py-2 rounded-lg hover:bg-purple-700 disabled:opacity-50">
          {{ saving ? 'Saving...' : 'Save Settings' }}
        </button>
        <span v-if="saved" class="text-green-600 text-sm">Saved!</span>
        <span v-if="restartRequired" class="text-orange-600 text-sm">Restart server to apply changes</span>
        <span v-if="error" class="text-red-500 text-sm">{{ error }}</span>
      </div>
    </form>
  </div>
</template>
