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
  <div class="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary-50 via-white to-accent-50 px-4 py-8">
    <div class="card w-full max-w-md p-8 animate-slide-up">
      <!-- Brand Logo -->
      <div class="flex flex-col items-center mb-8 animate-fade-in">
        <div class="w-16 h-16 rounded-full bg-gradient-to-br from-primary to-accent flex items-center justify-center shadow-lg mb-4">
          <svg class="w-8 h-8 text-white" fill="currentColor" viewBox="0 0 24 24">
            <path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/>
          </svg>
        </div>
        <h1 class="text-3xl font-display font-bold bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent">
          Mnemosyne
        </h1>
        <p class="text-gray-400 text-sm mt-1">Memory-driven virtual companion</p>
      </div>

      <!-- Form -->
      <form @submit.prevent="handleSubmit" class="space-y-5">
        <div class="animate-slide-up" style="animation-delay: 0.05s">
          <label class="block text-sm font-semibold text-gray-600 mb-1.5">Username</label>
          <input
            v-model="username"
            type="text"
            required
            placeholder="Enter your username"
            class="input"
          />
        </div>
        <div class="animate-slide-up" style="animation-delay: 0.1s">
          <label class="block text-sm font-semibold text-gray-600 mb-1.5">Password</label>
          <input
            v-model="password"
            type="password"
            required
            placeholder="Enter your password"
            class="input"
          />
        </div>

        <!-- Error Message -->
        <transition
          enter-active-class="transition duration-200 ease-out"
          enter-from-class="opacity-0 -translate-y-1"
          enter-to-class="opacity-100 translate-y-0"
          leave-active-class="transition duration-150 ease-in"
          leave-from-class="opacity-100 translate-y-0"
          leave-to-class="opacity-0 -translate-y-1"
        >
          <div v-if="error" class="flex items-center gap-2 bg-red-50 border border-red-200 text-red-600 text-sm rounded-xl px-4 py-3">
            <svg class="w-4 h-4 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/>
            </svg>
            <span>{{ error }}</span>
          </div>
        </transition>

        <!-- Submit Button -->
        <div class="animate-slide-up" style="animation-delay: 0.15s">
          <button
            type="submit"
            :disabled="loading"
            class="btn-primary w-full py-3 text-base"
          >
            <svg v-if="loading" class="animate-spin w-5 h-5" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
            </svg>
            <span v-else>{{ isRegister ? 'Create Account' : 'Sign In' }}</span>
          </button>
        </div>
      </form>

      <!-- Toggle Login/Register -->
      <div class="mt-6 text-center animate-fade-in" style="animation-delay: 0.2s">
        <p class="text-sm text-gray-400">
          <template v-if="isRegister">
            Already have an account?
            <button @click="isRegister = false" class="text-primary font-semibold hover:underline transition-colors">
              Sign In
            </button>
          </template>
          <template v-else>
            First time here?
            <button @click="isRegister = true" class="text-accent font-semibold hover:underline transition-colors">
              Create Account
            </button>
          </template>
        </p>
      </div>
    </div>
  </div>
</template>
