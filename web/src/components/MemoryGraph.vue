<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import axios from 'axios'

const props = defineProps<{
  characterId: string
}>()

interface GraphNode {
  id: string
  type: string
  content: string
  importance: number
  created_at: string | null
  x: number
  y: number
  vx: number
  vy: number
}

interface GraphEdge {
  source: string
  target: string
  similarity: number
}

const canvas = ref<HTMLCanvasElement | null>(null)
const nodes = ref<GraphNode[]>([])
const edges = ref<GraphEdge[]>([])
const loading = ref(true)
const hoveredNode = ref<GraphNode | null>(null)
const tooltipPos = ref({ x: 0, y: 0 })

// Drag state
let dragNode: GraphNode | null = null
let isPanning = false
let panStart = { x: 0, y: 0 }
let offset = { x: 0, y: 0 }
let scale = 1

// Colors by type
const typeColors: Record<string, string> = {
  fact: '#3b82f6',    // blue
  feeling: '#f59e0b', // amber
  event: '#10b981',   // emerald
}

let animFrame: number | null = null

onMounted(async () => {
  await fetchGraph()
  if (nodes.value.length > 0) {
    initPositions()
    startSimulation()
  }
})

onUnmounted(() => {
  if (animFrame) cancelAnimationFrame(animFrame)
})

async function fetchGraph() {
  loading.value = true
  try {
    const { data } = await axios.get(`/api/memories/${props.characterId}/graph`)
    nodes.value = data.nodes.map((n: any) => ({
      ...n,
      x: 0, y: 0, vx: 0, vy: 0,
    }))
    edges.value = data.edges
  } catch (e) {
    console.error('Failed to fetch memory graph:', e)
  } finally {
    loading.value = false
  }
}

function initPositions() {
  const el = canvas.value
  if (!el) return
  const cx = el.width / 2
  const cy = el.height / 2
  const r = Math.min(cx, cy) * 0.6
  nodes.value.forEach((n, i) => {
    const angle = (2 * Math.PI * i) / nodes.value.length
    n.x = cx + r * Math.cos(angle)
    n.y = cy + r * Math.sin(angle)
  })
}

function startSimulation() {
  const el = canvas.value
  if (!el) return

  const ctx = el.getContext('2d')!
  const REPULSION = 5000
  const ATTRACTION = 0.005
  const DAMPING = 0.85
  const CENTER_GRAVITY = 0.01

  function tick() {
    const w = el!.width
    const h = el!.height
    const cx = w / 2
    const cy = h / 2

    // Repulsion between all nodes
    for (let i = 0; i < nodes.value.length; i++) {
      for (let j = i + 1; j < nodes.value.length; j++) {
        const a = nodes.value[i]
        const b = nodes.value[j]
        let dx = a.x - b.x
        let dy = a.y - b.y
        let dist = Math.sqrt(dx * dx + dy * dy) || 1
        let force = REPULSION / (dist * dist)
        let fx = (dx / dist) * force
        let fy = (dy / dist) * force
        a.vx += fx; a.vy += fy
        b.vx -= fx; b.vy -= fy
      }
    }

    // Attraction along edges
    const nodeMap = new Map(nodes.value.map(n => [n.id, n]))
    for (const edge of edges.value) {
      const a = nodeMap.get(edge.source)
      const b = nodeMap.get(edge.target)
      if (!a || !b) continue
      let dx = b.x - a.x
      let dy = b.y - a.y
      let dist = Math.sqrt(dx * dx + dy * dy) || 1
      let force = ATTRACTION * dist * edge.similarity
      let fx = (dx / dist) * force
      let fy = (dy / dist) * force
      a.vx += fx; a.vy += fy
      b.vx -= fx; b.vy -= fy
    }

    // Center gravity + damping + position update
    for (const n of nodes.value) {
      if (n === dragNode) continue
      n.vx += (cx - n.x) * CENTER_GRAVITY
      n.vy += (cy - n.y) * CENTER_GRAVITY
      n.vx *= DAMPING
      n.vy *= DAMPING
      n.x += n.vx
      n.y += n.vy
      // Bounds
      n.x = Math.max(20, Math.min(w - 20, n.x))
      n.y = Math.max(20, Math.min(h - 20, n.y))
    }

    draw(ctx, w, h)
    animFrame = requestAnimationFrame(tick)
  }

  tick()
}

function draw(ctx: CanvasRenderingContext2D, w: number, h: number) {
  ctx.clearRect(0, 0, w, h)
  ctx.save()
  ctx.translate(offset.x, offset.y)
  ctx.scale(scale, scale)

  // Draw edges
  const nodeMap = new Map(nodes.value.map(n => [n.id, n]))
  for (const edge of edges.value) {
    const a = nodeMap.get(edge.source)
    const b = nodeMap.get(edge.target)
    if (!a || !b) continue
    ctx.beginPath()
    ctx.moveTo(a.x, a.y)
    ctx.lineTo(b.x, b.y)
    ctx.strokeStyle = `rgba(148, 163, 184, ${edge.similarity * 0.5})`
    ctx.lineWidth = edge.similarity * 2
    ctx.stroke()
  }

  // Draw nodes
  for (const n of nodes.value) {
    const r = Math.max(8, n.importance * 20)
    const color = typeColors[n.type] || '#94a3b8'

    ctx.beginPath()
    ctx.arc(n.x, n.y, r, 0, Math.PI * 2)
    ctx.fillStyle = color
    ctx.globalAlpha = n === hoveredNode.value ? 1.0 : 0.8
    ctx.fill()
    ctx.globalAlpha = 1.0

    if (n === hoveredNode.value) {
      ctx.strokeStyle = '#1e293b'
      ctx.lineWidth = 2
      ctx.stroke()
    }
  }

  ctx.restore()
}

function getMousePos(e: MouseEvent): { x: number, y: number } {
  const rect = canvas.value!.getBoundingClientRect()
  return {
    x: (e.clientX - rect.left - offset.x) / scale,
    y: (e.clientY - rect.top - offset.y) / scale,
  }
}

function findNodeAt(mx: number, my: number): GraphNode | null {
  for (const n of nodes.value) {
    const r = Math.max(8, n.importance * 20)
    const dx = n.x - mx
    const dy = n.y - my
    if (dx * dx + dy * dy <= r * r) return n
  }
  return null
}

function handleMouseDown(e: MouseEvent) {
  const pos = getMousePos(e)
  const node = findNodeAt(pos.x, pos.y)
  if (node) {
    dragNode = node
  } else {
    isPanning = true
    panStart = { x: e.clientX - offset.x, y: e.clientY - offset.y }
  }
}

function handleMouseMove(e: MouseEvent) {
  if (dragNode) {
    const pos = getMousePos(e)
    dragNode.x = pos.x
    dragNode.y = pos.y
    dragNode.vx = 0
    dragNode.vy = 0
  } else if (isPanning) {
    offset.x = e.clientX - panStart.x
    offset.y = e.clientY - panStart.y
  } else {
    const pos = getMousePos(e)
    const node = findNodeAt(pos.x, pos.y)
    hoveredNode.value = node
    if (node && canvas.value) {
      tooltipPos.value = { x: e.clientX, y: e.clientY }
    }
  }
}

function handleMouseUp() {
  dragNode = null
  isPanning = false
}

function handleWheel(e: WheelEvent) {
  e.preventDefault()
  const delta = e.deltaY > 0 ? -0.1 : 0.1
  scale = Math.max(0.3, Math.min(3, scale + delta))
}

function resizeCanvas() {
  const el = canvas.value
  if (!el) return
  const parent = el.parentElement
  if (!parent) return
  el.width = parent.clientWidth
  el.height = parent.clientHeight
}

watch(canvas, () => {
  if (canvas.value) {
    nextTick(resizeCanvas)
    window.addEventListener('resize', resizeCanvas)
  }
})

onUnmounted(() => {
  window.removeEventListener('resize', resizeCanvas)
})

const typeLabels: Record<string, string> = { fact: 'Fact', feeling: 'Feeling', event: 'Event' }
</script>

<template>
  <div class="relative w-full h-[500px] bg-gray-50 rounded-2xl overflow-hidden border border-gray-100">
    <!-- Loading -->
    <div v-if="loading" class="absolute inset-0 flex items-center justify-center">
      <div class="flex items-center gap-2 text-gray-400">
        <svg class="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
        </svg>
        Loading graph...
      </div>
    </div>

    <!-- Empty -->
    <div v-else-if="nodes.length === 0" class="absolute inset-0 flex items-center justify-center text-gray-400 text-sm">
      No memories to visualize yet
    </div>

    <!-- Canvas -->
    <canvas
      v-else
      ref="canvas"
      class="w-full h-full cursor-grab active:cursor-grabbing"
      @mousedown="handleMouseDown"
      @mousemove="handleMouseMove"
      @mouseup="handleMouseUp"
      @mouseleave="handleMouseUp"
      @wheel.prevent="handleWheel"
    />

    <!-- Legend -->
    <div v-if="nodes.length > 0" class="absolute bottom-3 left-3 flex items-center gap-3 bg-white/80 backdrop-blur-sm rounded-lg px-3 py-1.5 text-xs">
      <span class="flex items-center gap-1">
        <span class="w-2.5 h-2.5 rounded-full bg-blue-500"></span> Fact
      </span>
      <span class="flex items-center gap-1">
        <span class="w-2.5 h-2.5 rounded-full bg-amber-500"></span> Feeling
      </span>
      <span class="flex items-center gap-1">
        <span class="w-2.5 h-2.5 rounded-full bg-emerald-500"></span> Event
      </span>
    </div>

    <!-- Node count -->
    <div v-if="nodes.length > 0" class="absolute top-3 right-3 bg-white/80 backdrop-blur-sm rounded-lg px-3 py-1.5 text-xs text-gray-500">
      {{ nodes.length }} memories
    </div>

    <!-- Tooltip -->
    <Teleport to="body">
      <div
        v-if="hoveredNode"
        class="fixed z-[9999] bg-gray-800 text-white text-xs rounded-lg px-3 py-2 max-w-[250px] pointer-events-none shadow-lg"
        :style="{ left: tooltipPos.x + 12 + 'px', top: tooltipPos.y - 8 + 'px' }"
      >
        <div class="flex items-center gap-1.5 mb-1">
          <span class="badge text-[10px]" :style="{ backgroundColor: typeColors[hoveredNode.type] || '#94a3b8', color: 'white' }">
            {{ typeLabels[hoveredNode.type] || hoveredNode.type }}
          </span>
          <span class="text-gray-400">importance: {{ hoveredNode.importance.toFixed(2) }}</span>
        </div>
        <p class="leading-relaxed">{{ hoveredNode.content }}</p>
      </div>
    </Teleport>
  </div>
</template>
