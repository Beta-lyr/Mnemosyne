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
const loading = ref(true)

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
  loading.value = false
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

const typeIcons: Record<string, string> = {
  fact: 'M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25',
  feeling: 'M15.182 15.182a4.5 4.5 0 01-6.364 0M21 12a9 9 0 11-18 0 9 9 0 0118 0zM9.75 9.75c0 .414-.168.75-.375.75S9 10.164 9 9.75 9.168 9 9.375 9s.375.336.375.75zm-.375 0h.008v.015h-.008V9.75zm5.625 0c0 .414-.168.75-.375.75s-.375-.336-.375-.75.168-.75.375-.75.375.336.375.75zm-.375 0h.008v.015h-.008V9.75z',
  event: 'M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 012.25-2.25h13.5A2.25 2.25 0 0121 7.5v11.25m-18 0A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75m-18 0v-7.5A2.25 2.25 0 015.25 9h13.5A2.25 2.25 0 0121 11.25v7.5',
}

const typeColors: Record<string, string> = {
  fact: 'bg-blue-100 text-blue-700 border-blue-200',
  feeling: 'bg-amber-100 text-amber-700 border-amber-200',
  event: 'bg-emerald-100 text-emerald-700 border-emerald-200',
}

const typeActiveColors: Record<string, string> = {
  fact: 'bg-blue-500 text-white border-blue-500 shadow-sm',
  feeling: 'bg-amber-500 text-white border-amber-500 shadow-sm',
  event: 'bg-emerald-500 text-white border-emerald-500 shadow-sm',
}
</script>

<template>
  <div>
    <!-- Header -->
    <div class="flex items-center gap-3 mb-8">
      <button @click="router.push('/')" class="btn-ghost p-2 rounded-xl">
        <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
        </svg>
      </button>
      <div>
        <h2 class="text-2xl font-display font-bold text-gray-800">Memories</h2>
        <p class="text-sm text-gray-500">{{ character?.name }}'s long-term memory</p>
      </div>
    </div>

    <!-- Loading skeleton -->
    <div v-if="loading" class="space-y-4">
      <div class="flex gap-3">
        <div class="h-9 w-24 skeleton rounded-full"></div>
        <div class="h-9 w-28 skeleton rounded-full"></div>
        <div class="h-9 w-24 skeleton rounded-full"></div>
      </div>
      <div v-for="i in 4" :key="i" class="card p-4">
        <div class="flex items-start gap-3">
          <div class="h-6 w-16 skeleton rounded-full"></div>
          <div class="flex-1 space-y-2">
            <div class="h-4 w-full skeleton"></div>
            <div class="h-3 w-32 skeleton"></div>
          </div>
        </div>
      </div>
    </div>

    <div v-else class="animate-fade-in">
      <!-- Stats & Actions -->
      <div class="flex flex-wrap items-center gap-2 mb-6">
        <button @click="setFilter('fact')"
          class="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-full text-sm font-medium border transition-all duration-200"
          :class="activeFilter === 'fact' ? typeActiveColors.fact : typeColors.fact">
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" :d="typeIcons.fact" />
          </svg>
          Facts ({{ typeCounts.fact }})
        </button>
        <button @click="setFilter('feeling')"
          class="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-full text-sm font-medium border transition-all duration-200"
          :class="activeFilter === 'feeling' ? typeActiveColors.feeling : typeColors.feeling">
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" :d="typeIcons.feeling" />
          </svg>
          Feelings ({{ typeCounts.feeling }})
        </button>
        <button @click="setFilter('event')"
          class="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-full text-sm font-medium border transition-all duration-200"
          :class="activeFilter === 'event' ? typeActiveColors.event : typeColors.event">
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" :d="typeIcons.event" />
          </svg>
          Events ({{ typeCounts.event }})
        </button>
        <div class="ml-auto flex gap-2">
          <button @click="handleExport" class="btn-outline text-sm py-2">
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
            </svg>
            Export
          </button>
          <button @click="showConfirmClear = true" class="btn-ghost text-sm py-2 text-red-400 hover:text-red-500 hover:bg-red-50">
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
            </svg>
            Clear All
          </button>
        </div>
      </div>

      <!-- Memory List -->
      <div class="space-y-3">
        <div v-for="(memory, index) in filteredMemories" :key="memory.id"
          class="card p-4 flex items-start gap-3 animate-slide-up"
          :style="{ animationDelay: `${index * 40}ms`, animationFillMode: 'backwards' }">
          <span class="badge text-xs mt-0.5" :class="typeColors[memory.type] || 'bg-gray-100 text-gray-600'">
            {{ memory.type }}
          </span>
          <div class="flex-1 min-w-0">
            <p class="text-sm text-gray-700 leading-relaxed">{{ memory.content }}</p>
            <p class="text-xs text-gray-400 mt-1.5 flex items-center gap-1">
              <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              {{ new Date(memory.created_at).toLocaleString() }}
            </p>
          </div>
          <button @click="handleDeleteMemory(memory.id)"
            class="btn-ghost p-1.5 text-gray-400 hover:text-red-500 rounded-lg shrink-0">
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>

      <!-- Empty state -->
      <div v-if="filteredMemories.length === 0" class="text-center py-16 animate-fade-in">
        <div class="w-16 h-16 mx-auto mb-4 rounded-full bg-gradient-to-br from-primary-100 to-accent-100 flex items-center justify-center">
          <svg class="w-8 h-8 text-primary-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 18v-5.25m0 0a6.01 6.01 0 001.5-.189m-1.5.189a6.01 6.01 0 01-1.5-.189m3.75 7.478a12.06 12.06 0 01-4.5 0m3.75 2.383a14.406 14.406 0 01-3 0M14.25 18v-.192c0-.983.658-1.823 1.508-2.316a7.5 7.5 0 10-7.517 0c.85.493 1.509 1.333 1.509 2.316V18" />
          </svg>
        </div>
        <h3 class="text-lg font-display font-bold text-gray-700 mb-1">
          {{ memoryStore.memories.length === 0 ? 'No memories yet' : 'No memories match this filter' }}
        </h3>
        <p class="text-sm text-gray-500">
          {{ memoryStore.memories.length === 0 ? 'Start a conversation to build memories!' : 'Try selecting a different memory type' }}
        </p>
      </div>
    </div>

    <!-- Confirm Clear Modal -->
    <Teleport to="body">
      <transition
        enter-active-class="transition duration-200 ease-out"
        enter-from-class="opacity-0"
        enter-to-class="opacity-100"
        leave-active-class="transition duration-150 ease-in"
        leave-from-class="opacity-100"
        leave-to-class="opacity-0"
      >
        <div v-if="showConfirmClear" class="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50 p-4" @click.self="showConfirmClear = false">
          <div class="bg-white rounded-2xl shadow-modal p-6 w-full max-w-sm animate-slide-up">
            <div class="w-12 h-12 mx-auto mb-4 rounded-full bg-red-50 flex items-center justify-center">
              <svg class="w-6 h-6 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
              </svg>
            </div>
            <h3 class="text-lg font-display font-bold text-gray-800 text-center mb-1">Clear All Memories?</h3>
            <p class="text-sm text-gray-500 text-center mb-5">
              This will permanently delete all memories for <strong>{{ character?.name }}</strong>. This cannot be undone.
            </p>
            <div class="flex gap-2 justify-end">
              <button @click="showConfirmClear = false" class="btn-secondary">Cancel</button>
              <button @click="handleClearAll" class="btn-danger">
                <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
                </svg>
                Clear All
              </button>
            </div>
          </div>
        </div>
      </transition>
    </Teleport>
  </div>
</template>
