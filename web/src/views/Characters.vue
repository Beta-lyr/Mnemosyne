<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useCharacterStore } from '../stores/characters'
import type { CharacterCreate } from '../stores/characters'

const router = useRouter()
const store = useCharacterStore()

const showCreate = ref(false)
const showImport = ref(false)
const form = ref<CharacterCreate>({
  name: '',
  personality: '',
  mood_default: 'sweet',
  voice_style: {},
})
const importText = ref('')
const importError = ref('')

onMounted(() => store.fetchCharacters())

async function handleCreate() {
  if (!form.value.name || !form.value.personality) return
  const char = await store.createCharacter(form.value)
  showCreate.value = false
  form.value = { name: '', personality: '', mood_default: 'sweet', voice_style: {} }
  router.push(`/characters/${char.id}`)
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

async function handleDelete(id: string, name: string) {
  if (confirm(`Delete "${name}"? This will remove all memories and conversations.`)) {
    await store.deleteCharacter(id)
  }
}
</script>

<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <h2 class="text-2xl font-bold">Characters</h2>
      <div class="flex gap-2">
        <button @click="showImport = true"
          class="border border-purple-600 text-purple-600 px-4 py-2 rounded-lg hover:bg-purple-50">
          Import Card
        </button>
        <button @click="showCreate = true"
          class="bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-700">
          + Create Character
        </button>
      </div>
    </div>

    <!-- Character List -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <div v-for="char in store.characters" :key="char.id"
        class="bg-white rounded-xl shadow-sm border p-4">
        <div class="flex items-center gap-3 mb-3">
          <div class="w-14 h-14 rounded-full bg-purple-100 flex items-center justify-center overflow-hidden">
            <img v-if="char.base_image_url" :src="char.base_image_url" class="w-full h-full object-cover" />
            <span v-else class="text-purple-600 text-xl font-bold">{{ char.name[0] }}</span>
          </div>
          <div class="flex-1">
            <h3 class="font-semibold text-lg">{{ char.name }}</h3>
            <p class="text-xs text-gray-400">Created: {{ new Date(char.created_at).toLocaleDateString() }}</p>
          </div>
        </div>
        <p class="text-sm text-gray-600 line-clamp-3 mb-4">{{ char.personality }}</p>
        <div class="flex gap-2 flex-wrap">
          <button @click="router.push(`/chat/${char.id}`)"
            class="text-sm bg-purple-600 text-white px-3 py-1 rounded hover:bg-purple-700">Chat</button>
          <button @click="router.push(`/characters/${char.id}`)"
            class="text-sm border px-3 py-1 rounded hover:bg-gray-50">Edit</button>
          <button @click="router.push(`/memories/${char.id}`)"
            class="text-sm border px-3 py-1 rounded hover:bg-gray-50">Memories</button>
          <button @click="handleDelete(char.id, char.name)"
            class="text-sm text-red-500 border border-red-300 px-3 py-1 rounded hover:bg-red-50">Delete</button>
        </div>
      </div>
    </div>

    <div v-if="store.characters.length === 0 && !store.loading"
      class="text-center py-16 text-gray-500">
      No characters yet. Create your first companion!
    </div>

    <!-- Create Modal -->
    <div v-if="showCreate" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div class="bg-white rounded-xl p-6 w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <h3 class="text-xl font-bold mb-4">Create Character</h3>
        <form @submit.prevent="handleCreate" class="space-y-4">
          <div>
            <label class="block text-sm font-medium mb-1">Name *</label>
            <input v-model="form.name" type="text" required
              class="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-purple-500 focus:outline-none" />
          </div>
          <div>
            <label class="block text-sm font-medium mb-1">Personality *</label>
            <textarea v-model="form.personality" rows="5" required
              placeholder="Describe the character's personality, speaking style, quirks..."
              class="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-purple-500 focus:outline-none"></textarea>
          </div>
          <div>
            <label class="block text-sm font-medium mb-1">Default Mood</label>
            <select v-model="form.mood_default"
              class="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-purple-500 focus:outline-none">
              <option value="sweet">Sweet</option>
              <option value="happy">Happy</option>
              <option value="shy">Shy</option>
              <option value="cool">Cool</option>
              <option value="gentle">Gentle</option>
              <option value="energetic">Energetic</option>
            </select>
          </div>
          <div class="flex gap-2 justify-end">
            <button type="button" @click="showCreate = false"
              class="px-4 py-2 border rounded-lg hover:bg-gray-50">Cancel</button>
            <button type="submit"
              class="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700">Create</button>
          </div>
        </form>
      </div>
    </div>

    <!-- Import Modal -->
    <div v-if="showImport" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div class="bg-white rounded-xl p-6 w-full max-w-lg">
        <h3 class="text-xl font-bold mb-4">Import Character Card</h3>
        <textarea v-model="importText" rows="10" placeholder="Paste JSON character card here..."
          class="w-full border rounded-lg px-3 py-2 font-mono text-sm focus:ring-2 focus:ring-purple-500 focus:outline-none"></textarea>
        <p v-if="importError" class="text-red-500 text-sm mt-2">{{ importError }}</p>
        <div class="flex gap-2 justify-end mt-4">
          <button @click="showImport = false" class="px-4 py-2 border rounded-lg hover:bg-gray-50">Cancel</button>
          <button @click="handleImport"
            class="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700">Import</button>
        </div>
      </div>
    </div>
  </div>
</template>
