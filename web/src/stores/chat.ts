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
  error?: boolean
}

export const useChatStore = defineStore('chat', () => {
  const messages = ref<ChatMessage[]>([])
  const loading = ref(false)
  const loadingOlder = ref(false)
  const hasMore = ref(true)
  const ws = ref<WebSocket | null>(null)
  const connectionStatus = ref<'connected' | 'reconnecting' | 'disconnected'>('disconnected')
  const streamingContent = ref('')

  // Reconnect state
  let reconnectAttempts = 0
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null
  const MAX_RECONNECT_ATTEMPTS = 5
  let storedCharacterId = ''
  let storedOnMessage: ((msg: any) => void) | null = null

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
    } catch (e) {
      // Mark the last user message as failed
      const lastMsg = messages.value[messages.value.length - 1]
      if (lastMsg?.role === 'user') {
        // Add an empty assistant message with error flag for retry
        messages.value.push({ role: 'assistant', content: '', error: true })
      }
      throw e
    } finally {
      loading.value = false
    }
  }

  function _scheduleReconnect() {
    if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
      connectionStatus.value = 'disconnected'
      return
    }
    connectionStatus.value = 'reconnecting'
    const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 16000)
    reconnectTimer = setTimeout(() => {
      reconnectAttempts++
      if (storedCharacterId && storedOnMessage) {
        _doConnect(storedCharacterId, storedOnMessage)
      }
    }, delay)
  }

  function _doConnect(characterId: string, onMessage: (msg: any) => void) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/api/chat/${characterId}/ws`
    connectionStatus.value = 'reconnecting'
    const socket = new WebSocket(wsUrl)
    ws.value = socket

    socket.onopen = () => {
      reconnectAttempts = 0
      connectionStatus.value = 'connected'
    }

    socket.onmessage = (event) => {
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
      } else if (data.type === 'chunk') {
        streamingContent.value += data.content
      } else if (data.type === 'typing') {
        onMessage({ type: 'typing' })
      } else if (data.type === 'done') {
        // Streaming complete - create the final message
        const finalMsg: ChatMessage = {
          id: data.id,
          role: 'assistant',
          content: streamingContent.value || data.content || '',
          image_url: data.image_url || null,
          audio_url: data.audio_url || null,
          video_url: data.video_url || null,
          media_status: data.media_status || null,
          created_at: data.created_at || new Date().toISOString(),
        }
        messages.value.push(finalMsg)
        streamingContent.value = ''
        onMessage(finalMsg)
      } else {
        messages.value.push(data as ChatMessage)
        onMessage(data)
      }
    }

    socket.onclose = () => {
      ws.value = null
      if (connectionStatus.value === 'connected' || connectionStatus.value === 'reconnecting') {
        // Unexpected close - attempt reconnect
        _scheduleReconnect()
      }
    }

    socket.onerror = () => {
      // onerror is always followed by onclose, so reconnect is handled there
    }
  }

  function connectWebSocket(characterId: string, onMessage: (msg: any) => void) {
    storedCharacterId = characterId
    storedOnMessage = onMessage
    reconnectAttempts = 0
    _doConnect(characterId, onMessage)
  }

  function sendViaWebSocket(content: string) {
    if (ws.value && ws.value.readyState === WebSocket.OPEN) {
      messages.value.push({ role: 'user', content })
      ws.value.send(JSON.stringify({ content }))
    }
  }

  function retryMessage(characterId: string, index: number) {
    // Find the user message before the failed assistant message
    let userMsgContent = ''
    for (let i = index - 1; i >= 0; i--) {
      if (messages.value[i].role === 'user') {
        userMsgContent = messages.value[i].content
        break
      }
    }
    if (!userMsgContent) return

    // Remove the error assistant message
    messages.value.splice(index, 1)

    // Resend
    if (ws.value && ws.value.readyState === WebSocket.OPEN) {
      ws.value.send(JSON.stringify({ content: userMsgContent }))
    } else {
      sendMessage(characterId, userMsgContent)
    }
  }

  function disconnectWebSocket() {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    connectionStatus.value = 'disconnected'
    storedCharacterId = ''
    storedOnMessage = null
    if (ws.value) {
      ws.value.close()
      ws.value = null
    }
  }

  return {
    messages, loading, loadingOlder, hasMore, ws, connectionStatus, streamingContent,
    fetchHistory, loadOlderMessages, sendMessage,
    connectWebSocket, sendViaWebSocket, disconnectWebSocket, retryMessage,
  }
})
