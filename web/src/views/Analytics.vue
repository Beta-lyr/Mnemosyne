<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useCharacterStore } from '../stores/characters'
import type { Character } from '../stores/characters'
import axios from 'axios'

const route = useRoute()
const router = useRouter()
const charStore = useCharacterStore()

const character = ref<Character | null>(null)
const loading = ref(true)
const analytics = ref<any>(null)


onMounted(async () => {
  const id = route.params.id as string
  if (charStore.characters.length === 0) await charStore.fetchCharacters()
  character.value = charStore.characters.find((c) => c.id === id) || null
  try {
    const { data } = await axios.get(`/api/chat/${id}/analytics`)
    analytics.value = data
  } catch (e) {
    console.error('Failed to fetch analytics:', e)
  }
  loading.value = false
})

// Draw line chart for messages by day
function drawLineChart(canvas: HTMLCanvasElement) {
  if (!analytics.value?.messages_by_day?.length) return
  const ctx = canvas.getContext('2d')!
  const data = analytics.value.messages_by_day
  const w = canvas.width
  const h = canvas.height
  const padding = { top: 20, right: 20, bottom: 40, left: 40 }

  ctx.clearRect(0, 0, w, h)

  const maxVal = Math.max(...data.map((d: any) => d.count), 1)
  const chartW = w - padding.left - padding.right
  const chartH = h - padding.top - padding.bottom

  // Grid lines
  ctx.strokeStyle = '#e5e7eb'
  ctx.lineWidth = 0.5
  for (let i = 0; i <= 4; i++) {
    const y = padding.top + (chartH / 4) * i
    ctx.beginPath()
    ctx.moveTo(padding.left, y)
    ctx.lineTo(w - padding.right, y)
    ctx.stroke()

    ctx.fillStyle = '#9ca3af'
    ctx.font = '10px sans-serif'
    ctx.textAlign = 'right'
    ctx.fillText(String(Math.round(maxVal - (maxVal / 4) * i)), padding.left - 5, y + 3)
  }

  // Line
  ctx.beginPath()
  ctx.strokeStyle = '#ec4899'
  ctx.lineWidth = 2
  data.forEach((d: any, i: number) => {
    const x = padding.left + (chartW / (data.length - 1 || 1)) * i
    const y = padding.top + chartH - (d.count / maxVal) * chartH
    if (i === 0) ctx.moveTo(x, y)
    else ctx.lineTo(x, y)
  })
  ctx.stroke()

  // Fill
  ctx.lineTo(padding.left + chartW, padding.top + chartH)
  ctx.lineTo(padding.left, padding.top + chartH)
  ctx.closePath()
  ctx.fillStyle = 'rgba(236, 72, 153, 0.1)'
  ctx.fill()

  // Dots
  data.forEach((d: any, i: number) => {
    const x = padding.left + (chartW / (data.length - 1 || 1)) * i
    const y = padding.top + chartH - (d.count / maxVal) * chartH
    ctx.beginPath()
    ctx.arc(x, y, 3, 0, Math.PI * 2)
    ctx.fillStyle = '#ec4899'
    ctx.fill()
  })

  // X labels
  ctx.fillStyle = '#9ca3af'
  ctx.font = '10px sans-serif'
  ctx.textAlign = 'center'
  const step = Math.max(1, Math.floor(data.length / 7))
  data.forEach((d: any, i: number) => {
    if (i % step === 0 || i === data.length - 1) {
      const x = padding.left + (chartW / (data.length - 1 || 1)) * i
      const label = d.date.slice(5) // MM-DD
      ctx.fillText(label, x, h - padding.bottom + 15)
    }
  })
}

// Draw bar chart for memory types
function drawBarChart(canvas: HTMLCanvasElement, byType: Record<string, { count: number }>) {
  const ctx = canvas.getContext('2d')!
  const entries = Object.entries(byType)
  if (entries.length === 0) return

  const w = canvas.width
  const h = canvas.height
  const padding = { top: 20, right: 20, bottom: 40, left: 40 }
  const chartW = w - padding.left - padding.right
  const chartH = h - padding.top - padding.bottom
  const maxVal = Math.max(...entries.map(([_, v]) => v.count), 1)
  const barW = Math.min(60, chartW / entries.length - 10)

  ctx.clearRect(0, 0, w, h)

  const barColors: Record<string, string> = {
    fact: '#3b82f6',
    feeling: '#f59e0b',
    event: '#10b981',
  }

  entries.forEach(([type, data], i) => {
    const x = padding.left + (chartW / entries.length) * i + (chartW / entries.length - barW) / 2
    const barH = (data.count / maxVal) * chartH
    const y = padding.top + chartH - barH

    ctx.fillStyle = barColors[type] || '#94a3b8'
    ctx.beginPath()
    ctx.roundRect(x, y, barW, barH, [4, 4, 0, 0])
    ctx.fill()

    // Label
    ctx.fillStyle = '#6b7280'
    ctx.font = '11px sans-serif'
    ctx.textAlign = 'center'
    ctx.fillText(type, x + barW / 2, h - padding.bottom + 15)

    // Value
    ctx.fillStyle = '#374151'
    ctx.font = 'bold 11px sans-serif'
    ctx.fillText(String(data.count), x + barW / 2, y - 5)
  })
}
</script>

<template>
  <div class="animate-fade-in">
    <!-- Header -->
    <div class="flex items-center gap-3 mb-8">
      <button @click="router.push('/')" class="btn-ghost p-2 rounded-xl">
        <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
        </svg>
      </button>
      <div>
        <h2 class="text-2xl font-display font-bold text-gray-800">Analytics</h2>
        <p class="text-sm text-gray-500">{{ character?.name }}'s conversation insights</p>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
      <div v-for="i in 4" :key="i" class="card p-5">
        <div class="h-3 w-20 skeleton mb-2"></div>
        <div class="h-8 w-16 skeleton"></div>
      </div>
    </div>

    <div v-else-if="analytics" class="space-y-6">
      <!-- Stat Cards -->
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div class="card p-5">
          <p class="text-xs text-gray-500 mb-1">Total Messages</p>
          <p class="text-2xl font-display font-bold text-gray-800">{{ analytics.total_messages }}</p>
        </div>
        <div class="card p-5">
          <p class="text-xs text-gray-500 mb-1">Total Memories</p>
          <p class="text-2xl font-display font-bold text-gray-800">{{ analytics.memory_stats?.total || 0 }}</p>
        </div>
        <div class="card p-5">
          <p class="text-xs text-gray-500 mb-1">Images Generated</p>
          <p class="text-2xl font-display font-bold text-gray-800">{{ analytics.media_stats?.images || 0 }}</p>
        </div>
        <div class="card p-5">
          <p class="text-xs text-gray-500 mb-1">Audio/Video</p>
          <p class="text-2xl font-display font-bold text-gray-800">
            {{ (analytics.media_stats?.audio || 0) + (analytics.media_stats?.video || 0) }}
          </p>
        </div>
      </div>

      <!-- Message Trend -->
      <div class="card p-5">
        <h3 class="font-display font-bold text-gray-800 mb-4">Message Trend (Last 30 Days)</h3>
        <div v-if="analytics.messages_by_day?.length" class="h-[200px]">
          <canvas
            :ref="(el) => { if (el) drawLineChart(el as HTMLCanvasElement) }"
            width="800"
            height="200"
            class="w-full h-full"
          />
        </div>
        <p v-else class="text-sm text-gray-400 text-center py-8">No message data yet</p>
      </div>

      <!-- Memory Distribution -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div class="card p-5">
          <h3 class="font-display font-bold text-gray-800 mb-4">Memory Types</h3>
          <div v-if="analytics.memory_stats?.by_type && Object.keys(analytics.memory_stats.by_type).length" class="h-[200px]">
            <canvas
              :ref="(el) => { if (el) drawBarChart(el as HTMLCanvasElement, analytics.memory_stats.by_type) }"
              width="400"
              height="200"
              class="w-full h-full"
            />
          </div>
          <p v-else class="text-sm text-gray-400 text-center py-8">No memories yet</p>
        </div>

        <div class="card p-5">
          <h3 class="font-display font-bold text-gray-800 mb-4">Memory Importance</h3>
          <div v-if="analytics.memory_stats?.by_type" class="space-y-3">
            <div v-for="(data, type) in analytics.memory_stats.by_type" :key="String(type)" class="flex items-center gap-3">
              <span class="badge text-xs" :class="{
                'bg-blue-100 text-blue-700': String(type) === 'fact',
                'bg-amber-100 text-amber-700': String(type) === 'feeling',
                'bg-emerald-100 text-emerald-700': String(type) === 'event',
              }">{{ type }}</span>
              <div class="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                <div class="h-full rounded-full" :class="{
                  'bg-blue-500': String(type) === 'fact',
                  'bg-amber-500': String(type) === 'feeling',
                  'bg-emerald-500': String(type) === 'event',
                }" :style="{ width: `${(data.avg_importance || 0) * 100}%` }"></div>
              </div>
              <span class="text-xs text-gray-500 w-10 text-right">{{ ((data.avg_importance || 0) * 100).toFixed(0) }}%</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
