<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

defineProps<{
  src: string
  alt?: string
}>()

const emit = defineEmits<{ close: [] }>()

const scale = ref(1)
const translateX = ref(0)
const translateY = ref(0)
const isDragging = ref(false)
let lastX = 0
let lastY = 0
let lastPinchDist = 0

function handleWheel(e: WheelEvent) {
  e.preventDefault()
  const delta = e.deltaY > 0 ? -0.1 : 0.1
  scale.value = Math.max(0.5, Math.min(5, scale.value + delta))
  if (scale.value <= 1) {
    translateX.value = 0
    translateY.value = 0
  }
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape') emit('close')
}

function handleMouseDown(e: MouseEvent) {
  if (scale.value <= 1) return
  isDragging.value = true
  lastX = e.clientX
  lastY = e.clientY
}

function handleMouseMove(e: MouseEvent) {
  if (!isDragging.value) return
  translateX.value += e.clientX - lastX
  translateY.value += e.clientY - lastY
  lastX = e.clientX
  lastY = e.clientY
}

function handleMouseUp() {
  isDragging.value = false
}

function handleTouchStart(e: TouchEvent) {
  if (e.touches.length === 2) {
    const dx = e.touches[0].clientX - e.touches[1].clientX
    const dy = e.touches[0].clientY - e.touches[1].clientY
    lastPinchDist = Math.sqrt(dx * dx + dy * dy)
  } else if (e.touches.length === 1 && scale.value > 1) {
    isDragging.value = true
    lastX = e.touches[0].clientX
    lastY = e.touches[0].clientY
  }
}

function handleTouchMove(e: TouchEvent) {
  if (e.touches.length === 2) {
    e.preventDefault()
    const dx = e.touches[0].clientX - e.touches[1].clientX
    const dy = e.touches[0].clientY - e.touches[1].clientY
    const dist = Math.sqrt(dx * dx + dy * dy)
    if (lastPinchDist > 0) {
      const delta = (dist - lastPinchDist) * 0.005
      scale.value = Math.max(0.5, Math.min(5, scale.value + delta))
    }
    lastPinchDist = dist
  } else if (e.touches.length === 1 && isDragging.value) {
    translateX.value += e.touches[0].clientX - lastX
    translateY.value += e.touches[0].clientY - lastY
    lastX = e.touches[0].clientX
    lastY = e.touches[0].clientY
  }
}

function handleTouchEnd() {
  isDragging.value = false
  lastPinchDist = 0
}

function handleBackdropClick(e: MouseEvent) {
  if ((e.target as HTMLElement).classList.contains('lightbox-backdrop')) {
    emit('close')
  }
}

function resetTransform() {
  scale.value = 1
  translateX.value = 0
  translateY.value = 0
}

onMounted(() => {
  document.addEventListener('keydown', handleKeydown)
  document.body.style.overflow = 'hidden'
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeydown)
  document.body.style.overflow = ''
})
</script>

<template>
  <Teleport to="body">
    <transition name="lightbox">
      <div
        class="lightbox-backdrop fixed inset-0 z-[9999] bg-black/80 backdrop-blur-sm flex items-center justify-center"
        @click="handleBackdropClick"
        @wheel.prevent="handleWheel"
        @mousedown="handleMouseDown"
        @mousemove="handleMouseMove"
        @mouseup="handleMouseUp"
        @mouseleave="handleMouseUp"
        @touchstart="handleTouchStart"
        @touchmove="handleTouchMove"
        @touchend="handleTouchEnd"
      >
        <!-- Close button -->
        <button
          @click="emit('close')"
          class="absolute top-4 right-4 z-10 w-10 h-10 rounded-full bg-white/10 hover:bg-white/20 flex items-center justify-center text-white transition-colors"
          aria-label="Close"
        >
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>

        <!-- Reset button -->
        <button
          v-if="scale !== 1"
          @click="resetTransform"
          class="absolute bottom-4 right-4 z-10 px-3 py-1.5 rounded-full bg-white/10 hover:bg-white/20 text-white text-sm transition-colors"
        >
          Reset
        </button>

        <!-- Zoom indicator -->
        <div v-if="scale !== 1" class="absolute top-4 left-4 z-10 px-3 py-1.5 rounded-full bg-white/10 text-white text-sm">
          {{ Math.round(scale * 100) }}%
        </div>

        <img
          :src="src"
          :alt="alt || ''"
          class="max-w-[90vw] max-h-[90vh] object-contain select-none"
          :style="{
            transform: `scale(${scale}) translate(${translateX / scale}px, ${translateY / scale}px)`,
            cursor: scale > 1 ? (isDragging ? 'grabbing' : 'grab') : 'zoom-in',
            transition: isDragging ? 'none' : 'transform 0.2s ease-out',
          }"
          @dblclick="scale > 1 ? resetTransform() : scale = 2"
          draggable="false"
        />
      </div>
    </transition>
  </Teleport>
</template>

<style scoped>
.lightbox-enter-active,
.lightbox-leave-active {
  transition: opacity 0.2s ease;
}
.lightbox-enter-from,
.lightbox-leave-to {
  opacity: 0;
}
</style>
