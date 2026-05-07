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
const editForm = ref({
  name: '',
  personality: '',
  system_prompt: '',
  mood_default: 'sweet',
  telegram_token: '',
})
const fileInput = ref<HTMLInputElement | null>(null)

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
  <div v-if="loading" class="text-center py-12 text-gray-500">Loading...</div>
  <div v-else-if="!character" class="text-center py-12 text-red-500">Character not found</div>
  <div v-else class="max-w-2xl mx-auto">
    <div class="flex items-center gap-3 mb-6">
      <button @click="router.push('/characters')" class="text-gray-500 hover:text-gray-700">&larr; Back</button>
      <h2 class="text-2xl font-bold">Edit: {{ character.name }}</h2>
    </div>

    <!-- Base Image Upload -->
    <div class="bg-white rounded-xl border p-6 mb-4">
      <h3 class="font-semibold mb-3">Base Image (Reference Photo)</h3>
      <div class="flex items-center gap-4">
        <div class="w-24 h-24 rounded-full bg-purple-100 flex items-center justify-center overflow-hidden">
          <img v-if="character.base_image_url" :src="character.base_image_url" class="w-full h-full object-cover" />
          <span v-else class="text-gray-400 text-sm">No image</span>
        </div>
        <div>
          <input ref="fileInput" type="file" accept="image/*" class="hidden" @change="handleUploadImage" />
          <button @click="fileInput?.click()" :disabled="uploading"
            class="border px-4 py-2 rounded-lg hover:bg-gray-50 disabled:opacity-50">
            {{ uploading ? 'Uploading...' : 'Upload Photo' }}
          </button>
          <p class="text-xs text-gray-400 mt-1">This photo will be used as the face reference for all generated images.</p>
        </div>
      </div>
    </div>

    <!-- Edit Form -->
    <form @submit.prevent="handleSave" class="bg-white rounded-xl border p-6 space-y-4">
      <div>
        <label class="block text-sm font-medium mb-1">Name</label>
        <input v-model="editForm.name" type="text" required
          class="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-purple-500 focus:outline-none" />
      </div>
      <div>
        <label class="block text-sm font-medium mb-1">Personality</label>
        <textarea v-model="editForm.personality" rows="5" required
          class="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-purple-500 focus:outline-none"></textarea>
      </div>
      <div>
        <label class="block text-sm font-medium mb-1">System Prompt</label>
        <textarea v-model="editForm.system_prompt" rows="4"
          placeholder="Advanced: override the system prompt template"
          class="w-full border rounded-lg px-3 py-2 font-mono text-sm focus:ring-2 focus:ring-purple-500 focus:outline-none"></textarea>
      </div>
      <div>
        <label class="block text-sm font-medium mb-1">Default Mood</label>
        <select v-model="editForm.mood_default"
          class="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-purple-500 focus:outline-none">
          <option value="sweet">Sweet</option>
          <option value="happy">Happy</option>
          <option value="shy">Shy</option>
          <option value="cool">Cool</option>
          <option value="gentle">Gentle</option>
          <option value="energetic">Energetic</option>
        </select>
      </div>
      <div>
        <label class="block text-sm font-medium mb-1">Telegram Bot Token (optional)</label>
        <input v-model="editForm.telegram_token" type="text"
          placeholder="123456:ABC-DEF..."
          class="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-purple-500 focus:outline-none" />
      </div>
      <div class="flex gap-2 justify-end">
        <button type="button" @click="router.push('/characters')"
          class="px-4 py-2 border rounded-lg hover:bg-gray-50">Cancel</button>
        <button type="submit" :disabled="saving"
          class="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50">
          {{ saving ? 'Saving...' : 'Save Changes' }}
        </button>
      </div>
    </form>

    <!-- Export Card -->
    <div class="bg-white rounded-xl border p-6 mt-4">
      <h3 class="font-semibold mb-3">Export Character Card</h3>
      <p class="text-sm text-gray-500 mb-3">Export this character's settings as a shareable card file.</p>
      <div class="flex gap-2">
        <button @click="handleExport('yaml')" class="border px-4 py-2 rounded-lg hover:bg-gray-50">Export YAML</button>
        <button @click="handleExport('json')" class="border px-4 py-2 rounded-lg hover:bg-gray-50">Export JSON</button>
      </div>
    </div>
  </div>
</template>
