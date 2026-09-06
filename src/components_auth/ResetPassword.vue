<script setup lang="ts">
// ============================================================================
//
// Dedicated Supabase password-recovery completion screen.
// ============================================================================

import { computed, onMounted, ref } from 'vue';
import { storeToRefs } from 'pinia';
import { useRouter } from 'vue-router';
import { AlertCircle, CheckCircle2, LoaderCircle, Lock } from 'lucide-vue-next';
import ThemeSwitcher from '@/components/ThemeSwitcher.vue';
import { authErrorMessage, useAuthStore } from '@/stores/useAuth';
import {
  MINIMUM_RECOVERY_PASSWORD_LENGTH,
  validateRecoveryPassword,
} from '@/lib/auth/passwordRecovery';

const router = useRouter();
const auth = useAuthStore();
const { passwordRecovery, passwordRecoveryError, session } = storeToRefs(auth);

const password = ref('');
const confirmation = ref('');
const submitting = ref(false);
const errorMessage = ref<string | null>(null);
const complete = ref(false);

const recoveryReady = computed(() =>
  passwordRecovery.value && session.value !== null && passwordRecoveryError.value === null,
);
const canSubmit = computed(() =>
  recoveryReady.value
    && password.value.length > 0
    && confirmation.value.length > 0
    && !submitting.value
    && !complete.value,
);

onMounted(() => {
  // Supabase has already consumed the callback by this point. Remove error
  // parameters or any surviving implicit tokens from browser history.
  if (window.location.search || window.location.hash) {
    window.history.replaceState(window.history.state, document.title, window.location.pathname);
  }
});

async function submitPassword() {
  if (!canSubmit.value) return;
  const validationError = validateRecoveryPassword(password.value, confirmation.value);
  if (validationError) {
    errorMessage.value = validationError;
    return;
  }

  submitting.value = true;
  errorMessage.value = null;
  try {
    await auth.updateRecoveredPassword(password.value);
    complete.value = true;
    password.value = '';
    confirmation.value = '';
    await router.replace({ name: 'Login', query: { notice: 'password-updated' } });
  } catch (error) {
    errorMessage.value = authErrorMessage(error);
  } finally {
    submitting.value = false;
  }
}

async function requestAnotherLink() {
  // an unrelated persisted session must not make the guest-only login route
  // bounce back to the dashboard while the user is trying to recover access.
  if (session.value) await auth.logout();
  auth.clearPasswordRecovery();
  await router.replace({ name: 'Login', query: { mode: 'recovery' } });
}
</script>

<template>
  <main class="recovery-screen">
    <section class="recovery-card" aria-labelledby="recovery-title">
      <header class="brand">
        <div class="brand-mark" aria-hidden="true">
          <Lock />
        </div>
        <h1 id="recovery-title">Choose a new password</h1>
        <p>
          Use at least {{ MINIMUM_RECOVERY_PASSWORD_LENGTH }} characters.
          Your password is sent only to Supabase Auth.
        </p>
      </header>

      <div class="status" aria-live="polite">
        <p v-if="passwordRecoveryError || !recoveryReady" class="status-line error">
          <AlertCircle /> This password reset link is invalid or has expired.
        </p>
        <p v-else-if="errorMessage" class="status-line error">
          <AlertCircle /> {{ errorMessage }}
        </p>
        <p v-else-if="complete" class="status-line notice">
          <CheckCircle2 /> Password updated.
        </p>
      </div>

      <form v-if="recoveryReady && !complete" class="form" @submit.prevent="submitPassword">
        <label class="field">
          <span>New password</span>
          <input
            v-model="password"
            type="password"
            autocomplete="new-password"
            :minlength="MINIMUM_RECOVERY_PASSWORD_LENGTH"
            :disabled="submitting"
            required
          />
        </label>
        <label class="field">
          <span>Confirm new password</span>
          <input
            v-model="confirmation"
            type="password"
            autocomplete="new-password"
            :minlength="MINIMUM_RECOVERY_PASSWORD_LENGTH"
            :disabled="submitting"
            required
          />
        </label>
        <button type="submit" class="primary" :disabled="!canSubmit">
          <LoaderCircle v-if="submitting" class="spin" />
          <span v-else>Update password</span>
        </button>
      </form>

      <button
        v-if="!recoveryReady"
        type="button"
        class="primary"
        @click="requestAnotherLink"
      >Request another reset link</button>

      <div class="theme-row"><ThemeSwitcher /></div>
    </section>
  </main>
</template>

<style lang="scss" scoped>
.recovery-screen {
  position: fixed;
  inset: 0;
  display: grid;
  place-items: center;
  overflow-y: auto;
  padding: 24px;
  color: $text;
  background-color: $secondary-background;
  background-image:
    linear-gradient(to right, $grid-line 1px, transparent 1px),
    linear-gradient(to bottom, $grid-line 1px, transparent 1px);
  background-size: 30px 30px;
}

.recovery-card {
  width: min(100%, 420px);
  padding: 2rem;
  border: 1px solid $border;
  border-radius: $radius-card;
  background: $secondary-background;
  box-shadow: $card-shadow;
}

.brand {
  text-align: center;

  h1 {
    margin: 0.8rem 0 0.4rem;
    font-family: $font-display;
    font-size: 1.25rem;
    font-weight: 500;
  }

  p {
    margin: 0;
    color: $muted;
    font-family: $font-body;
    font-size: 0.8rem;
    line-height: 1.5;
  }
}

.brand-mark {
  display: grid;
  width: 42px;
  height: 42px;
  margin: 0 auto;
  place-items: center;
  border-radius: $radius-control;
  background: $tertiary-background;
  color: $accent;

  svg { width: 20px; }
}

.status {
  min-height: 54px;
  margin-top: 1rem;
}

.status-line {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin: 0;
  padding: 9px 10px;
  border-radius: $radius-control;
  font-family: $font-body;
  font-size: 0.78rem;

  svg { width: 16px; flex: 0 0 auto; }
  &.error { background: $danger-darkened; }
  &.error svg { stroke: $danger; }
  &.notice { background: $success-darkened; }
  &.notice svg { stroke: $success; }
}

.form {
  display: grid;
  gap: 0.9rem;
}

.field {
  display: grid;
  gap: 6px;
  font-family: $font-display;
  font-size: 0.72rem;

  input {
    width: 100%;
    box-sizing: border-box;
    padding: 11px 12px;
    border: 1px solid $border;
    border-radius: $radius-control;
    outline: none;
    background: $tertiary-background;
    color: $text;
    font-family: $font-body;

    &:focus {
      border-color: $secondary-color;
      box-shadow: 0 0 0 3px $focus-ring;
    }
  }
}

.primary {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  margin-top: 0.25rem;
  padding: 11px 16px;
  border: 2px solid $secondary-color;
  border-radius: $radius-pill;
  background: transparent;
  color: $text;
  cursor: pointer;
  font-family: $font-display;

  &:hover:not(:disabled) { background: $secondary-color; }
  &:disabled { cursor: not-allowed; opacity: 0.45; }
}

.spin { width: 17px; animation: spin 0.9s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

.theme-row {
  display: flex;
  justify-content: center;
  margin-top: 1.2rem;
}

@media (prefers-reduced-motion: reduce) {
  .spin { animation-duration: 3s; }
}
</style>
