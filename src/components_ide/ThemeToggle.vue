<script setup>
// repointed at the app's single theme module. The IDE shipped its own,
// which wrote data-theme='light'|'dark' - the same attribute this app uses for
// 'soluer-dark' | 'exam-paper' | 'cambridge-dark'. Two writers, one attribute,
// last one wins: keeping both would have made the theme depend on which page
// you happened to load first.
import { cycleTheme as toggleTheme, isLightTheme } from '@/lib/theme'
import { computed } from 'vue'
const isDarkTheme = computed(() => !isLightTheme.value)
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
