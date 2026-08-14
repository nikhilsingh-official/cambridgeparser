<script setup>
import { isDarkTheme, toggleTheme } from '@/services/theme'
</script>

<template>
  <button
    type="button"
    class="theme-toggle"
    :aria-label="`Switch to ${isDarkTheme ? 'light' : 'dark'} mode`"
    :title="`Switch to ${isDarkTheme ? 'light' : 'dark'} mode`"
    @click="toggleTheme"
  >
    <span aria-hidden="true">{{ isDarkTheme ? '☀' : '☾' }}</span>
    {{ isDarkTheme ? 'Light' : 'Dark' }}
  </button>
</template>

<style scoped>
.theme-toggle {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  min-height: 2rem;
  padding: 0.35rem 0.65rem;
  border: 1px solid var(--border);
  background: var(--panel);
  color: var(--ink);
  font-size: 0.82rem;
}

.theme-toggle:hover {
  border-color: var(--accent);
  color: var(--accent);
}
</style>
