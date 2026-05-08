<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useCharacterStore } from '../stores/characters'
import type { CharacterCreate } from '../stores/characters'

const router = useRouter()
const store = useCharacterStore()

const showCreate = ref(false)
const showImport = ref(false)
const showAdvanced = ref(false)
const compiling = ref(false)
const showDelete = ref(false)
const deleteTarget = ref<{ id: string; name: string } | null>(null)
const form = ref<CharacterCreate>({
  name: '',
  personality: '',
  mood_default: 'sweet',
  voice_style: {},
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
const importText = ref('')
const importError = ref('')

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

onMounted(() => store.fetchCharacters())

async function handleCreate() {
  if (!form.value.name || !form.value.personality) return
  compiling.value = true
  try {
    const char = await store.createCharacter(form.value)
    showCreate.value = false
    form.value = { name: '', personality: '', mood_default: 'sweet', voice_style: {} }
    router.push(`/characters/${char.id}`)
  } finally {
    compiling.value = false
  }
}

async function handleImport() {
  importError.value = ''
  try {
    const card = JSON.parse(importText.value)
    const result = await store.importCard(card)
    showImport.value = false
    importText.value = ''
    router.push(`/characters/${result.id}`)
  } catch (e: any) {
    importError.value = 'Invalid JSON format: ' + e.message
  }
}

function promptDelete(id: string, name: string) {
  deleteTarget.value = { id, name }
  showDelete.value = true
}

async function confirmDelete() {
  if (!deleteTarget.value) return
  await store.deleteCharacter(deleteTarget.value.id)
  showDelete.value = false
  deleteTarget.value = null
}

const moodColors: Record<string, string> = {
  sweet: 'bg-pink-100 text-pink-700',
  happy: 'bg-yellow-100 text-yellow-700',
  shy: 'bg-blue-100 text-blue-700',
  cool: 'bg-gray-100 text-gray-700',
  gentle: 'bg-green-100 text-green-700',
  energetic: 'bg-orange-100 text-orange-700',
}
</script>

<template>
  <div>
    <!-- Header -->
    <div class="flex items-center justify-between mb-8">
      <div>
        <h2 class="text-2xl font-display font-bold text-gray-800">Characters</h2>
        <p class="text-sm text-gray-500 mt-1">Manage your virtual companions</p>
      </div>
      <div class="flex gap-2">
        <button @click="showImport = true" class="btn-outline text-sm">
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
          </svg>
          Import
        </button>
        <button @click="showCreate = true" class="btn-primary text-sm">
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          Create
        </button>
      </div>
    </div>

    <!-- Loading skeleton -->
    <div v-if="store.loading" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
      <div v-for="i in 3" :key="i" class="card p-5">
        <div class="flex items-center gap-3 mb-4">
          <div class="w-14 h-14 rounded-full skeleton"></div>
          <div class="flex-1 space-y-2">
            <div class="h-5 w-24 skeleton"></div>
            <div class="h-3 w-16 skeleton"></div>
          </div>
        </div>
        <div class="space-y-2 mb-4">
          <div class="h-4 w-full skeleton"></div>
          <div class="h-4 w-3/4 skeleton"></div>
        </div>
        <div class="flex gap-2">
          <div class="h-8 w-16 skeleton rounded-lg"></div>
          <div class="h-8 w-16 skeleton rounded-lg"></div>
          <div class="h-8 w-16 skeleton rounded-lg"></div>
        </div>
      </div>
    </div>

    <!-- Character grid -->
    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
      <div v-for="(char, index) in store.characters" :key="char.id"
        class="card p-5 cursor-pointer group animate-slide-up"
        :style="{ animationDelay: `${index * 80}ms`, animationFillMode: 'backwards' }"
        @click="router.push(`/chat/${char.id}`)">

        <div class="flex items-center gap-3 mb-4">
          <div class="w-14 h-14 rounded-full bg-gradient-to-br from-accent-100 to-primary-100 flex items-center justify-center overflow-hidden ring-2 ring-white shadow-sm group-hover:ring-accent-200 transition-all">
            <img v-if="char.base_image_url" :src="char.base_image_url" class="w-full h-full object-cover" />
            <span v-else class="text-accent text-xl font-display font-bold">{{ char.name[0] }}</span>
          </div>
          <div class="flex-1 min-w-0">
            <h3 class="font-display font-bold text-gray-800 truncate">{{ char.name }}</h3>
            <span class="badge text-xs mt-1" :class="moodColors[char.mood_default] || 'bg-gray-100 text-gray-600'">
              {{ char.mood_default }}
            </span>
          </div>
        </div>

        <p class="text-sm text-gray-500 line-clamp-2 mb-4 leading-relaxed">{{ char.personality }}</p>

        <div class="flex gap-2 border-t border-gray-100 pt-3" @click.stop>
          <button @click="router.push(`/chat/${char.id}`)" class="btn-primary text-xs flex-1 py-2">
            <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
            Chat
          </button>
          <button @click="router.push(`/memories/${char.id}`)" class="btn-secondary text-xs py-2">
            Memories
          </button>
          <button @click="router.push(`/characters/${char.id}`)" class="btn-ghost text-xs py-2">
            <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
            </svg>
          </button>
          <button @click="promptDelete(char.id, char.name)" class="btn-ghost text-xs py-2 text-gray-400 hover:text-red-500">
            <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
        </div>
      </div>
    </div>

    <!-- Empty state -->
    <div v-if="store.characters.length === 0 && !store.loading"
      class="text-center py-20 animate-fade-in">
      <div class="w-20 h-20 mx-auto mb-6 rounded-full bg-gradient-to-br from-primary-100 to-accent-100 flex items-center justify-center">
        <svg class="w-10 h-10 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M18 18.72a9.094 9.094 0 003.741-.479 3 3 0 00-4.682-2.72m.94 3.198l.001.031c0 .225-.012.447-.037.666A11.944 11.944 0 0112 21c-2.17 0-4.207-.576-5.963-1.584A6.062 6.062 0 016 18.719m12 0a5.971 5.971 0 00-.941-3.197m0 0A5.995 5.995 0 0012 12.75a5.995 5.995 0 00-5.058 2.772m0 0a3 3 0 00-4.681 2.72 8.986 8.986 0 003.74.477m.94-3.197a5.971 5.971 0 00-.94 3.197M15 6.75a3 3 0 11-6 0 3 3 0 016 0zm6 3a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0zm-13.5 0a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0z" />
        </svg>
      </div>
      <h3 class="text-xl font-display font-bold text-gray-700 mb-2">No companions yet</h3>
      <p class="text-gray-500 mb-6">Create your first virtual companion to get started</p>
      <button @click="showCreate = true" class="btn-primary">
        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
        </svg>
        Create Your First Companion
      </button>
    </div>

    <!-- Create Modal -->
    <Teleport to="body">
      <transition
        enter-active-class="transition duration-200 ease-out"
        enter-from-class="opacity-0"
        enter-to-class="opacity-100"
        leave-active-class="transition duration-150 ease-in"
        leave-from-class="opacity-100"
        leave-to-class="opacity-0"
      >
        <div v-if="showCreate" class="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50 p-4" @click.self="showCreate = false">
          <div class="bg-white rounded-2xl shadow-modal p-6 w-full max-w-lg animate-slide-up">
            <h3 class="text-xl font-display font-bold text-gray-800 mb-1">Create Character</h3>
            <p class="text-sm text-gray-500 mb-5">Design your virtual companion</p>
            <form @submit.prevent="handleCreate" class="space-y-4">
              <div>
                <label class="block text-sm font-semibold text-gray-700 mb-1.5">Name *</label>
                <input v-model="form.name" type="text" required placeholder="e.g. Xiaoyu" class="input" />
              </div>
              <div>
                <label class="block text-sm font-semibold text-gray-700 mb-1.5">Personality *</label>
                <textarea v-model="form.personality" rows="5" required
                  placeholder="Describe the character's personality, speaking style, quirks, hobbies..."
                  class="input resize-none"></textarea>
              </div>
              <div>
                <label class="block text-sm font-semibold text-gray-700 mb-1.5">Default Mood</label>
                <select v-model="form.mood_default" class="input">
                  <option value="sweet">Sweet</option>
                  <option value="happy">Happy</option>
                  <option value="shy">Shy</option>
                  <option value="cool">Cool</option>
                  <option value="gentle">Gentle</option>
                  <option value="energetic">Energetic</option>
                </select>
              </div>

              <!-- Advanced toggle -->
              <button type="button" @click="showAdvanced = !showAdvanced"
                class="flex items-center gap-2 text-sm font-semibold text-accent hover:text-accent-600 transition-colors">
                <svg class="w-4 h-4 transition-transform" :class="{ 'rotate-90': showAdvanced }" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" />
                </svg>
                Advanced Persona Settings
              </button>

              <div v-if="showAdvanced" class="space-y-4 pt-1 pb-1">
                <div class="grid grid-cols-2 gap-4">
                  <div>
                    <label class="block text-sm font-semibold text-gray-700 mb-1.5">Gender</label>
                    <input v-model="form.gender" type="text" placeholder="e.g. female" class="input" />
                  </div>
                  <div>
                    <label class="block text-sm font-semibold text-gray-700 mb-1.5">Age</label>
                    <input v-model="form.age" type="text" placeholder="e.g. 22" class="input" />
                  </div>
                </div>
                <div>
                  <label class="block text-sm font-semibold text-gray-700 mb-1.5">Occupation</label>
                  <input v-model="form.occupation" type="text" placeholder="e.g. university student" class="input" />
                </div>
                <div class="grid grid-cols-2 gap-4">
                  <div>
                    <label class="block text-sm font-semibold text-gray-700 mb-1.5">MBTI</label>
                    <select v-model="form.mbti" class="input">
                      <option value="">Not set</option>
                      <option v-for="t in mbtiTypes" :key="t" :value="t">{{ t }}</option>
                    </select>
                  </div>
                  <div>
                    <label class="block text-sm font-semibold text-gray-700 mb-1.5">Zodiac</label>
                    <select v-model="form.zodiac" class="input">
                      <option value="">Not set</option>
                      <option v-for="z in zodiacSigns" :key="z" :value="z">{{ z }}</option>
                    </select>
                  </div>
                </div>
                <div class="grid grid-cols-2 gap-4">
                  <div>
                    <label class="block text-sm font-semibold text-gray-700 mb-1.5">Attachment Style</label>
                    <select v-model="form.attachment_style" class="input">
                      <option value="">Not set</option>
                      <option value="secure">Secure</option>
                      <option value="anxious">Anxious</option>
                      <option value="avoidant">Avoidant</option>
                      <option value="disorganized">Disorganized</option>
                    </select>
                  </div>
                  <div>
                    <label class="block text-sm font-semibold text-gray-700 mb-1.5">Tone</label>
                    <input v-model="form.tone" type="text" placeholder="e.g. warm, playful" class="input" />
                  </div>
                </div>
                <div>
                  <label class="block text-sm font-semibold text-gray-700 mb-1.5">Core Vulnerability</label>
                  <input v-model="form.core_vulnerability" type="text" placeholder="e.g. fears abandonment" class="input" />
                </div>
                <div>
                  <label class="block text-sm font-semibold text-gray-700 mb-1.5">Quirks</label>
                  <textarea v-model="form.quirks" rows="2" placeholder="e.g. snorts when laughing, always cold" class="input resize-none"></textarea>
                </div>
                <div class="grid grid-cols-2 gap-4">
                  <div>
                    <label class="block text-sm font-semibold text-gray-700 mb-1.5">Emoji Usage</label>
                    <select v-model="form.emoji_usage" class="input">
                      <option value="none">None</option>
                      <option value="low">Low</option>
                      <option value="mid">Medium</option>
                      <option value="high">High</option>
                    </select>
                  </div>
                  <div>
                    <label class="block text-sm font-semibold text-gray-700 mb-1.5">Visual Style</label>
                    <select v-model="form.visual_style" class="input">
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
                  <textarea v-model="form.physical_attributes" rows="2" placeholder="e.g. long black hair, brown eyes, petite" class="input resize-none"></textarea>
                </div>
                <div>
                  <label class="block text-sm font-semibold text-gray-700 mb-1.5">
                    Free-form Description
                    <span class="text-xs font-normal text-gray-400 ml-1">AI will compile this into a deep persona</span>
                  </label>
                  <textarea v-model="form.user_free_text" rows="3"
                    placeholder="Describe your character in natural language — personality, backstory, relationship dynamics, anything..."
                    class="input resize-none"></textarea>
                </div>
              </div>

              <div class="flex gap-2 justify-end pt-2">
                <button type="button" @click="showCreate = false" class="btn-secondary">Cancel</button>
                <button type="submit" :disabled="compiling" class="btn-primary">
                  <svg v-if="compiling" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
                  </svg>
                  {{ compiling ? 'Compiling...' : 'Create' }}
                </button>
              </div>
            </form>
          </div>
        </div>
      </transition>
    </Teleport>

    <!-- Import Modal -->
    <Teleport to="body">
      <transition
        enter-active-class="transition duration-200 ease-out"
        enter-from-class="opacity-0"
        enter-to-class="opacity-100"
        leave-active-class="transition duration-150 ease-in"
        leave-from-class="opacity-100"
        leave-to-class="opacity-0"
      >
        <div v-if="showImport" class="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50 p-4" @click.self="showImport = false">
          <div class="bg-white rounded-2xl shadow-modal p-6 w-full max-w-lg animate-slide-up">
            <h3 class="text-xl font-display font-bold text-gray-800 mb-1">Import Character Card</h3>
            <p class="text-sm text-gray-500 mb-4">Paste a JSON character card to import</p>
            <textarea v-model="importText" rows="10" placeholder='{"name": "...", "personality": "...", ...}'
              class="input font-mono text-xs resize-none"></textarea>
            <p v-if="importError" class="text-red-500 text-sm mt-2 flex items-center gap-1">
              <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              {{ importError }}
            </p>
            <div class="flex gap-2 justify-end mt-4">
              <button @click="showImport = false" class="btn-secondary">Cancel</button>
              <button @click="handleImport" class="btn-primary">Import</button>
            </div>
          </div>
        </div>
      </transition>
    </Teleport>

    <!-- Delete Confirmation Modal -->
    <Teleport to="body">
      <transition
        enter-active-class="transition duration-200 ease-out"
        enter-from-class="opacity-0"
        enter-to-class="opacity-100"
        leave-active-class="transition duration-150 ease-in"
        leave-from-class="opacity-100"
        leave-to-class="opacity-0"
      >
        <div v-if="showDelete" class="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50 p-4" @click.self="showDelete = false">
          <div class="bg-white rounded-2xl shadow-modal p-6 w-full max-w-sm animate-slide-up">
            <div class="w-12 h-12 mx-auto mb-4 rounded-full bg-red-50 flex items-center justify-center">
              <svg class="w-6 h-6 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </div>
            <h3 class="text-lg font-display font-bold text-gray-800 text-center mb-1">Delete Character</h3>
            <p class="text-sm text-gray-500 text-center mb-5">
              Are you sure you want to delete <span class="font-semibold text-gray-700">"{{ deleteTarget?.name }}"</span>?
              This will remove all memories and conversations.
            </p>
            <div class="flex gap-2 justify-end">
              <button @click="showDelete = false" class="btn-secondary">Cancel</button>
              <button @click="confirmDelete" class="bg-red-500 hover:bg-red-600 text-white font-semibold px-4 py-2 rounded-xl text-sm transition-colors">
                Delete
              </button>
            </div>
          </div>
        </div>
      </transition>
    </Teleport>
  </div>
</template>
