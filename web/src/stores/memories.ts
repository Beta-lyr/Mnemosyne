import { defineStore } from 'pinia'
import { ref } from 'vue'
import axios from 'axios'

export interface Memory {
  id: string
  character_id: string
  type: 'fact' | 'feeling' | 'event'
  content: string
  metadata: Record<string, unknown>
  importance: number
  created_at: string
}

export const useMemoryStore = defineStore('memories', () => {
  const memories = ref<Memory[]>([])
  const loading = ref(false)
  const filter = ref<string>('')

  async function fetchMemories(characterId: string, type?: string) {
    loading.value = true
    try {
      const params: Record<string, string> = {}
      if (type) params.type = type
      const { data } = await axios.get(`/api/memories/${characterId}`, { params })
      memories.value = data
    } finally {
      loading.value = false
    }
  }

  async function deleteMemory(memoryId: string) {
    await axios.delete(`/api/memories/${memoryId}`)
    memories.value = memories.value.filter((m) => m.id !== memoryId)
  }

  async function clearAllMemories(characterId: string) {
    await axios.delete(`/api/memories/${characterId}/all`)
    memories.value = []
  }

  async function exportMemories(characterId: string) {
    const { data } = await axios.get(`/api/memories/${characterId}/export`)
    return data
  }

  return { memories, loading, filter, fetchMemories, deleteMemory, clearAllMemories, exportMemories }
})
