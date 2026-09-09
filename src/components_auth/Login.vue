<script lang="ts" setup>
// ==========================================================================
//
// Replaces the unstyled placeholder that shipped three bare buttons, two
// unlabelled inputs and a REAL EMAIL AND PASSWORD hardcoded as the default
// field values (see the note in the commit - those credentials are in git
// history and should be rotated).
//
// Every colour, font, radius and shadow below comes from a THEME TOKEN, so
// this one screen renders correctly under the internal soluer-dark theme id
// (shown to users as Teal Dark),
// exam-paper (warm paper, oxblood, square) and cambridge-dark (amber, square)
// with no per-theme rules. That is the whole point of the token layer: the
// same login screen serves the whole CambridgeParser application.
// ==========================================================================
import { computed, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { Mail, Lock, Eye, EyeOff, LoaderCircle, ArrowRight, AlertCircle, CheckCircle2, BookOpenCheck } from 'lucide-vue-next';
import { useAuthStore, authErrorMessage, type OAuthProvider } from '@/stores/useAuth';
import ThemeSwitcher from '@/components/ThemeSwitcher.vue';

const { login, signUp, sendPasswordReset, clearPasswordRecovery } = useAuthStore();
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

type Mode = 'signin' | 'signup' | 'recovery-request';
// invalid/reset links return here with mode=recovery so another email can
// be requested without making the user hunt for the entry point.
const mode = ref<Mode>(route.query.mode === 'recovery' ? 'recovery-request' : 'signin');

const email = ref('');
const password = ref('');
const showPassword = ref(false);

const loading = ref(false);
/** tracked separately so only the clicked provider shows a spinner. */
const oauthLoading = ref<OAuthProvider | null>(null);
const errorMessage = ref<string | null>(null);
const notice = ref<string | null>(
  route.query.notice === 'password-updated'
    ? 'Password updated. Sign in with your new password.'
    : null,
);

const busy = computed(() => loading.value || oauthLoading.value !== null);

const canSubmit = computed(() =>
  email.value.trim().length > 0
    && (mode.value === 'recovery-request' || password.value.length > 0)
    && !busy.value,
);

function switchMode(next: Mode) {
  mode.value = next;
  password.value = '';
  errorMessage.value = null;
  notice.value = null;
  if (next === 'recovery-request') clearPasswordRecovery();
}

async function submitEmail() {
  if (!canSubmit.value) return;
  loading.value = true;
  errorMessage.value = null;
  notice.value = null;

  try {
    if (mode.value === 'recovery-request') {
      // Supabase intentionally does not reveal whether this address exists.
      await sendPasswordReset(email.value.trim());
      notice.value = 'If an account exists, check your email for a reset link.';
      return;
    }
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

// lucide ships no brand marks, so these are inline paths. Kept as a small
// typed list rather than three near-identical blocks in the template.
const providers: { id: OAuthProvider; label: string; path?: string }[] = [
  {
    id: 'google',
    label: 'Google',
  },
  {
    id: 'azure',
    label: 'Microsoft',
    path: 'M3 3h8.5v8.5H3V3zm9.5 0H21v8.5h-8.5V3zM3 12.5h8.5V21H3v-8.5zm9.5 0H21V21h-8.5v-8.5z',
  },
  {
    id: 'github',
    label: 'GitHub',
    path: 'M12 .7a12 12 0 0 0-3.79 23.39c.6.11.82-.26.82-.58v-2.23c-3.34.73-4.04-1.42-4.04-1.42-.55-1.39-1.34-1.76-1.34-1.76-1.09-.75.08-.73.08-.73 1.2.09 1.84 1.24 1.84 1.24 1.07 1.84 2.81 1.31 3.5 1 .11-.78.42-1.31.76-1.61-2.67-.3-5.47-1.33-5.47-5.93 0-1.31.47-2.38 1.24-3.22-.13-.3-.54-1.52.11-3.18 0 0 1.01-.32 3.3 1.23A11.5 11.5 0 0 1 12 6.8c1.02 0 2.04.14 3 .4 2.29-1.55 3.3-1.23 3.3-1.23.65 1.66.24 2.88.12 3.18.77.84 1.23 1.91 1.23 3.22 0 4.61-2.81 5.62-5.48 5.92.43.37.81 1.1.81 2.22v3c0 .32.22.7.83.58A12 12 0 0 0 12 .7Z',
  },
];
</script>

<template>
  <div class="login-screen">
    <div class="login-card">

      <header class="brand">
        <div class="brand-mark">
          <BookOpenCheck aria-hidden="true" />
          <h1>CambridgeParser</h1>
        </div>
        <h2>{{ mode === 'signin'
          ? 'Welcome back'
          : mode === 'signup' ? 'Create your account' : 'Reset your password' }}</h2>
        <p class="brand-sub">
          {{ mode === 'signin'
            ? 'Sign in to sit papers and track your progress.'
            : mode === 'signup'
              ? 'Start solving past papers with automatic marking.'
              : 'Enter your email and we will send a secure reset link.' }}
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

        <label v-if="mode !== 'recovery-request'" class="field">
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

        <button type="submit" class="primary" :disabled="!canSubmit">
          <LoaderCircle v-if="loading" class="btn-icon spin" />
          <template v-else>
            {{ mode === 'signin'
              ? 'Sign in'
              : mode === 'signup' ? 'Create account' : 'Send reset link' }}
            <ArrowRight class="btn-icon" />
          </template>
        </button>
      </form>

      <div v-if="mode !== 'recovery-request'" class="divider"><span>or continue with</span></div>

      <div v-if="mode !== 'recovery-request'" class="oauth-row">
        <button
          v-for="p in providers"
          :key="p.id"
          class="oauth"
          type="button"
          :disabled="busy"
          :aria-label="oauthLoading === p.id ? `Connecting to ${p.label}` : `Continue with ${p.label}`"
          :aria-busy="oauthLoading === p.id"
          @click="submitOAuth(p.id)"
        >
          <LoaderCircle v-if="oauthLoading === p.id" class="btn-icon spin" aria-hidden="true" />
          <!-- Google's required multicolour brand mark is intentionally
               not recoloured through the app theme. -->
          <svg v-else-if="p.id === 'google'" xmlns="http://www.w3.org/2000/svg"
               viewBox="0 0 18 18" class="btn-icon" aria-hidden="true">
            <path fill="#4285f4" d="M17.64 9.205c0-.639-.057-1.252-.164-1.841H9v3.482h4.844a4.14 4.14 0 0 1-1.797 2.716v2.259h2.909c1.702-1.567 2.684-3.875 2.684-6.616Z" />
            <path fill="#34a853" d="M9 18c2.43 0 4.468-.806 5.956-2.179l-2.909-2.259c-.806.54-1.835.859-3.047.859-2.344 0-4.328-1.585-5.037-3.714H.956v2.332A9 9 0 0 0 9 18Z" />
            <path fill="#fbbc05" d="M3.963 10.707A5.41 5.41 0 0 1 3.682 9c0-.592.102-1.167.281-1.707V4.961H.956A9 9 0 0 0 0 9c0 1.452.347 2.827.956 4.039l3.007-2.332Z" />
            <path fill="#ea4335" d="M9 3.579c1.321 0 2.507.454 3.441 1.346l2.581-2.581C13.464.892 11.427 0 9 0A9 9 0 0 0 .956 4.961l3.007 2.332C4.672 5.164 6.656 3.579 9 3.579Z" />
          </svg>
          <svg v-else xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"
               class="btn-icon" fill="currentColor" aria-hidden="true">
            <path :d="p.path" />
          </svg>
          <span>{{ oauthLoading === p.id ? `Connecting to ${p.label}` : `Continue with ${p.label}` }}</span>
        </button>
      </div>

      <!-- theme choice lives on the login screen because it is the one
           page every user sees before anything else. -->
      <div class="theme-row">
        <ThemeSwitcher />
      </div>

      <p class="switch">
        <template v-if="mode === 'signin'">
          New here?
          <button type="button" class="link-btn" @click="switchMode('signup')">
            Create an account
          </button>
          <span class="switch-separator" aria-hidden="true">·</span>
          <button type="button" class="link-btn" @click="switchMode('recovery-request')">
            Forgot password?
          </button>
        </template>
        <template v-else-if="mode === 'recovery-request'">
          Remembered it?
          <button type="button" class="link-btn" @click="switchMode('signin')">
            Sign in
          </button>
        </template>
        <template v-else>
          Already have an account?
          <button type="button" class="link-btn" @click="switchMode('signin')">
            Sign in
          </button>
        </template>
      </p>

      <!-- keep policy and deletion disclosures directly reachable from
           every account-provisioning path. -->
      <p class="legal-notice">
        By continuing, you agree to our
        <RouterLink to="/terms">Terms</RouterLink>
        and acknowledge our
        <RouterLink to="/privacy">Privacy Policy</RouterLink>.
        You can also review how to
        <RouterLink to="/data-deletion">delete your account and data</RouterLink>.
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
    linear-gradient(to right, $grid-line 1px, transparent 1px),
    linear-gradient(to bottom, $grid-line 1px, transparent 1px);
  background-size: 30px 30px;
}

.login-card {
  width: 100%;
  max-width: 420px;
  background-color: $secondary-background;
  border: 1px solid $border;
  border-radius: $radius-card;
  padding: 2.2rem 2rem;
  box-shadow: $card-shadow;
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
      font-family: $font-body;
      font-size: 1.6rem;
      font-weight: 500;
      margin: 0;
    }
  }
  h2 {
    font-family: $font-display;
    font-weight: 400;
    font-size: 1.15rem;
    margin: 1.1rem 0 0;
  }
  .brand-sub {
    font-family: $font-body;
    font-size: 0.8rem;
    // $muted rather than opacity - opacity on a light theme washes text
    // to unreadable grey, whereas the token is tuned per theme.
    color: $muted;
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
  font-family: $font-body;
  font-size: 0.78rem;
  border-radius: $radius-control;
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
    font-family: $font-display;
    font-size: 0.72rem;
    opacity: 0.55;
  }
  .field-input {
    display: flex;
    align-items: center;
    column-gap: 10px;
    background-color: $tertiary-background;
    border: 1px solid transparent;
    border-radius: $radius-control;
    padding: 0 12px;
    transition: border-color 0.25s ease, box-shadow 0.25s ease;

    // :focus-within so the whole field lights up, not just the bare input.
    &:focus-within {
      border-color: $secondary-color;
      box-shadow: 0 0 0 3px $focus-ring;
    }
    input {
      flex: 1;
      background: transparent;
      border: none;
      outline: none;
      color: $text;
      font-family: $font-body;
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

/* ---- buttons (LoadingScreen's pill, same hover) ---------------------- */
.primary {
  margin-top: 0.3rem;
  cursor: pointer;
  font-family: $font-display;
  display: flex;
  align-items: center;
  justify-content: center;
  column-gap: 8px;
  border: $secondary-color 2px solid;
  background-color: transparent;
  color: $text;
  padding: 11px 20px;
  border-radius: $radius-pill;
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
  font-family: $font-mono;
  font-size: 0.65rem;
  opacity: 0.35;

  &::before, &::after {
    content: '';
    flex: 1;
    height: 1px;
    background-color: $border;
  }
}

.oauth-row {
  display: grid;
  grid-template-columns: 1fr;
  gap: 10px;
}
.oauth {
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  column-gap: 7px;
  background-color: $tertiary-background;
  border: 1px solid $border;
  border-radius: $radius-control;
  color: $text;
  font-family: $font-body;
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
  font-family: $font-body;
  font-size: 0.75rem;
  &:hover:not(:disabled) { text-decoration: underline; }
  &:disabled { opacity: 0.5; cursor: not-allowed; }
}

.theme-row {
  display: flex;
  justify-content: center;
  margin-top: 1.2rem;
}

.switch {
  text-align: center;
  font-family: $font-body;
  font-size: 0.75rem;
  opacity: 0.65;
  margin: 1.2rem 0 0;
}

// visually separates the two sign-in alternatives without another row.
.switch-separator { margin: 0 0.35rem; }

// OAuth policy links remain visible before a user grants account access.
.legal-notice {
  margin: 0.8rem 0 0;
  color: $muted;
  font-family: $font-body;
  font-size: 0.65rem;
  line-height: 1.5;
  text-align: center;

  a {
    color: $accent;
    text-underline-offset: 0.18em;
  }
}
</style>
