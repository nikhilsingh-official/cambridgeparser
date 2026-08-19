<script setup>
// Login screen, shared in design with SmartSolver's. Both apps render the same
// layout, spacing and states. Both now run on the same Supabase project, so a
// sign-in here is a sign-in there. Each styles itself entirely from the shared
// CSS custom properties, so this screen follows whichever theme is active.
import { ref, computed } from 'vue'
import { RouterLink, useRouter, useRoute } from 'vue-router'
import {
  loginWithEmail,
  registerWithEmail,
  loginWithGoogle,
  sendPasswordReset,
} from '@/services/auth'
import ThemeToggle from '@/components/ThemeToggle.vue'

const router = useRouter()
const route = useRoute()

const mode = ref('login') // 'login' | 'register'
const email = ref('')
const password = ref('')
const showPassword = ref(false)
const error = ref('')
const notice = ref('')
const busy = ref(false)

const heading = computed(() => (mode.value === 'login' ? 'Welcome back' : 'Create your account'))
const submitLabel = computed(() => (mode.value === 'login' ? 'Sign in' : 'Create account'))
const subtitle = computed(() =>
  mode.value === 'login'
    ? 'Sign in to practise pseudocode with mark-scheme feedback.'
    : 'Start practising Cambridge 9618 pseudocode.',
)

// Where to go after a successful sign-in: the route the guard bounced us from,
// or the IDE home. Only same-site paths are accepted, so a crafted
// ?redirect=https://evil.example cannot bounce a user off-site post-login.
function destination() {
  const target = route.query.redirect
  if (typeof target !== 'string' || !target) return '/ide'
  return target.startsWith('/') && !target.startsWith('//') ? target : '/ide'
}

// Supabase AuthError carries a stable `code` on recent versions and a prose
// `message` on all of them, so match on the code where there is one and fall
// back to matching the message. The messages are deliberately vague about
// whether an account exists: "Invalid login credentials" covers both a wrong
// password and an unknown address, and repeating that vagueness here keeps the
// form from becoming an account-enumeration oracle.
function friendlyError(err) {
  const code = err?.code || ''
  const byCode = {
    invalid_credentials: 'Incorrect email or password.',
    email_address_invalid: 'That email address is not valid.',
    user_already_exists: 'An account already exists for that email.',
    email_exists: 'An account already exists for that email.',
    weak_password: 'Password should be at least 6 characters.',
    over_request_rate_limit: 'Too many attempts. Wait a moment and try again.',
    email_not_confirmed: 'Confirm your email address first - check your inbox.',
  }
  if (byCode[code]) return byCode[code]

  const message = err?.message || ''
  if (/invalid login credentials/i.test(message)) return 'Incorrect email or password.'
  if (/already registered|already exists/i.test(message)) return 'An account already exists for that email.'
  if (/password should be at least/i.test(message)) return 'Password should be at least 6 characters.'
  if (/email not confirmed/i.test(message)) return 'Confirm your email address first - check your inbox.'
  if (/rate limit|too many/i.test(message)) return 'Too many attempts. Wait a moment and try again.'
  if (/fetch|network/i.test(message)) return 'Cannot reach the server. Check your connection.'
  return message || 'Something went wrong. Please try again.'
}

async function submitEmail() {
  error.value = ''
  notice.value = ''
  busy.value = true
  try {
    if (mode.value === 'login') {
      await loginWithEmail(email.value.trim(), password.value)
    } else {
      await registerWithEmail(email.value.trim(), password.value)
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
  notice.value = ''
  busy.value = true
  try {
    // Navigates the page away to Google, so there is nothing to route to here
    // and `busy` stays true until the browser leaves. The destination travels
    // with the request and is applied when the redirect returns.
    await loginWithGoogle(destination())
  } catch (err) {
    error.value = friendlyError(err)
    busy.value = false
  }
}

async function forgotPassword() {
  if (!email.value.trim()) {
    error.value = 'Enter your email first, then choose "Forgot password".'
    return
  }
  error.value = ''
  busy.value = true
  try {
    await sendPasswordReset(email.value.trim())
    // Deliberately not "we sent an email": confirming which addresses have
    // accounts turns this form into an account-enumeration oracle.
    notice.value = 'If that email has an account, a reset link is on its way.'
  } catch (err) {
    error.value = friendlyError(err)
  } finally {
    busy.value = false
  }
}

function toggleMode() {
  mode.value = mode.value === 'login' ? 'register' : 'login'
  error.value = ''
  notice.value = ''
}
</script>

<template>
  <main class="login-screen">
    <form class="login-card" @submit.prevent="submitEmail">
      <header class="brand">
        <RouterLink class="brand-mark" to="/">
          <svg viewBox="0 0 24 24" width="26" height="26" fill="none"
               stroke="currentColor" stroke-width="2"
               stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <polyline points="16 18 22 12 16 6" />
            <polyline points="8 6 2 12 8 18" />
          </svg>
          <span>CambridgeParser</span>
        </RouterLink>
        <h1>{{ heading }}</h1>
        <p class="brand-sub">{{ subtitle }}</p>
      </header>

      <!-- Reserves its own height so the card does not jump when a message
           appears. aria-live announces the outcome of a submit. -->
      <div class="status" aria-live="polite">
        <p v-if="error" class="status-line is-error">{{ error }}</p>
        <p v-else-if="notice" class="status-line is-notice">{{ notice }}</p>
      </div>

      <label class="field">
        <span class="field-label">Email</span>
        <div class="field-input">
          <input
            v-model="email"
            type="email"
            autocomplete="email"
            placeholder="you@example.com"
            :disabled="busy"
            required
          />
        </div>
      </label>

      <label class="field">
        <span class="field-label">Password</span>
        <div class="field-input">
          <input
            v-model="password"
            :type="showPassword ? 'text' : 'password'"
            :autocomplete="mode === 'login' ? 'current-password' : 'new-password'"
            placeholder="••••••••"
            :disabled="busy"
            required
          />
          <button
            type="button"
            class="reveal"
            :aria-label="showPassword ? 'Hide password' : 'Show password'"
            @click="showPassword = !showPassword"
          >
            {{ showPassword ? 'Hide' : 'Show' }}
          </button>
        </div>
      </label>

      <button
        v-if="mode === 'login'"
        type="button"
        class="link forgot"
        :disabled="busy"
        @click="forgotPassword"
      >
        Forgot password?
      </button>

      <button class="primary" type="submit" :disabled="busy">
        {{ busy ? 'Working…' : submitLabel }}
      </button>

      <div class="divider"><span>or continue with</span></div>

      <button class="oauth" type="button" :disabled="busy" @click="submitGoogle">
        <svg viewBox="0 0 24 24" width="15" height="15" fill="currentColor" aria-hidden="true">
          <path d="M21.35 11.1h-9.17v2.92h5.27c-.23 1.37-1.6 4.02-5.27 4.02-3.17 0-5.76-2.62-5.76-5.86s2.59-5.86 5.76-5.86c1.81 0 3.02.77 3.71 1.43l2.53-2.44C16.79 3.79 14.7 2.9 12.18 2.9 6.98 2.9 2.77 7.11 2.77 12.3s4.21 9.4 9.41 9.4c5.43 0 9.03-3.82 9.03-9.2 0-.62-.07-1.09-.16-1.4z" />
        </svg>
        Google
      </button>

      <div class="theme-row">
        <ThemeToggle />
      </div>

      <p class="switch">
        <template v-if="mode === 'login'">
          New here?
          <button type="button" class="link" @click="toggleMode">Create an account</button>
        </template>
        <template v-else>
          Already have an account?
          <button type="button" class="link" @click="toggleMode">Sign in</button>
        </template>
      </p>
    </form>
  </main>
</template>

<style scoped>
/* The gridded backdrop is the shared signature of both apps' full-screen
   screens. --grid-line keeps it visible on paper as well as on slate. */
.login-screen {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 2rem 1rem;
  background-color: var(--background);
  background-image:
    linear-gradient(to right, var(--grid-line) 1px, transparent 1px),
    linear-gradient(to bottom, var(--grid-line) 1px, transparent 1px);
  background-size: 30px 30px;
}

.login-card {
  width: 100%;
  max-width: 24rem;
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: var(--radius-card);
  box-shadow: var(--card-shadow);
  padding: 1.9rem 1.75rem;
}

.brand {
  text-align: center;
}

.brand-mark {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--ink);
  font-family: var(--font-display);
  font-weight: 600;
  text-decoration: none;
}

.brand-mark svg {
  color: var(--accent);
}

.brand h1 {
  margin: 1rem 0 0;
  font-size: 1.2rem;
  font-weight: 600;
}

.brand-sub {
  margin: 0.35rem 0 0;
  color: var(--muted);
  font-size: 0.84rem;
}

.status {
  min-height: 2.1rem;
}

.status-line {
  margin: 0;
  border-radius: var(--radius-control);
  padding: 0.5rem 0.6rem;
  font-size: 0.8rem;
  border: 1px solid transparent;
}

.status-line.is-error {
  color: var(--danger-foreground);
  background: var(--danger-darkened);
  border-color: var(--danger);
}

.status-line.is-notice {
  color: var(--success);
  background: var(--success-darkened);
  border-color: var(--success);
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}

.field-label {
  color: var(--muted);
  font-size: 0.76rem;
}

.field-input {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: var(--panel-2);
  border: 1px solid var(--border);
  border-radius: var(--radius-control);
  padding: 0 0.6rem;
}

/* :focus-within so the whole field lights up, not just the bare input. */
.field-input:focus-within {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--focus-ring);
}

.field-input input {
  flex: 1;
  min-width: 0;
  border: 0;
  outline: none;
  background: transparent;
  color: var(--ink);
  padding: 0.55rem 0;
}

.field-input input::placeholder {
  color: var(--muted);
  opacity: 0.6;
}

.reveal {
  min-height: auto;
  border: 0;
  background: transparent;
  color: var(--muted);
  cursor: pointer;
  font-size: 0.74rem;
  padding: 0.2rem 0.1rem;
}

.reveal:hover {
  color: var(--accent);
}

.forgot {
  align-self: flex-end;
}

.primary {
  min-height: 2.4rem;
  border: 1px solid var(--secondary-color);
  border-radius: var(--radius-pill);
  background: var(--primary-color-lightened);
  color: var(--primary-foreground);
  cursor: pointer;
  font-family: var(--font-display);
  font-weight: 600;
}

.primary:disabled {
  opacity: 0.6;
  cursor: default;
}

.divider {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin: 0.35rem 0 0.1rem;
  color: var(--muted);
  font-family: var(--font-mono);
  font-size: 0.68rem;
}

.divider::before,
.divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--border);
}

.oauth {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  min-height: 2.3rem;
  border: 1px solid var(--border);
  border-radius: var(--radius-control);
  background: var(--panel-2);
  color: var(--ink);
  cursor: pointer;
}

.oauth:hover:not(:disabled) {
  border-color: var(--secondary-color);
  color: var(--accent);
}

.theme-row {
  display: flex;
  justify-content: center;
  margin-top: 0.4rem;
}

.link {
  min-height: auto;
  border: 0;
  padding: 0;
  background: transparent;
  color: var(--accent);
  cursor: pointer;
  font-size: 0.78rem;
}

.link:hover:not(:disabled) {
  text-decoration: underline;
}

.switch {
  margin: 0.4rem 0 0;
  text-align: center;
  color: var(--muted);
  font-size: 0.78rem;
}
</style>
