<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()

const isRegister = ref(false)
const username = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function handleSubmit() {
  error.value = ''
  loading.value = true
  try {
    if (isRegister.value) {
      await axios.post('/api/auth/register', {
        username: username.value,
        password: password.value,
      })
    }
    const { data } = await axios.post('/api/auth/login', new URLSearchParams({
      username: username.value,
      password: password.value,
    }))
    auth.setAuth(data.access_token, username.value)
    router.push('/')
  } catch (e: any) {
    error.value = e.response?.data?.detail || 'Authentication failed'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="min-h-screen flex items-center justify-center">
    <div class="bg-white rounded-xl shadow-lg p-8 w-full max-w-md">
      <h1 class="text-2xl font-bold text-center text-purple-600 mb-2">Mnemosyne</h1>
      <p class="text-center text-gray-500 mb-6">Memory-driven virtual companion</p>

      <form @submit.prevent="handleSubmit" class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Username</label>
          <input v-model="username" type="text" required
            class="w-full border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-purple-500" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Password</label>
          <input v-model="password" type="password" required
            class="w-full border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-purple-500" />
        </div>

        <p v-if="error" class="text-red-500 text-sm">{{ error }}</p>

        <button type="submit" :disabled="loading"
          class="w-full bg-purple-600 text-white py-2 rounded-lg hover:bg-purple-700 disabled:opacity-50">
          {{ loading ? 'Loading...' : (isRegister ? 'Register' : 'Login') }}
        </button>
      </form>

      <p class="text-center text-sm text-gray-500 mt-4">
        <button @click="isRegister = !isRegister" class="text-purple-600 hover:underline">
          {{ isRegister ? 'Already have an account? Login' : 'First time? Register' }}
        </button>
      </p>
    </div>
  </div>
</template>
