<script setup>
import { ref, computed } from 'vue'
import { RouterLink, useRouter, useRoute } from 'vue-router'
import {
  loginWithEmail,
  registerWithEmail,
  loginWithGoogle,
} from '@/services/auth'

const router = useRouter()
const route = useRoute()

const mode = ref('login') // 'login' | 'register'
const email = ref('')
const password = ref('')
const error = ref('')
const busy = ref(false)

const heading = computed(() => (mode.value === 'login' ? 'Sign in' : 'Create account'))
const submitLabel = computed(() => (mode.value === 'login' ? 'Sign in' : 'Create account'))

// Where to go after a successful sign-in: the route the guard bounced us from,
// or the IDE home.
function destination() {
  const target = route.query.redirect
  return typeof target === 'string' && target ? target : '/ide'
}

// Firebase auth errors are codes like "auth/invalid-credential"; map the common
// ones to something a person can read.
function friendlyError(err) {
  const code = err?.code || ''
  const map = {
    'auth/invalid-credential': 'Incorrect email or password.',
    'auth/invalid-email': 'That email address is not valid.',
    'auth/user-not-found': 'No account exists for that email.',
    'auth/wrong-password': 'Incorrect email or password.',
    'auth/email-already-in-use': 'An account already exists for that email.',
    'auth/weak-password': 'Password should be at least 6 characters.',
    'auth/popup-closed-by-user': 'Sign-in was cancelled.',
  }
  return map[code] || err?.message || 'Something went wrong. Please try again.'
}

async function submitEmail() {
  error.value = ''
  busy.value = true
  try {
    if (mode.value === 'login') {
      await loginWithEmail(email.value, password.value)
    } else {
      await registerWithEmail(email.value, password.value)
    }
    router.replace(destination())
  } catch (err) {
    error.value = friendlyError(err)
  } finally {
    busy.value = false
  }
}

async function submitGoogle() {
  error.value = ''
  busy.value = true
  try {
    await loginWithGoogle()
    router.replace(destination())
  } catch (err) {
    error.value = friendlyError(err)
  } finally {
    busy.value = false
  }
}

function toggleMode() {
  mode.value = mode.value === 'login' ? 'register' : 'login'
  error.value = ''
}
</script>

<template>
  <main class="login">
    <form class="card" @submit.prevent="submitEmail">
      <RouterLink class="login-brand" to="/">P/ Pseudocode</RouterLink>
      <h1>{{ heading }}</h1>
      <p class="sub">Cambridge Pseudocode IDE</p>

      <label>
        <span>Email</span>
        <input v-model="email" type="email" autocomplete="email" required />
      </label>

      <label>
        <span>Password</span>
        <input
          v-model="password"
          type="password"
          :autocomplete="mode === 'login' ? 'current-password' : 'new-password'"
          required
        />
      </label>

      <p v-if="error" class="error">{{ error }}</p>

      <button class="primary" type="submit" :disabled="busy">{{ submitLabel }}</button>

      <div class="divider"><span>or</span></div>

      <button class="google" type="button" :disabled="busy" @click="submitGoogle">
        Continue with Google
      </button>

      <p class="switch">
        <template v-if="mode === 'login'">
          No account?
          <button type="button" class="link" @click="toggleMode">Create one</button>
        </template>
        <template v-else>
          Already registered?
          <button type="button" class="link" @click="toggleMode">Sign in</button>
        </template>
      </p>
    </form>
  </main>
</template>

<style scoped>
.login {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 2rem 1rem;
}

.login-brand {
  color: var(--accent);
  font-family: var(--font-display);
  font-size: 0.78rem;
  font-weight: 600;
  letter-spacing: 0.03em;
  text-decoration: none;
}

.card {
  width: 100%;
  max-width: 22rem;
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 0.75rem;
  padding: 1.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
  box-shadow: 0 10px 30px color-mix(in srgb, var(--background) 72%, transparent);
}

h1 {
  margin: 0;
  font-size: 1.35rem;
}

.sub {
  margin: -0.5rem 0 0.5rem;
  color: var(--muted);
  font-size: 0.9rem;
}

label {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  font-size: 0.85rem;
  color: var(--muted);
}

input {
  padding: 0.55rem 0.65rem;
  border: 1px solid var(--border);
  border-radius: 0.45rem;
  background: var(--panel-2);
  color: var(--ink);
}

input:focus {
  outline: 2px solid var(--accent);
  outline-offset: 0;
}

button {
  cursor: pointer;
  border-radius: 0.45rem;
  padding: 0.55rem 0.75rem;
}

button:disabled {
  opacity: 0.6;
  cursor: default;
}

.primary {
  background: var(--primary-color-lightened);
  border-color: var(--secondary-color);
  color: var(--text);
  font-weight: 640;
}

.google {
  font-weight: 560;
}

.divider {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  color: var(--muted);
  font-size: 0.8rem;
}

.divider::before,
.divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--border);
}

.error {
  margin: 0;
  color: var(--danger-foreground);
  font-size: 0.85rem;
}

.switch {
  margin: 0.25rem 0 0;
  text-align: center;
  font-size: 0.85rem;
  color: var(--muted);
}

.link {
  border: none;
  background: none;
  padding: 0;
  color: var(--accent);
  font-weight: 600;
}
</style>
