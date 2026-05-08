<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useChatStore } from '../stores/chat'
import { useCharacterStore } from '../stores/characters'
import type { Character } from '../stores/characters'
import type { ChatMessage } from '../stores/chat'
import CacheDialog from './CacheDialog.vue'
import ImageLightbox from '../components/ImageLightbox.vue'
import MarkdownRenderer from '../components/MarkdownRenderer.vue'
import VoiceBar from '../components/VoiceBar.vue'

const route = useRoute()
const router = useRouter()
const chatStore = useChatStore()
const charStore = useCharacterStore()

const character = ref<Character | null>(null)
const inputText = ref('')
const messagesContainer = ref<HTMLDivElement | null>(null)
const waitingForResponse = ref(false)
const serverTyping = ref(false)
const showReadReceipt = ref(false)
const showCacheDialog = ref(false)
const characterId = ref('')
const lightboxSrc = ref<string | null>(null)
const showExportMenu = ref(false)

const isTyping = computed(() => waitingForResponse.value || serverTyping.value || chatStore.loading)

// Time divider logic
interface DisplayItem {
  type: 'divider' | 'message'
  time?: string
  message?: ChatMessage
  readReceipt?: boolean
}

const displayItems = computed<DisplayItem[]>(() => {
  const items: DisplayItem[] = []
  const msgs = chatStore.messages
  for (let i = 0; i < msgs.length; i++) {
    const msg = msgs[i]
    const msgTime = msg.created_at ? new Date(msg.created_at) : null
    const prevTime = i > 0 && msgs[i - 1].created_at ? new Date(msgs[i - 1].created_at!) : null
    if (msgTime && prevTime && msgTime.getTime() - prevTime.getTime() >= 5 * 60 * 1000) {
      items.push({ type: 'divider', time: formatDividerTime(msgTime) })
    } else if (i === 0 && msgTime) {
      items.push({ type: 'divider', time: formatDividerTime(msgTime) })
    }
    items.push({ type: 'message', message: msg })
  }
  return items
})

function formatDividerTime(date: Date): string {
  const now = new Date()
  const isToday = date.toDateString() === now.toDateString()
  const yesterday = new Date(now)
  yesterday.setDate(yesterday.getDate() - 1)
  const isYesterday = date.toDateString() === yesterday.toDateString()
  const hh = String(date.getHours()).padStart(2, '0')
  const mm = String(date.getMinutes()).padStart(2, '0')
  if (isToday) return `${hh}:${mm}`
  if (isYesterday) return `Yesterday ${hh}:${mm}`
  const M = String(date.getMonth() + 1).padStart(2, '0')
  const D = String(date.getDate()).padStart(2, '0')
  return `${M}-${D} ${hh}:${mm}`
}

function scrollToBottom(smooth = false) {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTo({
        top: messagesContainer.value.scrollHeight,
        behavior: smooth ? 'smooth' : 'instant',
      })
    }
  })
}

let scrollSaveHeight = 0

async function handleScroll() {
  const el = messagesContainer.value
  if (!el || chatStore.loadingOlder || !chatStore.hasMore) return
  if (el.scrollTop <= 20) {
    scrollSaveHeight = el.scrollHeight
    await chatStore.loadOlderMessages(characterId.value)
    nextTick(() => {
      el.scrollTop = el.scrollHeight - scrollSaveHeight
    })
  }
}

// Auto-scroll when streaming content updates
watch(() => chatStore.streamingContent, () => {
  scrollToBottom(true)
})

// Server typing timeout
let typingTimeout: ReturnType<typeof setTimeout> | null = null

onMounted(async () => {
  characterId.value = route.params.id as string
  if (charStore.characters.length === 0) await charStore.fetchCharacters()
  character.value = charStore.characters.find((c) => c.id === characterId.value) || null

  if (!character.value) {
    router.push('/characters')
    return
  }

  await chatStore.fetchHistory(characterId.value)
  scrollToBottom()

  chatStore.connectWebSocket(characterId.value, (msg: any) => {
    if (msg.type === 'read_receipt') {
      showReadReceipt.value = true
      waitingForResponse.value = false
      serverTyping.value = false
      if (typingTimeout) clearTimeout(typingTimeout)
      setTimeout(() => { showReadReceipt.value = false }, 5000)
      return
    }
    if (msg.type === 'typing') {
      serverTyping.value = true
      if (typingTimeout) clearTimeout(typingTimeout)
      typingTimeout = setTimeout(() => { serverTyping.value = false }, 30000)
      return
    }
    showReadReceipt.value = false
    waitingForResponse.value = false
    serverTyping.value = false
    if (typingTimeout) clearTimeout(typingTimeout)
    scrollToBottom(true)
  })

  // Listen for viewport resize (mobile keyboard)
  if (window.visualViewport) {
    window.visualViewport.addEventListener('resize', () => {
      scrollToBottom()
    })
  }
})

onUnmounted(() => {
  chatStore.disconnectWebSocket()
  if (typingTimeout) clearTimeout(typingTimeout)
  if (window.visualViewport) {
    window.visualViewport.removeEventListener('resize', () => {})
  }
})

async function handleSend() {
  const text = inputText.value.trim()
  if (!text || !character.value) return
  inputText.value = ''
  showReadReceipt.value = false
  scrollToBottom()

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

function isMediaCleared(msg: ChatMessage): boolean {
  return msg.media_status === 'cleared'
}

function openLightbox(src: string) {
  lightboxSrc.value = src
}

function handleRetry(index: number) {
  chatStore.retryMessage(characterId.value, index)
}

function exportChat(format: 'txt' | 'json') {
  showExportMenu.value = false
  const url = `/api/chat/${characterId.value}/export?format=${format}`
  const a = document.createElement('a')
  a.href = url
  a.download = `chat_${character.value?.name || 'export'}.${format}`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
}

// Close export menu on outside click
function handleDocumentClick(e: MouseEvent) {
  const target = e.target as HTMLElement
  if (!target.closest('.export-menu-container')) {
    showExportMenu.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', handleDocumentClick)
})
onUnmounted(() => {
  document.removeEventListener('click', handleDocumentClick)
})
</script>

<template>
  <div class="flex flex-col h-[calc(100vh-7rem)] animate-fade-in max-md:h-[calc(100vh-4rem)]">

    <!-- Chat Header -->
    <div class="flex items-center gap-3 mb-4 pb-4 border-b border-gray-100 flex-shrink-0">
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
        <div class="flex items-center gap-2">
          <h2 class="font-display font-bold text-lg leading-tight truncate max-md:text-base">
            {{ character?.name }}
          </h2>
          <!-- Connection status dot -->
          <span
            class="w-2 h-2 rounded-full flex-shrink-0"
            :class="{
              'bg-green-400': chatStore.connectionStatus === 'connected',
              'bg-yellow-400 animate-pulse': chatStore.connectionStatus === 'reconnecting',
              'bg-red-400': chatStore.connectionStatus === 'disconnected',
            }"
            :title="chatStore.connectionStatus"
          />
        </div>
        <span class="badge badge-primary text-[10px] mt-0.5">
          {{ character?.mood_default || 'Neutral' }}
        </span>
      </div>

      <!-- Export button -->
      <div class="relative export-menu-container">
        <button
          @click.stop="showExportMenu = !showExportMenu"
          class="btn-ghost p-2 rounded-xl"
          aria-label="Export"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
        </button>
        <transition name="menu">
          <div v-if="showExportMenu" class="absolute right-0 top-full mt-1 bg-white rounded-xl shadow-modal border border-gray-100 py-1 z-50 min-w-[120px]">
            <button @click="exportChat('txt')" class="w-full px-4 py-2 text-sm text-left hover:bg-gray-50 transition-colors">
              Export .txt
            </button>
            <button @click="exportChat('json')" class="w-full px-4 py-2 text-sm text-left hover:bg-gray-50 transition-colors">
              Export .json
            </button>
          </div>
        </transition>
      </div>

      <button
        @click="router.push(`/analytics/${characterId}`)"
        class="btn-ghost p-2 rounded-xl max-md:hidden"
        aria-label="Analytics"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
            d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
        </svg>
      </button>
      <button
        @click="showCacheDialog = true"
        class="btn-ghost p-2 rounded-xl"
        aria-label="Cache"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
            d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
        </svg>
      </button>
      <button
        @click="router.push(`/characters/${character?.id}`)"
        class="btn-ghost p-2 rounded-xl"
        aria-label="Settings"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
            d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
      </button>
    </div>

    <!-- Connection banner -->
    <div
      v-if="chatStore.connectionStatus === 'reconnecting'"
      class="flex items-center justify-center gap-2 py-2 px-4 bg-yellow-50 text-yellow-700 text-sm rounded-xl mb-3 animate-fade-in"
    >
      <svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
      </svg>
      Connection lost, reconnecting...
    </div>

    <!-- Messages Area -->
    <div
      ref="messagesContainer"
      class="flex-1 overflow-y-auto px-1 pb-4 space-y-3"
      @scroll="handleScroll"
      style="-webkit-overflow-scrolling: touch;"
    >
      <!-- Loading older messages indicator -->
      <div v-if="chatStore.loadingOlder" class="flex justify-center py-3">
        <div class="flex items-center gap-2 text-sm text-gray-400">
          <svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
          </svg>
          Loading earlier messages...
        </div>
      </div>

      <!-- No more messages -->
      <div v-if="!chatStore.hasMore && chatStore.messages.length > 0" class="flex justify-center py-2">
        <span class="text-xs text-gray-300">Beginning of conversation</span>
      </div>

      <!-- Empty State -->
      <div
        v-if="chatStore.messages.length === 0 && !isTyping && !chatStore.loadingOlder && !chatStore.streamingContent"
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

      <!-- Display Items (dividers + messages) -->
      <template v-for="(item, i) in displayItems" :key="i">
        <!-- Time Divider -->
        <div v-if="item.type === 'divider'" class="flex items-center gap-3 py-2">
          <div class="flex-1 h-px bg-gray-200"></div>
          <span class="text-xs text-gray-400 whitespace-nowrap">{{ item.time }}</span>
          <div class="flex-1 h-px bg-gray-200"></div>
        </div>

        <!-- Message Bubble -->
        <div
          v-else-if="item.type === 'message' && item.message"
          :class="item.message.role === 'user' ? 'flex justify-end' : 'flex justify-start'"
          class="animate-slide-up"
        >
          <!-- Assistant avatar -->
          <div v-if="item.message.role !== 'user'" class="flex items-start gap-2 max-w-[85%] md:max-w-[75%]">
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
                <!-- Markdown content for assistant -->
                <MarkdownRenderer
                  v-if="item.message.content"
                  :content="item.message.content"
                />
                <p v-else class="whitespace-pre-wrap text-sm leading-relaxed font-sans text-gray-400 italic">Empty response</p>

                <!-- Retry button for error messages -->
                <button
                  v-if="item.message.error"
                  @click="handleRetry(i)"
                  class="mt-2 flex items-center gap-1.5 text-xs text-red-500 hover:text-red-600 transition-colors"
                >
                  <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                      d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                  Retry
                </button>

                <!-- Image: show or placeholder -->
                <template v-if="item.message.image_url && !isMediaCleared(item.message)">
                  <img
                    :src="item.message.image_url"
                    class="mt-2 rounded-lg max-w-[240px] w-full object-cover cursor-pointer hover:opacity-90 transition-opacity"
                    alt="Image"
                    @click="openLightbox(item.message.image_url!)"
                  />
                </template>
                <div v-else-if="item.message.media_status === 'cleared' && item.message.image_url === null"
                  class="mt-2 w-[240px] h-[160px] bg-gray-100 rounded-lg flex flex-col items-center justify-center text-gray-400">
                  <svg class="w-8 h-8 mb-1" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909M3.75 21h16.5A2.25 2.25 0 0022.5 18.75V5.25A2.25 2.25 0 0020.25 3H3.75A2.25 2.25 0 001.5 5.25v13.5A2.25 2.25 0 003.75 21z" />
                  </svg>
                  <span class="text-xs">Image cleared</span>
                </div>
                <div v-else-if="item.message.media_status === 'pending'"
                  class="mt-2 w-[240px] h-[160px] bg-gray-50 rounded-lg flex items-center justify-center">
                  <div class="flex flex-col items-center gap-2 text-gray-400">
                    <svg class="w-6 h-6 animate-spin" fill="none" viewBox="0 0 24 24">
                      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                      <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
                    </svg>
                    <span class="text-xs">Generating image...</span>
                  </div>
                </div>

                <!-- Audio -->
                <template v-if="item.message.audio_url && !isMediaCleared(item.message)">
                  <VoiceBar :src="item.message.audio_url" class="mt-2" />
                </template>
                <div v-else-if="item.message.media_status === 'cleared' && item.message.audio_url === null"
                  class="mt-2 w-[240px] h-[40px] bg-gray-100 rounded-lg flex items-center justify-center gap-2 text-gray-400">
                  <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M9 10a1 1 0 011-1h1a1 1 0 011 1v4a1 1 0 01-1 1h-1a1 1 0 01-1-1v-4z" />
                  </svg>
                  <span class="text-xs">Audio cleared</span>
                </div>
                <div v-else-if="item.message.media_status === 'pending' && !item.message.audio_url"
                  class="mt-2 w-[240px] h-[40px] bg-gray-50 rounded-lg flex items-center justify-center gap-2 text-gray-400">
                  <svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
                  </svg>
                  <span class="text-xs">Generating audio...</span>
                </div>

                <!-- Video -->
                <template v-if="item.message.video_url && !isMediaCleared(item.message)">
                  <video :src="item.message.video_url" controls class="mt-2 rounded-lg max-w-[240px] w-full"></video>
                </template>
                <div v-else-if="item.message.media_status === 'cleared' && item.message.video_url === null"
                  class="mt-2 w-[240px] h-[135px] bg-gray-100 rounded-lg flex flex-col items-center justify-center text-gray-400">
                  <svg class="w-8 h-8 mb-1" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 10.5l4.72-4.72a.75.75 0 011.28.53v11.38a.75.75 0 01-1.28.53l-4.72-4.72M4.5 18.75h9a2.25 2.25 0 002.25-2.25v-9a2.25 2.25 0 00-2.25-2.25h-9A2.25 2.25 0 002.25 7.5v9a2.25 2.25 0 002.25 2.25z" />
                  </svg>
                  <span class="text-xs">Video cleared</span>
                </div>
                <div v-else-if="item.message.media_status === 'pending' && !item.message.video_url"
                  class="mt-2 w-[240px] h-[135px] bg-gray-50 rounded-lg flex items-center justify-center">
                  <div class="flex flex-col items-center gap-2 text-gray-400">
                    <svg class="w-6 h-6 animate-spin" fill="none" viewBox="0 0 24 24">
                      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                      <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
                    </svg>
                    <span class="text-xs">Generating video...</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- User message -->
          <div v-else class="max-w-[85%] md:max-w-[75%]">
            <div class="bg-primary text-white rounded-2xl rounded-br-sm px-4 py-2.5 shadow-bubble">
              <p class="whitespace-pre-wrap text-sm leading-relaxed font-sans">{{ item.message.content }}</p>
              <template v-if="item.message.image_url && !isMediaCleared(item.message)">
                <img
                  :src="item.message.image_url"
                  class="mt-2 rounded-lg max-w-[240px] w-full object-cover cursor-pointer hover:opacity-90 transition-opacity"
                  alt="Image"
                  @click="openLightbox(item.message.image_url!)"
                />
              </template>
              <template v-if="item.message.audio_url && !isMediaCleared(item.message)">
                <VoiceBar :src="item.message.audio_url" is-user class="mt-2" />
              </template>
              <template v-if="item.message.video_url && !isMediaCleared(item.message)">
                <video :src="item.message.video_url" controls class="mt-2 rounded-lg max-w-[240px] w-full"></video>
              </template>
            </div>
            <!-- Read receipt under last user message -->
            <div v-if="showReadReceipt && i === displayItems.length - 1" class="text-right mt-1">
              <span class="text-xs text-gray-400">Read</span>
            </div>
          </div>
        </div>
      </template>

      <!-- Streaming message (in-progress) -->
      <div v-if="chatStore.streamingContent" class="flex justify-start animate-slide-up">
        <div class="flex items-start gap-2 max-w-[85%] md:max-w-[75%]">
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
          <div class="bg-gray-100 text-gray-800 rounded-2xl rounded-bl-sm px-4 py-2.5 shadow-bubble">
            <MarkdownRenderer :content="chatStore.streamingContent" />
            <span class="inline-block w-0.5 h-4 bg-gray-400 animate-pulse ml-0.5 align-text-bottom"></span>
          </div>
        </div>
      </div>

      <!-- Typing Indicator -->
      <div v-if="isTyping && !showReadReceipt && !chatStore.streamingContent" class="flex items-start gap-2 animate-slide-up">
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
            <span class="w-2 h-2 bg-gray-400 rounded-full animate-typing" style="animation-delay: 0s"></span>
            <span class="w-2 h-2 bg-gray-400 rounded-full animate-typing" style="animation-delay: 0.2s"></span>
            <span class="w-2 h-2 bg-gray-400 rounded-full animate-typing" style="animation-delay: 0.4s"></span>
          </div>
        </div>
      </div>
    </div>

    <!-- Input Area -->
    <div class="flex items-end gap-2 pt-3 border-t border-gray-100 flex-shrink-0 pb-[env(safe-area-inset-bottom)]">
      <textarea
        v-model="inputText"
        @keydown="handleKeydown"
        rows="1"
        :placeholder="chatStore.connectionStatus === 'disconnected' ? 'Disconnected...' : 'Type a message...'"
        :disabled="chatStore.connectionStatus === 'disconnected'"
        class="input flex-1 resize-none min-h-[44px] max-h-[120px] py-3 disabled:opacity-50"
      ></textarea>
      <button
        @click="handleSend"
        :disabled="!inputText.trim() || isTyping || chatStore.connectionStatus === 'disconnected'"
        class="btn-primary p-3 rounded-xl flex-shrink-0"
        aria-label="Send message"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
            d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
        </svg>
      </button>
    </div>

    <!-- Cache Dialog -->
    <CacheDialog
      v-if="showCacheDialog && character"
      :character-id="characterId"
      :character-name="character.name"
      @close="showCacheDialog = false"
      @cleared="showCacheDialog = false"
    />

    <!-- Image Lightbox -->
    <ImageLightbox
      v-if="lightboxSrc"
      :src="lightboxSrc"
      @close="lightboxSrc = null"
    />
  </div>
</template>

<style scoped>
.menu-enter-active,
.menu-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}
.menu-enter-from,
.menu-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>
