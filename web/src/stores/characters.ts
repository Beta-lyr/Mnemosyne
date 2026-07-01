import { defineStore } from 'pinia'
import { ref } from 'vue'
import axios from 'axios'

export interface Character {
  id: string
  name: string
  personality: string
  system_prompt: string
  base_image_url: string | null
  mood_default: string
  voice_style: Record<string, unknown>
  telegram_token: string | null
  created_at: string
  // Extended persona fields
  gender: string | null
  age: string | null
  occupation: string | null
  mbti: string | null
  zodiac: string | null
  attachment_style: string | null
  core_vulnerability: string | null
  tone: string | null
  quirks: string | null
  emoji_usage: string | null
  visual_style: string | null
  physical_attributes: string | null
  processed_personality: string | null
  interaction_rules: string[] | null
}

export interface CharacterCreate {
  name: string
  personality: string
  system_prompt?: string
  mood_default?: string
  voice_style?: Record<string, unknown>
  telegram_token?: string
  // Extended persona fields
  gender?: string
  age?: string
  occupation?: string
  mbti?: string
  zodiac?: string
  attachment_style?: string
  core_vulnerability?: string
  tone?: string
  quirks?: string
  emoji_usage?: string
  visual_style?: string
  physical_attributes?: string
  user_free_text?: string
}

export const useCharacterStore = defineStore('characters', () => {
  const characters = ref<Character[]>([])
  const loading = ref(false)

  async function fetchCharacters() {
    loading.value = true
    try {
      const { data } = await axios.get('/api/characters/')
      characters.value = data
    } finally {
      loading.value = false
    }
  }

  async function createCharacter(payload: CharacterCreate): Promise<Character> {
    const { data } = await axios.post('/api/characters/', payload)
    characters.value.push(data)
    return data
  }

  async function updateCharacter(id: string, payload: Partial<CharacterCreate>): Promise<Character> {
    const { data } = await axios.put(`/api/characters/${id}`, payload)
    const idx = characters.value.findIndex((c) => c.id === id)
    if (idx !== -1) characters.value[idx] = data
    return data
  }

  async function deleteCharacter(id: string) {
    await axios.delete(`/api/characters/${id}`)
    characters.value = characters.value.filter((c) => c.id !== id)
  }

  async function uploadImage(id: string, file: File): Promise<string> {
    const formData = new FormData()
    formData.append('file', file)
    const { data } = await axios.post(`/api/characters/${id}/image`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    const idx = characters.value.findIndex((c) => c.id === id)
    if (idx !== -1) characters.value[idx].base_image_url = data.url
    return data.url
  }

  async function exportCard(id: string, format: string = 'yaml') {
    const { data } = await axios.get(`/api/characters/${id}/export`, { params: { format } })
    return data
  }

  async function importCard(card: Record<string, unknown>) {
    const { data } = await axios.post('/api/characters/import', card)
    await fetchCharacters()
    return data
  }

  return {
    characters, loading,
    fetchCharacters, createCharacter, updateCharacter, deleteCharacter,
    uploadImage, exportCard, importCard,
  }
})
