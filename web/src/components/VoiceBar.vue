<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

defineProps<{
  src: string
  isUser?: boolean
}>()

const audio = ref<HTMLAudioElement | null>(null)
const playing = ref(false)
const duration = ref(0)
const currentTime = ref(0)
const progress = ref(0)

let animFrame = 0

function formatTime(sec: number) {
  if (!sec || !isFinite(sec)) return '0:00'
  const m = Math.floor(sec / 60)
  const s = Math.floor(sec % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}

function togglePlay() {
  if (!audio.value) return
  if (playing.value) {
    audio.value.pause()
  } else {
    audio.value.play()
  }
}

function onPlay() {
  playing.value = true
  tick()
}

function onPause() {
  playing.value = false
  cancelAnimationFrame(animFrame)
}

function onEnded() {
  playing.value = false
  currentTime.value = 0
  progress.value = 0
  cancelAnimationFrame(animFrame)
}

function onLoadedMetadata() {
  if (audio.value) {
    duration.value = audio.value.duration
  }
}

function tick() {
  if (!audio.value) return
  currentTime.value = audio.value.currentTime
  progress.value = duration.value ? audio.value.currentTime / duration.value : 0
  if (playing.value) {
    animFrame = requestAnimationFrame(tick)
  }
}

onMounted(() => {
  if (audio.value) {
    audio.value.addEventListener('loadedmetadata', onLoadedMetadata)
  }
})

onUnmounted(() => {
  cancelAnimationFrame(animFrame)
  if (audio.value) {
    audio.value.pause()
    audio.value.removeEventListener('loadedmetadata', onLoadedMetadata)
  }
})
</script>

<template>
  <div
    class="voice-bar"
    :class="isUser ? 'voice-bar-user' : 'voice-bar-assistant'"
    @click="togglePlay"
  >
    <!-- Play/Pause icon -->
    <div class="voice-icon">
      <svg v-if="!playing" class="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
        <path d="M8 5v14l11-7z" />
      </svg>
      <svg v-else class="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
        <path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z" />
      </svg>
    </div>

    <!-- Waveform bars -->
    <div class="voice-wave">
      <div
        v-for="i in 16"
        :key="i"
        class="wave-bar"
        :class="{ 'wave-bar-active': playing }"
        :style="{
          animationDelay: playing ? `${i * 0.06}s` : '0s',
          height: playing ? undefined : `${6 + Math.sin(i * 0.8) * 4}px`,
          opacity: progress > 0 && (i / 16) <= progress ? 1 : 0.4,
        }"
      />
    </div>

    <!-- Duration -->
    <span class="voice-duration">{{ formatTime(duration) }}</span>

    <!-- Hidden audio element -->
    <audio
      ref="audio"
      :src="src"
      preload="metadata"
      @play="onPlay"
      @pause="onPause"
      @ended="onEnded"
    />
  </div>
</template>

<style scoped>
.voice-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 16px;
  cursor: pointer;
  user-select: none;
  min-width: 140px;
  max-width: 220px;
  transition: background-color 0.15s;
}

.voice-bar-user {
  background: #95ec69;
  flex-direction: row-reverse;
}

.voice-bar-assistant {
  background: #f0f0f0;
}

.voice-bar:hover {
  filter: brightness(0.95);
}

.voice-icon {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.voice-bar-user .voice-icon {
  color: #2d7d2d;
}

.voice-bar-assistant .voice-icon {
  color: #666;
}

.voice-wave {
  display: flex;
  align-items: center;
  gap: 2px;
  height: 20px;
  flex: 1;
}

.wave-bar {
  width: 3px;
  border-radius: 2px;
  transition: height 0.15s, opacity 0.15s;
  height: 6px;
}

.voice-bar-user .wave-bar {
  background: #2d7d2d;
}

.voice-bar-assistant .wave-bar {
  background: #999;
}

.wave-bar-active {
  animation: wave-bounce 0.8s ease-in-out infinite alternate;
}

@keyframes wave-bounce {
  0% { height: 4px; }
  50% { height: 16px; }
  100% { height: 6px; }
}

.voice-duration {
  font-size: 11px;
  flex-shrink: 0;
  min-width: 28px;
}

.voice-bar-user .voice-duration {
  color: #2d7d2d;
}

.voice-bar-assistant .voice-duration {
  color: #999;
}
</style>
