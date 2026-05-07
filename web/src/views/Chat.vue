<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useChatStore } from '../stores/chat'
import { useCharacterStore } from '../stores/characters'
import type { Character } from '../stores/characters'

const route = useRoute()
const router = useRouter()
const chatStore = useChatStore()
const charStore = useCharacterStore()

const character = ref<Character | null>(null)
const inputText = ref('')
const messagesContainer = ref<HTMLDivElement | null>(null)

onMounted(async () => {
  const id = route.params.id as string
  if (charStore.characters.length === 0) await charStore.fetchCharacters()
  character.value = charStore.characters.find((c) => c.id === id) || null

  if (!character.value) {
    router.push('/characters')
    return
  }

  await chatStore.fetchHistory(id)
  scrollToBottom()

  // Connect WebSocket for real-time chat
  chatStore.connectWebSocket(id, () => {
    scrollToBottom()
  })
})

onUnmounted(() => {
  chatStore.disconnectWebSocket()
})

function scrollToBottom() {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

async function handleSend() {
  const text = inputText.value.trim()
  if (!text || !character.value) return
  inputText.value = ''
  scrollToBottom()

  // Use WebSocket if connected, otherwise REST
  if (chatStore.ws && chatStore.ws.readyState === WebSocket.OPEN) {
    chatStore.sendViaWebSocket(text)
  } else {
    await chatStore.sendMessage(character.value.id, text)
  }
  scrollToBottom()
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSend()
  }
}
</script>

<template>
  <div class="flex flex-col h-[calc(100vh-7rem)]">
    <!-- Header -->
    <div class="flex items-center gap-3 mb-4">
      <button @click="router.push('/')" class="text-gray-500 hover:text-gray-700">&larr;</button>
      <div class="w-10 h-10 rounded-full bg-purple-100 flex items-center justify-center overflow-hidden">
        <img v-if="character?.base_image_url" :src="character.base_image_url" class="w-full h-full object-cover" />
        <span v-else class="text-purple-600 font-bold">{{ character?.name?.[0] }}</span>
      </div>
      <div>
        <h2 class="font-bold text-lg">{{ character?.name }}</h2>
        <p class="text-xs text-gray-400">Mood: {{ character?.mood_default }}</p>
      </div>
    </div>

    <!-- Messages -->
    <div ref="messagesContainer" class="flex-1 overflow-y-auto bg-white rounded-xl border p-4 mb-4 space-y-3">
      <div v-if="chatStore.messages.length === 0" class="text-center text-gray-400 py-12">
        Start a conversation with {{ character?.name }}...
      </div>

      <div v-for="(msg, i) in chatStore.messages" :key="i"
        :class="msg.role === 'user' ? 'flex justify-end' : 'flex justify-start'">
        <div :class="[
          'max-w-[70%] rounded-2xl px-4 py-2',
          msg.role === 'user'
            ? 'bg-purple-600 text-white rounded-br-sm'
            : 'bg-gray-100 text-gray-800 rounded-bl-sm'
        ]">
          <p class="whitespace-pre-wrap">{{ msg.content }}</p>
          <img v-if="msg.image_url" :src="msg.image_url" class="mt-2 rounded-lg max-w-xs" />
        </div>
      </div>

      <div v-if="chatStore.loading" class="flex justify-start">
        <div class="bg-gray-100 rounded-2xl rounded-bl-sm px-4 py-2">
          <span class="animate-pulse">...</span>
        </div>
      </div>
    </div>

    <!-- Input -->
    <div class="flex gap-2">
      <textarea v-model="inputText" @keydown="handleKeydown" rows="1"
        placeholder="Type a message... (Enter to send, Shift+Enter for newline)"
        class="flex-1 border rounded-xl px-4 py-2 resize-none focus:outline-none focus:ring-2 focus:ring-purple-500"></textarea>
      <button @click="handleSend" :disabled="!inputText.trim() || chatStore.loading"
        class="bg-purple-600 text-white px-6 py-2 rounded-xl hover:bg-purple-700 disabled:opacity-50">
        Send
      </button>
    </div>
  </div>
</template>
