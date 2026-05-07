<script setup lang="ts">
import { RouterView, useRouter } from 'vue-router'
import { useAuthStore } from './stores/auth'

const auth = useAuthStore()
const router = useRouter()

function handleLogout() {
  auth.logout()
  router.push('/login')
}
</script>

<template>
  <div class="min-h-screen bg-gray-50">
    <nav v-if="auth.isLoggedIn" class="bg-white shadow-sm border-b">
      <div class="max-w-7xl mx-auto px-4 py-3 flex items-center gap-6">
        <h1 class="text-xl font-bold text-purple-600">Mnemosyne</h1>
        <router-link to="/" class="text-gray-600 hover:text-gray-900">Dashboard</router-link>
        <router-link to="/characters" class="text-gray-600 hover:text-gray-900">Characters</router-link>
        <router-link to="/settings" class="text-gray-600 hover:text-gray-900">Settings</router-link>
        <div class="ml-auto flex items-center gap-3">
          <span class="text-sm text-gray-500">{{ auth.username }}</span>
          <button @click="handleLogout" class="text-sm text-red-500 hover:text-red-700">Logout</button>
        </div>
      </div>
    </nav>
    <main :class="auth.isLoggedIn ? 'max-w-7xl mx-auto px-4 py-6' : ''">
      <RouterView />
    </main>
  </div>
</template>
