<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useCharacterStore } from '../stores/characters'

const router = useRouter()
const store = useCharacterStore()

onMounted(() => store.fetchCharacters())

function greeting(): string {
  const h = new Date().getHours()
  if (h < 12) return 'Good morning'
  if (h < 18) return 'Good afternoon'
  return 'Good evening'
}
</script>

<template>
  <div class="min-h-screen px-4 py-8 md:px-8 lg:px-12">

    <!-- Welcome header -->
    <header class="mb-10 animate-fade-in">
      <h1 class="text-3xl md:text-4xl font-display font-bold text-gray-900">
        {{ greeting() }}, welcome back!
      </h1>
      <p class="mt-2 text-gray-500 text-lg">
        Your companions are waiting for you.
      </p>
    </header>

    <!-- Loading skeleton -->
    <div
      v-if="store.loading"
      class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
    >
      <div
        v-for="i in 6"
        :key="i"
        class="card p-6"
      >
        <div class="flex items-center gap-4 mb-4">
          <div class="skeleton w-16 h-16 rounded-full" />
          <div class="flex-1 space-y-2">
            <div class="skeleton h-5 w-28" />
            <div class="skeleton h-4 w-20" />
          </div>
        </div>
        <div class="space-y-2 mb-4">
          <div class="skeleton h-3.5 w-full" />
          <div class="skeleton h-3.5 w-3/4" />
        </div>
        <div class="flex gap-3 pt-3 border-t border-gray-100">
          <div class="skeleton h-8 w-24 rounded-lg" />
          <div class="skeleton h-8 w-20 rounded-lg" />
        </div>
      </div>
    </div>

    <!-- Empty state -->
    <div
      v-else-if="store.characters.length === 0"
      class="card max-w-lg mx-auto mt-16 p-10 text-center animate-slide-up"
    >
      <!-- illustration-style icon -->
      <div
        class="mx-auto mb-6 w-24 h-24 rounded-full bg-gradient-to-br from-primary-100 to-accent-100
               flex items-center justify-center"
      >
        <svg
          class="w-12 h-12 text-accent"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          stroke-width="1.5"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            d="M15.182 15.182a4.5 4.5 0 01-6.364 0M21 12a9 9 0 11-18 0 9 9 0 0118 0zM9.75 9.75c0 .414-.168.75-.375.75S9 10.164 9 9.75 9.168 9 9.375 9s.375.336.375.75zm-.375 0h.008v.015h-.008V9.75zm5.625 0c0 .414-.168.75-.375.75s-.375-.336-.375-.75.168-.75.375-.75.375.336.375.75zm-.375 0h.008v.015h-.008V9.75z"
          />
        </svg>
      </div>
      <h2 class="font-display text-xl font-bold text-gray-800 mb-2">
        No companions yet
      </h2>
      <p class="text-gray-500 mb-8">
        Create your first AI companion and start a conversation that feels real.
      </p>
      <button
        class="btn-primary text-base px-8 py-3"
        @click="router.push('/characters')"
      >
        Create Your First Companion
      </button>
    </div>

    <!-- Character grid -->
    <div
      v-else
      class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
    >
      <div
        v-for="(char, index) in store.characters"
        :key="char.id"
        class="card group p-6 cursor-pointer animate-slide-up"
        :style="{ animationDelay: `${index * 80}ms`, animationFillMode: 'backwards' }"
        @click="router.push(`/chat/${char.id}`)"
      >
        <!-- Top: avatar + name + mood -->
        <div class="flex items-center gap-4 mb-4">
          <div
            class="w-16 h-16 rounded-full overflow-hidden ring-2 ring-accent-100
                   bg-gradient-to-br from-accent-50 to-primary-50
                   flex items-center justify-center shrink-0
                   group-hover:ring-accent-300 transition-all duration-200"
          >
            <img
              v-if="char.base_image_url"
              :src="char.base_image_url"
              :alt="char.name"
              class="w-full h-full object-cover"
            />
            <span
              v-else
              class="text-accent text-2xl font-bold font-display"
            >
              {{ char.name[0] }}
            </span>
          </div>
          <div class="min-w-0 flex-1">
            <h3 class="font-display text-lg font-bold text-gray-900 truncate">
              {{ char.name }}
            </h3>
            <span class="badge-primary mt-1">
              {{ char.mood_default }}
            </span>
          </div>
        </div>

        <!-- Personality preview -->
        <p class="text-sm text-gray-500 leading-relaxed line-clamp-2 mb-5">
          {{ char.personality }}
        </p>

        <!-- Action buttons -->
        <div class="flex gap-3 pt-4 border-t border-gray-100">
          <button
            class="btn-secondary text-xs px-4 py-2 flex-1"
            @click.stop="router.push(`/memories/${char.id}`)"
          >
            Memories
          </button>
          <button
            class="btn-outline text-xs px-4 py-2 flex-1"
            @click.stop="router.push(`/characters/${char.id}`)"
          >
            Edit
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
