import { defineStore } from 'pinia'
import { ref } from 'vue'
import axios from 'axios'

export interface ChatMessage {
  id?: string
  role: 'user' | 'assistant'
  content: string
  image_url?: string | null
  audio_url?: string | null
  video_url?: string | null
  media_status?: string | null
  created_at?: string | null
}

export const useChatStore = defineStore('chat', () => {
  const messages = ref<ChatMessage[]>([])
  const loading = ref(false)
  const loadingOlder = ref(false)
  const hasMore = ref(true)
  const ws = ref<WebSocket | null>(null)

  async function fetchHistory(characterId: string) {
    const { data } = await axios.get(`/api/chat/${characterId}/history`, { params: { limit: 30 } })
    messages.value = data.messages
    hasMore.value = data.has_more
  }

  async function loadOlderMessages(characterId: string) {
    if (loadingOlder.value || !hasMore.value || messages.value.length === 0) return
    loadingOlder.value = true
    try {
      const oldest = messages.value[0]
      const before = oldest?.created_at
      if (!before) { hasMore.value = false; return }
      const { data } = await axios.get(`/api/chat/${characterId}/history`, { params: { limit: 30, before } })
      messages.value = [...data.messages, ...messages.value]
      hasMore.value = data.has_more
    } finally {
      loadingOlder.value = false
    }
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

  function connectWebSocket(characterId: string, onMessage: (msg: any) => void) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/api/chat/${characterId}/ws`
    ws.value = new WebSocket(wsUrl)

    ws.value.onmessage = (event) => {
      const data = JSON.parse(event.data)
      if (data.type === 'media_update') {
        const msg = messages.value.find(m => m.id === data.message_id)
        if (msg) {
          if (data.image_url) msg.image_url = data.image_url
          if (data.audio_url) msg.audio_url = data.audio_url
          if (data.video_url) msg.video_url = data.video_url
          msg.media_status = 'ready'
        }
      } else if (data.type === 'read_receipt') {
        onMessage({ type: 'read_receipt' })
      } else {
        messages.value.push(data as ChatMessage)
        onMessage(data)
      }
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
    messages, loading, loadingOlder, hasMore, ws,
    fetchHistory, loadOlderMessages, sendMessage,
    connectWebSocket, sendViaWebSocket, disconnectWebSocket,
  }
})
