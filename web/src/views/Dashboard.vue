<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useCharacterStore } from '../stores/characters'

const router = useRouter()
const store = useCharacterStore()

onMounted(() => store.fetchCharacters())
</script>

<template>
  <div>
    <h2 class="text-2xl font-bold mb-6">Dashboard</h2>

    <div v-if="store.characters.length === 0" class="text-center py-16">
      <p class="text-gray-500 text-lg mb-4">No companions yet</p>
      <button @click="router.push('/characters')"
        class="bg-purple-600 text-white px-6 py-2 rounded-lg hover:bg-purple-700">
        Create Your First Companion
      </button>
    </div>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <div v-for="char in store.characters" :key="char.id"
        class="bg-white rounded-xl shadow-sm border p-4 hover:shadow-md transition-shadow cursor-pointer"
        @click="router.push(`/chat/${char.id}`)">
        <div class="flex items-center gap-3 mb-3">
          <div class="w-12 h-12 rounded-full bg-purple-100 flex items-center justify-center overflow-hidden">
            <img v-if="char.base_image_url" :src="char.base_image_url" class="w-full h-full object-cover" />
            <span v-else class="text-purple-600 text-lg font-bold">{{ char.name[0] }}</span>
          </div>
          <div>
            <h3 class="font-semibold">{{ char.name }}</h3>
            <p class="text-xs text-gray-400">Mood: {{ char.mood_default }}</p>
          </div>
        </div>
        <p class="text-sm text-gray-600 line-clamp-2">{{ char.personality }}</p>
        <div class="flex gap-2 mt-3">
          <button @click.stop="router.push(`/memories/${char.id}`)"
            class="text-xs text-purple-600 hover:underline">Memories</button>
          <button @click.stop="router.push(`/characters/${char.id}`)"
            class="text-xs text-gray-500 hover:underline">Edit</button>
        </div>
      </div>
    </div>
  </div>
</template>
