<script lang="ts" setup>
// ==========================================================================
//
// Replaces the unstyled placeholder that shipped three bare buttons, two
// unlabelled inputs and a REAL EMAIL AND PASSWORD hardcoded as the default
// field values (see the note in the commit - those credentials are in git
// history and should be rotated).
//
// Visual language matches LoadingScreen/EndScreen: the gridded
// $secondary-background backdrop, a $secondary-background card at 20px radius,
// Lexend for headings, Inter for body, Kode Mono for the technical line, and
// the pill button with a $secondary-color border and an $accent glow on hover.
// ==========================================================================
import { computed, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { Mail, Lock, Eye, EyeOff, LoaderCircle, ArrowRight, AlertCircle, CheckCircle2 } from 'lucide-vue-next';
import { useAuthStore, authErrorMessage, type OAuthProvider } from '@/stores/useAuth';

const { login, signUp, sendPasswordReset } = useAuthStore();
const router = useRouter();
const route = useRoute();

// where to go after signing in. The guard puts the blocked destination in
// ?redirect, so a user who deep-linked to /stats lands on /stats, not "/".
const redirectPath = computed(() => {
  const raw = route.query.redirect;
  const path = typeof raw === 'string' ? raw : '/';
  // only accept same-site absolute paths. Without this check an attacker
  // could send someone to /login?redirect=https://evil.example and the app
  // would bounce them off-site straight after a successful sign-in.
  return path.startsWith('/') && !path.startsWith('//') ? path : '/';
});

type Mode = 'signin' | 'signup';
const mode = ref<Mode>('signin');

const email = ref('');
const password = ref('');
const showPassword = ref(false);

const loading = ref(false);
/** tracked separately so only the clicked provider shows a spinner. */
const oauthLoading = ref<OAuthProvider | null>(null);
const errorMessage = ref<string | null>(null);
const notice = ref<string | null>(null);

const busy = computed(() => loading.value || oauthLoading.value !== null);

const canSubmit = computed(() =>
  email.value.trim().length > 0 && password.value.length > 0 && !busy.value,
);

function switchMode(next: Mode) {
  mode.value = next;
  errorMessage.value = null;
  notice.value = null;
}

async function submitEmail() {
  if (!canSubmit.value) return;
  loading.value = true;
  errorMessage.value = null;
  notice.value = null;

  try {
    if (mode.value === 'signup') {
      const { needsConfirmation } = await signUp(email.value.trim(), password.value);
      if (needsConfirmation) {
        // signUp resolves with a user but no session when email
        // confirmation is enabled. Saying so is the difference between a
        // working flow and one that looks like it silently did nothing.
        notice.value = 'Account created. Check your email to confirm it, then sign in.';
        mode.value = 'signin';
        password.value = '';
        return;
      }
    } else {
      await login({ email: email.value.trim(), password: password.value });
    }
    await router.push(redirectPath.value);
  } catch (err) {
    errorMessage.value = authErrorMessage(err);
  } finally {
    loading.value = false;
  }
}

async function submitOAuth(provider: OAuthProvider) {
  if (busy.value) return;
  oauthLoading.value = provider;
  errorMessage.value = null;
  try {
    // this navigates away to the provider, so there is no success path to
    // handle here - control returns via the redirect URL.
    await login({ provider }, redirectPath.value);
  } catch (err) {
    errorMessage.value = authErrorMessage(err);
    oauthLoading.value = null;
  }
}

async function forgotPassword() {
  if (!email.value.trim()) {
    errorMessage.value = 'Enter your email first, then choose "Forgot password".';
    return;
  }
  loading.value = true;
  errorMessage.value = null;
  try {
    await sendPasswordReset(email.value.trim());
    notice.value = 'If that email has an account, a reset link is on its way.';
  } catch (err) {
    errorMessage.value = authErrorMessage(err);
  } finally {
    loading.value = false;
  }
}

// lucide ships no brand marks, so these are inline paths. Kept as a small
// typed list rather than three near-identical blocks in the template.
const providers: { id: OAuthProvider; label: string; path: string }[] = [
  {
    id: 'google',
    label: 'Google',
    path: 'M21.35 11.1h-9.17v2.92h5.27c-.23 1.37-1.6 4.02-5.27 4.02-3.17 0-5.76-2.62-5.76-5.86s2.59-5.86 5.76-5.86c1.81 0 3.02.77 3.71 1.43l2.53-2.44C16.79 3.79 14.7 2.9 12.18 2.9 6.98 2.9 2.77 7.11 2.77 12.3s4.21 9.4 9.41 9.4c5.43 0 9.03-3.82 9.03-9.2 0-.62-.07-1.09-.16-1.4z',
  },
  {
    id: 'azure',
    label: 'Microsoft',
    path: 'M3 3h8.5v8.5H3V3zm9.5 0H21v8.5h-8.5V3zM3 12.5h8.5V21H3v-8.5zm9.5 0H21V21h-8.5v-8.5z',
  },
  {
    id: 'twitter',
    label: 'X',
    path: 'M17.53 3h3.17l-6.93 7.92L21.94 21h-6.38l-5-6.54L4.83 21H1.66l7.41-8.47L2 3h6.54l4.52 5.98L17.53 3zm-1.11 16.06h1.76L7.66 4.84H5.78l10.64 14.22z',
  },
];
</script>

<template>
  <div class="login-screen">
    <div class="login-card">

      <header class="brand">
        <div class="brand-mark">
          <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24"
               fill="none" stroke="currentColor" stroke-width="2"
               stroke-linecap="round" stroke-linejoin="round">
            <rect width="7" height="9" x="3" y="3" rx="1"/>
            <rect width="7" height="5" x="14" y="3" rx="1"/>
            <rect width="7" height="9" x="14" y="12" rx="1"/>
            <rect width="7" height="5" x="3" y="16" rx="1"/>
          </svg>
          <h1>Soluer</h1>
        </div>
        <h2>{{ mode === 'signin' ? 'Welcome back' : 'Create your account' }}</h2>
        <p class="brand-sub">
          {{ mode === 'signin'
            ? 'Sign in to sit papers and track your progress.'
            : 'Start solving past papers with automatic marking.' }}
        </p>
      </header>

      <!-- status region. aria-live so a screen reader announces the result
           of a submit, which is otherwise a purely visual change. -->
      <div class="status" aria-live="polite">
        <p v-if="errorMessage" class="status-line error">
          <AlertCircle class="status-icon" /> {{ errorMessage }}
        </p>
        <p v-else-if="notice" class="status-line notice">
          <CheckCircle2 class="status-icon" /> {{ notice }}
        </p>
      </div>

      <form class="form" @submit.prevent="submitEmail">
        <label class="field">
          <span class="field-label">Email</span>
          <div class="field-input">
            <Mail class="field-icon" />
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
            <Lock class="field-icon" />
            <input
              v-model="password"
              :type="showPassword ? 'text' : 'password'"
              :autocomplete="mode === 'signup' ? 'new-password' : 'current-password'"
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
              <EyeOff v-if="showPassword" class="field-icon" />
              <Eye v-else class="field-icon" />
            </button>
          </div>
        </label>

        <button
          v-if="mode === 'signin'"
          type="button"
          class="link-btn forgot"
          :disabled="busy"
          @click="forgotPassword"
        >
          Forgot password?
        </button>

        <button type="submit" class="primary" :disabled="!canSubmit">
          <LoaderCircle v-if="loading" class="btn-icon spin" />
          <template v-else>
            {{ mode === 'signin' ? 'Sign in' : 'Create account' }}
            <ArrowRight class="btn-icon" />
          </template>
        </button>
      </form>

      <div class="divider"><span>or continue with</span></div>

      <div class="oauth-row">
        <button
          v-for="p in providers"
          :key="p.id"
          class="oauth"
          type="button"
          :disabled="busy"
          @click="submitOAuth(p.id)"
        >
          <LoaderCircle v-if="oauthLoading === p.id" class="btn-icon spin" />
          <svg v-else xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"
               class="btn-icon" fill="currentColor">
            <path :d="p.path" />
          </svg>
          <span>{{ p.label }}</span>
        </button>
      </div>

      <p class="switch">
        <template v-if="mode === 'signin'">
          New here?
          <button type="button" class="link-btn" @click="switchMode('signup')">
            Create an account
          </button>
        </template>
        <template v-else>
          Already have an account?
          <button type="button" class="link-btn" @click="switchMode('signin')">
            Sign in
          </button>
        </template>
      </p>
    </div>
  </div>
</template>

<style lang="scss" scoped>
// same gridded backdrop as LoadingScreen and EndScreen.
.login-screen {
  position: fixed;
  inset: 0;
  display: grid;
  place-items: center;
  padding: 24px;
  overflow-y: auto;
  color: $text;
  background-color: $secondary-background;
  background-image:
    linear-gradient(to right, $background 1px, transparent 1px),
    linear-gradient(to bottom, $background 1px, transparent 1px);
  background-size: 30px 30px;
}

.login-card {
  width: 100%;
  max-width: 420px;
  background-color: $secondary-background;
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 20px;
  padding: 2.2rem 2rem;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.45);
}

/* ---- brand ---------------------------------------------------------- */
.brand {
  text-align: center;
  margin-bottom: 1.2rem;

  .brand-mark {
    display: flex;
    align-items: center;
    justify-content: center;
    column-gap: 10px;
    color: $text;
    svg { color: $accent; }
    h1 {
      font-family: 'Inter';
      font-size: 1.6rem;
      font-weight: 500;
      margin: 0;
    }
  }
  h2 {
    font-family: 'Lexend';
    font-weight: 400;
    font-size: 1.15rem;
    margin: 1.1rem 0 0;
  }
  .brand-sub {
    font-family: 'Inter';
    font-size: 0.8rem;
    opacity: 0.5;
    margin: 6px 0 0;
  }
}

/* ---- status --------------------------------------------------------- */
// reserves its own height so the card does not jump when a message appears.
.status { min-height: 34px; }
.status-line {
  display: flex;
  align-items: flex-start;
  column-gap: 8px;
  font-family: 'Inter';
  font-size: 0.78rem;
  border-radius: 10px;
  padding: 8px 10px;
  margin: 0;

  .status-icon { width: 15px; height: 15px; flex-shrink: 0; margin-top: 1px; }
  &.error  { background-color: $danger-darkened;  color: $text; .status-icon { stroke: $danger; } }
  &.notice { background-color: $success-darkened; color: $text; .status-icon { stroke: $success; } }
}

/* ---- form ----------------------------------------------------------- */
.form { display: flex; flex-direction: column; row-gap: 0.9rem; }

.field {
  display: flex;
  flex-direction: column;
  row-gap: 6px;

  .field-label {
    font-family: 'Lexend';
    font-size: 0.72rem;
    opacity: 0.55;
  }
  .field-input {
    display: flex;
    align-items: center;
    column-gap: 10px;
    background-color: $tertiary-background;
    border: 1px solid transparent;
    border-radius: 10px;
    padding: 0 12px;
    transition: border-color 0.25s ease, box-shadow 0.25s ease;

    // :focus-within so the whole field lights up, not just the bare input.
    &:focus-within {
      border-color: $secondary-color;
      box-shadow: 0 0 0 3px rgba(98, 187, 193, 0.12);
    }
    input {
      flex: 1;
      background: transparent;
      border: none;
      outline: none;
      color: $text;
      font-family: 'Inter';
      font-size: 0.9rem;
      padding: 11px 0;
      &::placeholder { color: $text; opacity: 0.25; }
      &:disabled { opacity: 0.5; }
      // Chrome's autofill repaints the input with its own near-white
      // background, which is unreadable on this palette. A long inset shadow
      // is the only reliable override.
      &:-webkit-autofill {
        -webkit-text-fill-color: $text;
        box-shadow: 0 0 0 1000px $tertiary-background inset;
        transition: background-color 9999s ease-out;
      }
    }
  }
  .field-icon { width: 16px; height: 16px; opacity: 0.4; flex-shrink: 0; }
  .reveal {
    background: none;
    border: none;
    cursor: pointer;
    display: flex;
    padding: 0;
    color: $text;
    &:hover .field-icon { opacity: 0.8; }
  }
}

.forgot { align-self: flex-end; margin-top: -4px; }

/* ---- buttons (LoadingScreen's pill, same hover) ---------------------- */
.primary {
  margin-top: 0.3rem;
  cursor: pointer;
  font-family: 'Lexend';
  display: flex;
  align-items: center;
  justify-content: center;
  column-gap: 8px;
  border: $secondary-color 2px solid;
  background-color: transparent;
  color: $text;
  padding: 11px 20px;
  border-radius: 50px;
  font-size: 0.88rem;
  transition: background 1s ease, box-shadow 0.5s ease, opacity 0.2s ease;

  &:hover:not(:disabled) {
    background-color: $secondary-color;
    box-shadow: 0 0 5px 1px $accent;
  }
  &:disabled { opacity: 0.45; cursor: not-allowed; }
}

.btn-icon { width: 16px; height: 16px; }
// the spinner is the only motion on this screen; honour reduced-motion.
.spin { animation: spin 0.9s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
@media (prefers-reduced-motion: reduce) {
  .spin { animation-duration: 3s; }
}

.divider {
  display: flex;
  align-items: center;
  column-gap: 12px;
  margin: 1.2rem 0 1rem;
  font-family: 'Kode Mono';
  font-size: 0.65rem;
  opacity: 0.35;

  &::before, &::after {
    content: '';
    flex: 1;
    height: 1px;
    background-color: rgba(255, 255, 255, 0.1);
  }
}

.oauth-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}
.oauth {
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  column-gap: 7px;
  background-color: $tertiary-background;
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 10px;
  color: $text;
  font-family: 'Inter';
  font-size: 0.76rem;
  padding: 10px 6px;
  transition: border-color 0.3s ease, background-color 0.3s ease;

  &:hover:not(:disabled) {
    border-color: $secondary-color;
    background-color: $background;
  }
  &:disabled { opacity: 0.45; cursor: not-allowed; }
}

.link-btn {
  background: none;
  border: none;
  padding: 0;
  cursor: pointer;
  color: $accent;
  font-family: 'Inter';
  font-size: 0.75rem;
  &:hover:not(:disabled) { text-decoration: underline; }
  &:disabled { opacity: 0.5; cursor: not-allowed; }
}

.switch {
  text-align: center;
  font-family: 'Inter';
  font-size: 0.75rem;
  opacity: 0.65;
  margin: 1.2rem 0 0;
}
</style>
