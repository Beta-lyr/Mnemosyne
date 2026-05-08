<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useCharacterStore } from '../stores/characters'
import type { Character } from '../stores/characters'

const route = useRoute()
const router = useRouter()
const store = useCharacterStore()

const character = ref<Character | null>(null)
const loading = ref(true)
const saving = ref(false)
const uploading = ref(false)
const showAdvanced = ref(false)
const editForm = ref({
  name: '',
  personality: '',
  system_prompt: '',
  mood_default: 'sweet',
  telegram_token: '',
  gender: '',
  age: '',
  occupation: '',
  mbti: '',
  zodiac: '',
  attachment_style: '',
  core_vulnerability: '',
  tone: '',
  quirks: '',
  emoji_usage: 'mid',
  visual_style: 'photorealistic',
  physical_attributes: '',
  user_free_text: '',
})
const fileInput = ref<HTMLInputElement | null>(null)

const mbtiTypes = [
  'INTJ', 'INTP', 'ENTJ', 'ENTP',
  'INFJ', 'INFP', 'ENFJ', 'ENFP',
  'ISTJ', 'ISFJ', 'ESTJ', 'ESFJ',
  'ISTP', 'ISFP', 'ESTP', 'ESFP',
]

const zodiacSigns = [
  '白羊座', '金牛座', '双子座', '巨蟹座', '狮子座', '处女座',
  '天秤座', '天蝎座', '射手座', '摩羯座', '水瓶座', '双鱼座',
]

onMounted(async () => {
  const id = route.params.id as string
  if (store.characters.length === 0) await store.fetchCharacters()
  character.value = store.characters.find((c) => c.id === id) || null
  if (character.value) {
    editForm.value = {
      name: character.value.name,
      personality: character.value.personality,
      system_prompt: character.value.system_prompt,
      mood_default: character.value.mood_default,
      telegram_token: character.value.telegram_token || '',
      gender: character.value.gender || '',
      age: character.value.age || '',
      occupation: character.value.occupation || '',
      mbti: character.value.mbti || '',
      zodiac: character.value.zodiac || '',
      attachment_style: character.value.attachment_style || '',
      core_vulnerability: character.value.core_vulnerability || '',
      tone: character.value.tone || '',
      quirks: character.value.quirks || '',
      emoji_usage: character.value.emoji_usage || 'mid',
      visual_style: character.value.visual_style || 'photorealistic',
      physical_attributes: character.value.physical_attributes || '',
      user_free_text: '',
    }
    // Show advanced section if any persona fields are filled
    if (character.value.mbti || character.value.attachment_style || character.value.tone || character.value.quirks) {
      showAdvanced.value = true
    }
  }
  loading.value = false
})

async function handleSave() {
  if (!character.value) return
  saving.value = true
  try {
    await store.updateCharacter(character.value.id, editForm.value)
    router.push('/characters')
  } finally {
    saving.value = false
  }
}

async function handleUploadImage(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file || !character.value) return
  uploading.value = true
  try {
    await store.uploadImage(character.value.id, file)
  } finally {
    uploading.value = false
  }
}

async function handleExport(format: string) {
  if (!character.value) return
  const data = await store.exportCard(character.value.id, format)
  const blob = new Blob(
    [typeof data === 'string' ? data : JSON.stringify(data, null, 2)],
    { type: format === 'json' ? 'application/json' : 'text/yaml' }
  )
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${character.value.name}.card.${format}`
  a.click()
  URL.revokeObjectURL(url)
}

</script>

<template>
  <div>
    <!-- Loading skeleton -->
    <div v-if="loading" class="max-w-2xl mx-auto">
      <div class="flex items-center gap-3 mb-8">
        <div class="w-9 h-9 skeleton rounded-xl"></div>
        <div class="space-y-2">
          <div class="h-6 w-40 skeleton"></div>
          <div class="h-4 w-32 skeleton"></div>
        </div>
      </div>
      <div class="card p-6 mb-5">
        <div class="flex items-center gap-5">
          <div class="w-24 h-24 rounded-full skeleton"></div>
          <div class="flex-1 space-y-2">
            <div class="h-5 w-36 skeleton"></div>
            <div class="h-4 w-48 skeleton"></div>
          </div>
        </div>
      </div>
      <div class="card p-6 space-y-5">
        <div v-for="i in 5" :key="i" class="space-y-2">
          <div class="h-4 w-20 skeleton"></div>
          <div class="h-10 w-full skeleton rounded-xl"></div>
        </div>
      </div>
    </div>

    <!-- Not found -->
    <div v-else-if="!character" class="text-center py-20 animate-fade-in">
      <div class="w-20 h-20 mx-auto mb-6 rounded-full bg-red-50 flex items-center justify-center">
        <svg class="w-10 h-10 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
        </svg>
      </div>
      <h3 class="text-xl font-display font-bold text-gray-700 mb-2">Character not found</h3>
      <p class="text-gray-500 mb-6">This character may have been deleted</p>
      <button @click="router.push('/characters')" class="btn-primary">
        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
        </svg>
        Back to Characters
      </button>
    </div>

    <!-- Main content -->
    <div v-else class="max-w-2xl mx-auto animate-fade-in">
      <!-- Header -->
      <div class="flex items-center gap-3 mb-8">
        <button @click="router.push('/characters')" class="btn-ghost p-2 rounded-xl">
          <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
          </svg>
        </button>
        <div>
          <h2 class="text-2xl font-display font-bold text-gray-800">{{ character.name }}</h2>
          <p class="text-sm text-gray-500">Edit character profile</p>
        </div>
      </div>

      <!-- Base Image Upload -->
      <div class="card p-6 mb-5 animate-slide-up">
        <h3 class="font-display font-bold text-gray-800 mb-4 flex items-center gap-2">
          <svg class="w-5 h-5 text-accent" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909M3.75 21h16.5A2.25 2.25 0 0022.5 18.75V5.25A2.25 2.25 0 0020.25 3H3.75A2.25 2.25 0 001.5 5.25v13.5A2.25 2.25 0 003.75 21z" />
          </svg>
          Reference Photo
        </h3>
        <div class="flex items-center gap-5">
          <div class="w-24 h-24 rounded-full bg-gradient-to-br from-accent-100 to-primary-100 flex items-center justify-center overflow-hidden ring-4 ring-white shadow-md">
            <img v-if="character.base_image_url" :src="character.base_image_url" class="w-full h-full object-cover" />
            <svg v-else class="w-10 h-10 text-accent-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" />
            </svg>
          </div>
          <div>
            <input ref="fileInput" type="file" accept="image/*" class="hidden" @change="handleUploadImage" />
            <button @click="fileInput?.click()" :disabled="uploading" class="btn-outline text-sm">
              <svg v-if="!uploading" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
              </svg>
              <svg v-else class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
              </svg>
              {{ uploading ? 'Uploading...' : 'Upload Photo' }}
            </button>
            <p class="text-xs text-gray-400 mt-2">Used as face reference for generated images</p>
          </div>
        </div>
      </div>

      <!-- Edit Form -->
      <form @submit.prevent="handleSave" class="card p-6 space-y-5 animate-slide-up" style="animation-delay: 80ms; animation-fill-mode: backwards;">
        <div>
          <label class="block text-sm font-semibold text-gray-700 mb-1.5">Name</label>
          <input v-model="editForm.name" type="text" required placeholder="Character name" class="input" />
        </div>
        <div>
          <label class="block text-sm font-semibold text-gray-700 mb-1.5">Personality</label>
          <textarea v-model="editForm.personality" rows="5" required
            placeholder="Describe personality, speaking style, quirks, hobbies..."
            class="input resize-none"></textarea>
        </div>
        <div>
          <label class="block text-sm font-semibold text-gray-700 mb-1.5">
            System Prompt
            <span class="text-xs font-normal text-gray-400 ml-1">(advanced)</span>
          </label>
          <textarea v-model="editForm.system_prompt" rows="4"
            placeholder="Override the default system prompt template"
            class="input font-mono text-xs resize-none"></textarea>
        </div>
        <div>
          <label class="block text-sm font-semibold text-gray-700 mb-1.5">Default Mood</label>
          <select v-model="editForm.mood_default" class="input">
            <option value="sweet">Sweet</option>
            <option value="happy">Happy</option>
            <option value="shy">Shy</option>
            <option value="cool">Cool</option>
            <option value="gentle">Gentle</option>
            <option value="energetic">Energetic</option>
          </select>
        </div>
        <div>
          <label class="block text-sm font-semibold text-gray-700 mb-1.5">
            Telegram Bot Token
            <span class="text-xs font-normal text-gray-400 ml-1">(optional)</span>
          </label>
          <input v-model="editForm.telegram_token" type="text" placeholder="123456:ABC-DEF..." class="input" />
        </div>

        <!-- Advanced Persona Settings -->
        <button type="button" @click="showAdvanced = !showAdvanced"
          class="flex items-center gap-2 text-sm font-semibold text-accent hover:text-accent-600 transition-colors">
          <svg class="w-4 h-4 transition-transform" :class="{ 'rotate-90': showAdvanced }" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" />
          </svg>
          Advanced Persona Settings
          <span v-if="character.processed_personality" class="badge bg-green-100 text-green-700 text-xs">Compiled</span>
        </button>

        <div v-if="showAdvanced" class="space-y-4 pt-1 pb-1">
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-semibold text-gray-700 mb-1.5">Gender</label>
              <input v-model="editForm.gender" type="text" placeholder="e.g. female" class="input" />
            </div>
            <div>
              <label class="block text-sm font-semibold text-gray-700 mb-1.5">Age</label>
              <input v-model="editForm.age" type="text" placeholder="e.g. 22" class="input" />
            </div>
          </div>
          <div>
            <label class="block text-sm font-semibold text-gray-700 mb-1.5">Occupation</label>
            <input v-model="editForm.occupation" type="text" placeholder="e.g. university student" class="input" />
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-semibold text-gray-700 mb-1.5">MBTI</label>
              <select v-model="editForm.mbti" class="input">
                <option value="">Not set</option>
                <option v-for="t in mbtiTypes" :key="t" :value="t">{{ t }}</option>
              </select>
            </div>
            <div>
              <label class="block text-sm font-semibold text-gray-700 mb-1.5">Zodiac</label>
              <select v-model="editForm.zodiac" class="input">
                <option value="">Not set</option>
                <option v-for="z in zodiacSigns" :key="z" :value="z">{{ z }}</option>
              </select>
            </div>
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-semibold text-gray-700 mb-1.5">Attachment Style</label>
              <select v-model="editForm.attachment_style" class="input">
                <option value="">Not set</option>
                <option value="secure">Secure</option>
                <option value="anxious">Anxious</option>
                <option value="avoidant">Avoidant</option>
                <option value="disorganized">Disorganized</option>
              </select>
            </div>
            <div>
              <label class="block text-sm font-semibold text-gray-700 mb-1.5">Tone</label>
              <input v-model="editForm.tone" type="text" placeholder="e.g. warm, playful" class="input" />
            </div>
          </div>
          <div>
            <label class="block text-sm font-semibold text-gray-700 mb-1.5">Core Vulnerability</label>
            <input v-model="editForm.core_vulnerability" type="text" placeholder="e.g. fears abandonment" class="input" />
          </div>
          <div>
            <label class="block text-sm font-semibold text-gray-700 mb-1.5">Quirks</label>
            <textarea v-model="editForm.quirks" rows="2" placeholder="e.g. snorts when laughing, always cold" class="input resize-none"></textarea>
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-semibold text-gray-700 mb-1.5">Emoji Usage</label>
              <select v-model="editForm.emoji_usage" class="input">
                <option value="none">None</option>
                <option value="low">Low</option>
                <option value="mid">Medium</option>
                <option value="high">High</option>
              </select>
            </div>
            <div>
              <label class="block text-sm font-semibold text-gray-700 mb-1.5">Visual Style</label>
              <select v-model="editForm.visual_style" class="input">
                <option value="photorealistic">Photorealistic</option>
                <option value="anime">Anime</option>
                <option value="oil_painting">Oil Painting</option>
                <option value="watercolor">Watercolor</option>
                <option value="pixel_art">Pixel Art</option>
                <option value="3d_render">3D Render</option>
              </select>
            </div>
          </div>
          <div>
            <label class="block text-sm font-semibold text-gray-700 mb-1.5">Physical Attributes</label>
            <textarea v-model="editForm.physical_attributes" rows="2" placeholder="e.g. long black hair, brown eyes, petite" class="input resize-none"></textarea>
          </div>
          <div>
            <label class="block text-sm font-semibold text-gray-700 mb-1.5">
              Free-form Description
              <span class="text-xs font-normal text-gray-400 ml-1">Re-compile persona from natural language</span>
            </label>
            <textarea v-model="editForm.user_free_text" rows="3"
              placeholder="Describe your character in natural language — will re-compile the AI persona"
              class="input resize-none"></textarea>
          </div>
        </div>

        <div class="flex gap-2 justify-end pt-2">
          <button type="button" @click="router.push('/characters')" class="btn-secondary">Cancel</button>
          <button type="submit" :disabled="saving" class="btn-primary">
            <svg v-if="saving" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
            </svg>
            <svg v-else class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5" />
            </svg>
            {{ saving ? 'Saving...' : 'Save Changes' }}
          </button>
        </div>
      </form>

      <!-- Export Card -->
      <div class="card p-6 mt-5 animate-slide-up" style="animation-delay: 160ms; animation-fill-mode: backwards;">
        <h3 class="font-display font-bold text-gray-800 mb-1 flex items-center gap-2">
          <svg class="w-5 h-5 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
          </svg>
          Export Character Card
        </h3>
        <p class="text-sm text-gray-500 mb-4">Share this character's settings as a card file</p>
        <div class="flex gap-2">
          <button @click="handleExport('yaml')" class="btn-outline text-sm">
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
            </svg>
            YAML
          </button>
          <button @click="handleExport('json')" class="btn-outline text-sm">
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M17.25 6.75L22.5 12l-5.25 5.25m-10.5 0L1.5 12l5.25-5.25m7.5-3l-4.5 16.5" />
            </svg>
            JSON
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
