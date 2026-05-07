<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useMemoryStore } from '../stores/memories'
import { useCharacterStore } from '../stores/characters'
import type { Character } from '../stores/characters'

const route = useRoute()
const router = useRouter()
const memoryStore = useMemoryStore()
const charStore = useCharacterStore()

const character = ref<Character | null>(null)
const activeFilter = ref<string>('')
const showConfirmClear = ref(false)

const filteredMemories = computed(() => {
  if (!activeFilter.value) return memoryStore.memories
  return memoryStore.memories.filter((m) => m.type === activeFilter.value)
})

const typeCounts = computed(() => {
  const counts = { fact: 0, feeling: 0, event: 0 }
  memoryStore.memories.forEach((m) => {
    if (m.type in counts) counts[m.type as keyof typeof counts]++
  })
  return counts
})

onMounted(async () => {
  const id = route.params.id as string
  if (charStore.characters.length === 0) await charStore.fetchCharacters()
  character.value = charStore.characters.find((c) => c.id === id) || null
  await memoryStore.fetchMemories(id)
})

function setFilter(type: string) {
  activeFilter.value = activeFilter.value === type ? '' : type
}

async function handleDeleteMemory(id: string) {
  await memoryStore.deleteMemory(id)
}

async function handleClearAll() {
  const id = route.params.id as string
  await memoryStore.clearAllMemories(id)
  showConfirmClear.value = false
}

async function handleExport() {
  const id = route.params.id as string
  const data = await memoryStore.exportMemories(id)
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${character.value?.name || 'memories'}_memories.json`
  a.click()
  URL.revokeObjectURL(url)
}
</script>

<template>
  <div>
    <div class="flex items-center gap-3 mb-6">
      <button @click="router.push('/')" class="text-gray-500 hover:text-gray-700">&larr;</button>
      <h2 class="text-2xl font-bold">Memories: {{ character?.name }}</h2>
    </div>

    <!-- Stats & Actions -->
    <div class="flex flex-wrap items-center gap-3 mb-4">
      <button @click="setFilter('fact')"
        :class="['px-3 py-1 rounded-full text-sm border', activeFilter === 'fact' ? 'bg-blue-100 border-blue-300 text-blue-700' : '']">
        Facts ({{ typeCounts.fact }})
      </button>
      <button @click="setFilter('feeling')"
        :class="['px-3 py-1 rounded-full text-sm border', activeFilter === 'feeling' ? 'bg-yellow-100 border-yellow-300 text-yellow-700' : '']">
        Feelings ({{ typeCounts.feeling }})
      </button>
      <button @click="setFilter('event')"
        :class="['px-3 py-1 rounded-full text-sm border', activeFilter === 'event' ? 'bg-green-100 border-green-300 text-green-700' : '']">
        Events ({{ typeCounts.event }})
      </button>
      <div class="ml-auto flex gap-2">
        <button @click="handleExport" class="text-sm border px-3 py-1 rounded hover:bg-gray-50">Export JSON</button>
        <button @click="showConfirmClear = true"
          class="text-sm text-red-500 border border-red-300 px-3 py-1 rounded hover:bg-red-50">
          Clear All
        </button>
      </div>
    </div>

    <!-- Memory List -->
    <div class="space-y-2">
      <div v-for="memory in filteredMemories" :key="memory.id"
        class="bg-white rounded-lg border p-4 flex items-start gap-3">
        <span :class="[
          'px-2 py-0.5 rounded-full text-xs font-medium',
          memory.type === 'fact' ? 'bg-blue-100 text-blue-700' :
          memory.type === 'feeling' ? 'bg-yellow-100 text-yellow-700' :
          'bg-green-100 text-green-700'
        ]">
          {{ memory.type }}
        </span>
        <div class="flex-1">
          <p class="text-sm">{{ memory.content }}</p>
          <p class="text-xs text-gray-400 mt-1">{{ new Date(memory.created_at).toLocaleString() }}</p>
        </div>
        <button @click="handleDeleteMemory(memory.id)"
          class="text-gray-400 hover:text-red-500 text-sm">&times;</button>
      </div>
    </div>

    <div v-if="filteredMemories.length === 0" class="text-center py-12 text-gray-500">
      {{ memoryStore.memories.length === 0 ? 'No memories yet. Start a conversation!' : 'No memories match this filter.' }}
    </div>

    <!-- Confirm Clear Modal -->
    <div v-if="showConfirmClear" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div class="bg-white rounded-xl p-6 max-w-sm">
        <h3 class="font-bold text-lg mb-2">Clear All Memories?</h3>
        <p class="text-gray-600 text-sm mb-4">This will permanently delete all memories for {{ character?.name }}. This cannot be undone.</p>
        <div class="flex gap-2 justify-end">
          <button @click="showConfirmClear = false" class="px-4 py-2 border rounded-lg hover:bg-gray-50">Cancel</button>
          <button @click="handleClearAll"
            class="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700">Clear All</button>
        </div>
      </div>
    </div>
  </div>
</template>
