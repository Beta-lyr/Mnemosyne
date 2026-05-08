<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick, computed } from 'vue'
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
const waitingForResponse = ref(false)

const isTyping = computed(() => waitingForResponse.value || chatStore.loading)

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
    waitingForResponse.value = false
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
    waitingForResponse.value = true
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
  <div class="flex flex-col h-[calc(100vh-7rem)] animate-fade-in">

    <!-- Chat Header -->
    <div class="flex items-center gap-3 mb-4 pb-4 border-b border-gray-100">
      <button
        @click="router.push('/')"
        class="btn-ghost p-2 rounded-xl"
        aria-label="Back"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
        </svg>
      </button>

      <div class="w-10 h-10 rounded-full overflow-hidden bg-primary-100 flex items-center justify-center ring-2 ring-primary/20">
        <img
          v-if="character?.base_image_url"
          :src="character.base_image_url"
          :alt="character?.name"
          class="w-full h-full object-cover"
        />
        <span v-else class="text-primary font-bold text-sm">
          {{ character?.name?.[0]?.toUpperCase() }}
        </span>
      </div>

      <div class="flex-1 min-w-0">
        <h2 class="font-display font-bold text-lg leading-tight truncate">
          {{ character?.name }}
        </h2>
        <span class="badge badge-primary text-[10px] mt-0.5">
          {{ character?.mood_default || 'Neutral' }}
        </span>
      </div>
    </div>

    <!-- Messages Area -->
    <div
      ref="messagesContainer"
      class="flex-1 overflow-y-auto px-1 pb-4 space-y-3"
    >
      <!-- Empty State -->
      <div
        v-if="chatStore.messages.length === 0 && !isTyping"
        class="flex flex-col items-center justify-center h-full text-center py-16"
      >
        <div class="w-20 h-20 rounded-full bg-primary-50 flex items-center justify-center mb-4">
          <svg class="w-10 h-10 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
              d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
          </svg>
        </div>
        <p class="font-display text-lg text-gray-600 mb-1">
          Start chatting with {{ character?.name }}
        </p>
        <p class="text-sm text-gray-400 max-w-xs">
          Say hello and begin your conversation!
        </p>
      </div>

      <!-- Message Bubbles -->
      <div
        v-for="(msg, i) in chatStore.messages"
        :key="i"
        :class="msg.role === 'user' ? 'flex justify-end' : 'flex justify-start'"
        class="animate-slide-up"
      >
        <!-- Assistant avatar (small, left side) -->
        <div v-if="msg.role !== 'user'" class="flex items-end gap-2 max-w-[75%]">
          <div class="w-7 h-7 rounded-full overflow-hidden bg-primary-100 flex-shrink-0 flex items-center justify-center">
            <img
              v-if="character?.base_image_url"
              :src="character.base_image_url"
              :alt="character?.name"
              class="w-full h-full object-cover"
            />
            <span v-else class="text-primary font-bold text-[10px]">
              {{ character?.name?.[0]?.toUpperCase() }}
            </span>
          </div>
          <div>
            <div class="bg-gray-100 text-gray-800 rounded-2xl rounded-bl-sm px-4 py-2.5 shadow-bubble">
              <p class="whitespace-pre-wrap text-sm leading-relaxed font-sans">{{ msg.content }}</p>
              <img
                v-if="msg.image_url"
                :src="msg.image_url"
                class="mt-2 rounded-lg max-w-[240px] w-full object-cover"
                alt="Message image"
              />
              <audio
                v-if="msg.audio_url"
                :src="msg.audio_url"
                controls
                class="mt-2 w-full max-w-[240px]"
              ></audio>
              <video
                v-if="msg.video_url"
                :src="msg.video_url"
                controls
                class="mt-2 rounded-lg max-w-[240px] w-full"
              ></video>
            </div>
          </div>
        </div>

        <!-- User message (right side) -->
        <div v-else class="max-w-[75%]">
          <div class="bg-primary text-white rounded-2xl rounded-br-sm px-4 py-2.5 shadow-bubble">
            <p class="whitespace-pre-wrap text-sm leading-relaxed font-sans">{{ msg.content }}</p>
            <img
              v-if="msg.image_url"
              :src="msg.image_url"
              class="mt-2 rounded-lg max-w-[240px] w-full object-cover"
              alt="Message image"
            />
            <audio
              v-if="msg.audio_url"
              :src="msg.audio_url"
              controls
              class="mt-2 w-full max-w-[240px]"
            ></audio>
            <video
              v-if="msg.video_url"
              :src="msg.video_url"
              controls
              class="mt-2 rounded-lg max-w-[240px] w-full"
            ></video>
          </div>
        </div>
      </div>

      <!-- Typing Indicator -->
      <div v-if="isTyping" class="flex items-end gap-2 animate-slide-up">
        <div class="w-7 h-7 rounded-full overflow-hidden bg-primary-100 flex-shrink-0 flex items-center justify-center">
          <img
            v-if="character?.base_image_url"
            :src="character.base_image_url"
            :alt="character?.name"
            class="w-full h-full object-cover"
          />
          <span v-else class="text-primary font-bold text-[10px]">
            {{ character?.name?.[0]?.toUpperCase() }}
          </span>
        </div>
        <div class="bg-gray-100 rounded-2xl rounded-bl-sm px-4 py-3 shadow-bubble">
          <div class="flex items-center gap-1">
            <span
              class="w-2 h-2 bg-gray-400 rounded-full animate-typing"
              style="animation-delay: 0s"
            ></span>
            <span
              class="w-2 h-2 bg-gray-400 rounded-full animate-typing"
              style="animation-delay: 0.2s"
            ></span>
            <span
              class="w-2 h-2 bg-gray-400 rounded-full animate-typing"
              style="animation-delay: 0.4s"
            ></span>
          </div>
        </div>
      </div>
    </div>

    <!-- Input Area -->
    <div class="flex items-end gap-2 pt-3 border-t border-gray-100">
      <textarea
        v-model="inputText"
        @keydown="handleKeydown"
        rows="1"
        placeholder="Type a message..."
        class="input flex-1 resize-none min-h-[44px] max-h-[120px] py-3"
      ></textarea>
      <button
        @click="handleSend"
        :disabled="!inputText.trim() || isTyping"
        class="btn-primary p-3 rounded-xl flex-shrink-0"
        aria-label="Send message"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
            d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
        </svg>
      </button>
    </div>

  </div>
</template>
