<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import axios from 'axios'

const props = defineProps<{
  characterId: string
  characterName: string
}>()

const emit = defineEmits<{
  close: []
  cleared: []
}>()

const mediaItems = ref<any[]>([])
const loading = ref(true)
const activeTab = ref<'all' | 'image' | 'audio' | 'video'>('all')
const selectedIds = ref<Set<string>>(new Set())
const deleting = ref(false)

const tabs = [
  { key: 'all' as const, label: 'All' },
  { key: 'image' as const, label: 'Images' },
  { key: 'audio' as const, label: 'Audio' },
  { key: 'video' as const, label: 'Video' },
]

const filteredItems = computed(() => {
  if (activeTab.value === 'all') return mediaItems.value
  return mediaItems.value.filter(item => item.type === activeTab.value)
})

const allSelected = computed(() => {
  return filteredItems.value.length > 0 && filteredItems.value.every(item => selectedIds.value.has(item.message_id + ':' + item.type))
})

async function fetchMedia() {
  loading.value = true
  try {
    const { data } = await axios.get(`/api/chat/${props.characterId}/media`)
    mediaItems.value = data
  } finally {
    loading.value = false
  }
}

function toggleSelect(messageId: string, type: string) {
  const key = messageId + ':' + type
  const s = new Set(selectedIds.value)
  if (s.has(key)) s.delete(key)
  else s.add(key)
  selectedIds.value = s
}

function toggleSelectAll() {
  if (allSelected.value) {
    selectedIds.value = new Set()
  } else {
    const s = new Set<string>()
    filteredItems.value.forEach(item => s.add(item.message_id + ':' + item.type))
    selectedIds.value = s
  }
}

async function deleteSelected() {
  if (selectedIds.value.size === 0) return
  deleting.value = true
  try {
    // Group by message_id for the API
    const ids = [...new Set([...selectedIds.value].map(k => k.split(':')[0]))]
    await axios.delete(`/api/chat/${props.characterId}/media`, {
      data: { ids, media_type: activeTab.value === 'all' ? 'all' : activeTab.value },
    })
    selectedIds.value = new Set()
    await fetchMedia()
    emit('cleared')
  } finally {
    deleting.value = false
  }
}

async function clearAll() {
  deleting.value = true
  try {
    await axios.delete(`/api/chat/${props.characterId}/media`, {
      data: { clear_all: true, media_type: activeTab.value === 'all' ? 'all' : activeTab.value },
    })
    selectedIds.value = new Set()
    await fetchMedia()
    emit('cleared')
  } finally {
    deleting.value = false
  }
}

function formatSize(url: string): string {
  // Just show the filename for now
  return url.split('/').pop() || url
}

function formatDate(iso: string | null): string {
  if (!iso) return ''
  const d = new Date(iso)
  return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

function typeIcon(type: string): string {
  if (type === 'image') return 'M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909M3.75 21h16.5A2.25 2.25 0 0022.5 18.75V5.25A2.25 2.25 0 0020.25 3H3.75A2.25 2.25 0 001.5 5.25v13.5A2.25 2.25 0 003.75 21z'
  if (type === 'audio') return 'M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M9 10a1 1 0 011-1h1a1 1 0 011 1v4a1 1 0 01-1 1h-1a1 1 0 01-1-1v-4z'
  return 'M15.75 10.5l4.72-4.72a.75.75 0 011.28.53v11.38a.75.75 0 01-1.28.53l-4.72-4.72M4.5 18.75h9a2.25 2.25 0 002.25-2.25v-9a2.25 2.25 0 00-2.25-2.25h-9A2.25 2.25 0 002.25 7.5v9a2.25 2.25 0 002.25 2.25z'
}

onMounted(fetchMedia)
</script>

<template>
  <Teleport to="body">
    <transition
      enter-active-class="transition duration-200 ease-out"
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
      leave-active-class="transition duration-150 ease-in"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div class="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50 p-4" @click.self="emit('close')">
        <div class="bg-white rounded-2xl shadow-modal w-full max-w-lg max-h-[80vh] flex flex-col animate-slide-up">
          <!-- Header -->
          <div class="px-6 pt-6 pb-4 border-b border-gray-100">
            <h3 class="text-xl font-display font-bold text-gray-800 mb-1">Cache Manager</h3>
            <p class="text-sm text-gray-500">Manage media files for {{ characterName }}</p>
          </div>

          <!-- Tabs -->
          <div class="flex gap-1 px-6 pt-3">
            <button
              v-for="tab in tabs" :key="tab.key"
              @click="activeTab = tab.key; selectedIds = new Set()"
              class="px-3 py-1.5 text-sm rounded-lg transition-colors"
              :class="activeTab === tab.key ? 'bg-primary text-white' : 'text-gray-500 hover:bg-gray-100'"
            >
              {{ tab.label }}
            </button>
          </div>

          <!-- Content -->
          <div class="flex-1 overflow-y-auto px-6 py-4">
            <!-- Loading -->
            <div v-if="loading" class="space-y-3">
              <div v-for="i in 4" :key="i" class="flex items-center gap-3">
                <div class="w-5 h-5 skeleton rounded"></div>
                <div class="w-10 h-10 skeleton rounded-lg"></div>
                <div class="flex-1 space-y-1">
                  <div class="h-4 w-32 skeleton"></div>
                  <div class="h-3 w-20 skeleton"></div>
                </div>
              </div>
            </div>

            <!-- Empty -->
            <div v-else-if="filteredItems.length === 0" class="text-center py-12 text-gray-400">
              <svg class="w-12 h-12 mx-auto mb-3 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M20.25 7.5l-.625 10.632a2.25 2.25 0 01-2.247 2.118H6.622a2.25 2.25 0 01-2.247-2.118L3.75 7.5m6 4.125l2.25 2.25m0 0l2.25 2.25M12 13.875l2.25-2.25M12 13.875l-2.25 2.25M3.375 7.5h17.25c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125z" />
              </svg>
              <p>No media files found</p>
            </div>

            <!-- List -->
            <div v-else class="space-y-2">
              <div class="flex items-center gap-2 mb-2">
                <button @click="toggleSelectAll" class="text-sm text-accent hover:underline">
                  {{ allSelected ? 'Deselect All' : 'Select All' }}
                </button>
                <span class="text-xs text-gray-400">{{ filteredItems.length }} items</span>
              </div>
              <div
                v-for="item in filteredItems" :key="item.message_id + ':' + item.type"
                class="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-50 cursor-pointer transition-colors"
                @click="toggleSelect(item.message_id, item.type)"
              >
                <input
                  type="checkbox"
                  :checked="selectedIds.has(item.message_id + ':' + item.type)"
                  class="w-4 h-4 rounded border-gray-300 text-primary focus:ring-primary/20"
                  @click.stop
                  @change="toggleSelect(item.message_id, item.type)"
                />
                <div class="w-10 h-10 rounded-lg bg-gray-100 flex items-center justify-center flex-shrink-0">
                  <svg class="w-5 h-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
                    <path stroke-linecap="round" stroke-linejoin="round" :d="typeIcon(item.type)" />
                  </svg>
                </div>
                <div class="flex-1 min-w-0">
                  <p class="text-sm text-gray-700 truncate">{{ formatSize(item.url) }}</p>
                  <p class="text-xs text-gray-400">{{ formatDate(item.created_at) }} &middot; {{ item.type }}</p>
                </div>
              </div>
            </div>
          </div>

          <!-- Footer -->
          <div class="px-6 py-4 border-t border-gray-100 flex gap-2 justify-between">
            <button @click="clearAll" :disabled="deleting || filteredItems.length === 0"
              class="btn-ghost text-sm text-red-500 hover:text-red-700 hover:bg-red-50 disabled:opacity-40">
              Clear {{ activeTab === 'all' ? 'All' : activeTab.charAt(0).toUpperCase() + activeTab.slice(1) }}
            </button>
            <div class="flex gap-2">
              <button @click="emit('close')" class="btn-secondary text-sm">Close</button>
              <button @click="deleteSelected" :disabled="deleting || selectedIds.size === 0"
                class="btn-primary text-sm disabled:opacity-40">
                <svg v-if="deleting" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
                </svg>
                Clear Selected ({{ selectedIds.size }})
              </button>
            </div>
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>
