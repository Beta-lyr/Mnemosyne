<script setup lang="ts">
import { RouterView, useRouter, useRoute } from 'vue-router'
import { ref } from 'vue'
import { useAuthStore } from './stores/auth'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()
const mobileMenuOpen = ref(false)

const navLinks = [
  { path: '/', label: 'Home', icon: 'home' },
  { path: '/characters', label: 'Characters', icon: 'users' },
  { path: '/settings', label: 'Settings', icon: 'gear' },
]

function isActive(path: string) {
  if (path === '/') return route.path === '/'
  return route.path.startsWith(path)
}

function handleLogout() {
  auth.logout()
  router.push('/login')
  mobileMenuOpen.value = false
}

// Simple toast system
const toasts = ref<{ id: number; message: string; type: string }[]>([])
let toastId = 0

function showToast(message: string, type = 'info') {
  const id = ++toastId
  toasts.value.push({ id, message, type })
  setTimeout(() => {
    toasts.value = toasts.value.filter(t => t.id !== id)
  }, 3500)
}

// Expose toast globally
;(window as any).__showToast = showToast
</script>

<template>
  <div class="min-h-screen bg-surface-secondary">
    <!-- Navigation -->
    <nav v-if="auth.isLoggedIn" class="bg-white/80 backdrop-blur-lg border-b border-gray-100 sticky top-0 z-50">
      <div class="max-w-7xl mx-auto px-4 sm:px-6">
        <div class="flex items-center justify-between h-16">
          <!-- Brand -->
          <router-link to="/" class="flex items-center gap-2.5 group">
            <div class="w-8 h-8 rounded-xl bg-gradient-to-br from-primary to-accent flex items-center justify-center">
              <svg class="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
              </svg>
            </div>
            <span class="text-lg font-display font-bold text-gray-800 group-hover:text-primary transition-colors">Mnemosyne</span>
          </router-link>

          <!-- Desktop Nav -->
          <div class="hidden md:flex items-center gap-1">
            <router-link
              v-for="link in navLinks"
              :key="link.path"
              :to="link.path"
              class="relative px-4 py-2 rounded-xl text-sm font-medium transition-all duration-200"
              :class="isActive(link.path)
                ? 'text-primary bg-primary-50'
                : 'text-gray-500 hover:text-gray-800 hover:bg-gray-50'"
            >
              {{ link.label }}
            </router-link>
          </div>

          <!-- Right side -->
          <div class="hidden md:flex items-center gap-3">
            <div class="flex items-center gap-2 px-3 py-1.5 rounded-full bg-gray-50">
              <div class="w-6 h-6 rounded-full bg-gradient-to-br from-accent-300 to-accent-500 flex items-center justify-center">
                <span class="text-xs text-white font-bold">{{ auth.username?.[0]?.toUpperCase() }}</span>
              </div>
              <span class="text-sm text-gray-600 font-medium">{{ auth.username }}</span>
            </div>
            <button @click="handleLogout" class="btn-ghost text-sm text-gray-400 hover:text-red-500">
              <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
              </svg>
            </button>
          </div>

          <!-- Mobile menu button -->
          <button @click="mobileMenuOpen = !mobileMenuOpen" class="md:hidden p-2 rounded-xl hover:bg-gray-100 transition-colors">
            <svg v-if="!mobileMenuOpen" class="w-6 h-6 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M4 6h16M4 12h16M4 18h16" />
            </svg>
            <svg v-else class="w-6 h-6 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>

      <!-- Mobile menu -->
      <transition
        enter-active-class="transition duration-200 ease-out"
        enter-from-class="opacity-0 -translate-y-2"
        enter-to-class="opacity-100 translate-y-0"
        leave-active-class="transition duration-150 ease-in"
        leave-from-class="opacity-100 translate-y-0"
        leave-to-class="opacity-0 -translate-y-2"
      >
        <div v-if="mobileMenuOpen" class="md:hidden border-t border-gray-100 bg-white px-4 py-3 space-y-1">
          <router-link
            v-for="link in navLinks"
            :key="link.path"
            :to="link.path"
            @click="mobileMenuOpen = false"
            class="block px-4 py-2.5 rounded-xl text-sm font-medium transition-colors"
            :class="isActive(link.path)
              ? 'text-primary bg-primary-50'
              : 'text-gray-600 hover:bg-gray-50'"
          >
            {{ link.label }}
          </router-link>
          <div class="border-t border-gray-100 pt-2 mt-2">
            <button @click="handleLogout" class="w-full text-left px-4 py-2.5 rounded-xl text-sm text-red-500 hover:bg-red-50 transition-colors">
              Logout ({{ auth.username }})
            </button>
          </div>
        </div>
      </transition>
    </nav>

    <!-- Main content -->
    <main :class="auth.isLoggedIn ? 'max-w-7xl mx-auto px-4 sm:px-6 py-6' : ''">
      <RouterView />
    </main>

    <!-- Toast notifications -->
    <div class="fixed bottom-6 right-6 z-[100] flex flex-col gap-2">
      <transition-group
        enter-active-class="transition duration-300 ease-out"
        enter-from-class="opacity-0 translate-y-4 scale-95"
        enter-to-class="opacity-100 translate-y-0 scale-100"
        leave-active-class="transition duration-200 ease-in"
        leave-from-class="opacity-100 translate-y-0 scale-100"
        leave-to-class="opacity-0 translate-y-2 scale-95"
      >
        <div
          v-for="toast in toasts"
          :key="toast.id"
          class="px-5 py-3 rounded-xl shadow-modal text-sm font-medium max-w-sm"
          :class="{
            'bg-gray-800 text-white': toast.type === 'info',
            'bg-green-600 text-white': toast.type === 'success',
            'bg-red-500 text-white': toast.type === 'error',
          }"
        >
          {{ toast.message }}
        </div>
      </transition-group>
    </div>
  </div>
</template>
