import { defineStore } from 'pinia'
import { ref } from 'vue'
import axios from 'axios'

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  image_url?: string | null
  audio_url?: string | null
  video_url?: string | null
}

export const useChatStore = defineStore('chat', () => {
  const messages = ref<ChatMessage[]>([])
  const loading = ref(false)
  const ws = ref<WebSocket | null>(null)

  async function fetchHistory(characterId: string) {
    const { data } = await axios.get(`/api/chat/${characterId}/history`)
    messages.value = data
  }

  async function sendMessage(characterId: string, content: string): Promise<ChatMessage> {
    loading.value = true
    try {
      messages.value.push({ role: 'user', content })
      const { data } = await axios.post(`/api/chat/${characterId}/message`, { content })
      messages.value.push(data)
      return data
    } finally {
      loading.value = false
    }
  }

  function connectWebSocket(characterId: string, onMessage: (msg: ChatMessage) => void) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/api/chat/${characterId}/ws`
    ws.value = new WebSocket(wsUrl)

    ws.value.onmessage = (event) => {
      const msg = JSON.parse(event.data) as ChatMessage
      messages.value.push(msg)
      onMessage(msg)
    }

    ws.value.onclose = () => {
      ws.value = null
    }
  }

  function sendViaWebSocket(content: string) {
    if (ws.value && ws.value.readyState === WebSocket.OPEN) {
      messages.value.push({ role: 'user', content })
      ws.value.send(JSON.stringify({ content }))
    }
  }

  function disconnectWebSocket() {
    if (ws.value) {
      ws.value.close()
      ws.value = null
    }
  }

  return {
    messages, loading, ws,
    fetchHistory, sendMessage,
    connectWebSocket, sendViaWebSocket, disconnectWebSocket,
  }
})
