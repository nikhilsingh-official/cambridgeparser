<script setup lang="ts">
// ============================================================================
//
// Explicit gate for application layouts that are not safe at phone widths.
// ============================================================================

import { MonitorUp } from 'lucide-vue-next';
import { useRouter } from 'vue-router';
import { MINIMUM_APP_WIDTH } from '@/lib/layout/mobileAccess';
import { useAuthStore } from '@/stores/useAuth';

const router = useRouter();
const auth = useAuthStore();

async function signOut() {
  await auth.logout();
  await router.replace({ name: 'Login' });
}
</script>

<template>
  <main class="mobile-block" aria-labelledby="mobile-block-title">
    <section class="mobile-block__card">
      <MonitorUp aria-hidden="true" />
      <h1 id="mobile-block-title">Desktop required</h1>
      <p>
        The paper solver, IDE, and progress pages are not supported at this
        screen size. Use a window at least {{ MINIMUM_APP_WIDTH }} pixels wide.
      </p>
      <button type="button" @click="signOut">Sign out</button>
    </section>
  </main>
</template>

<style lang="scss" scoped>
.mobile-block {
  position: fixed;
  inset: 0;
  z-index: 10000;
  display: grid;
  place-items: center;
  padding: 24px;
  color: $text;
  background: $secondary-background;
}

.mobile-block__card {
  max-width: 30rem;
  text-align: center;

  > svg {
    width: 42px;
    height: 42px;
    color: $accent;
  }

  h1 {
    margin: 1rem 0 0.5rem;
    font-family: $font-display;
    font-size: 1.4rem;
  }

  p {
    margin: 0;
    color: $muted;
    font-family: $font-body;
    font-size: 0.9rem;
    line-height: 1.6;
  }

  button {
    margin-top: 1.25rem;
    padding: 9px 18px;
    border: 1px solid $border;
    border-radius: $radius-control;
    background: $tertiary-background;
    color: $text;
    cursor: pointer;
    font-family: $font-body;
  }
}
</style>
