<script setup lang="ts">
// ==========================================================================
// Cycles through the available themes. Styled entirely from tokens, so it is
// legible in all three without any per-theme rules of its own.
// ==========================================================================
import { Palette } from 'lucide-vue-next';
import { ALL_THEMES, THEME_LABEL, currentTheme, cycleTheme } from '@/lib/theme';
import { computed } from 'vue';

const nextLabel = computed(() => {
  const i = ALL_THEMES.indexOf(currentTheme.value);
  return THEME_LABEL[ALL_THEMES[(i + 1) % ALL_THEMES.length]!];
});
</script>

<template>
  <button
    type="button"
    class="theme-switcher"
    :title="`Switch to ${nextLabel}`"
    :aria-label="`Current theme ${THEME_LABEL[currentTheme]}. Switch to ${nextLabel}.`"
    @click="cycleTheme"
  >
    <Palette class="icon" />
    <span>{{ THEME_LABEL[currentTheme] }}</span>
  </button>
</template>

<style lang="scss" scoped>
.theme-switcher {
  display: inline-flex;
  align-items: center;
  column-gap: 7px;
  cursor: pointer;
  background-color: $tertiary-background;
  border: 1px solid $border;
  border-radius: $radius-control;
  color: $text;
  font-family: $font-body;
  font-size: 0.76rem;
  padding: 7px 11px;
  transition: border-color 0.25s ease, color 0.25s ease;

  &:hover {
    border-color: $secondary-color;
    color: $accent;
  }
  .icon { width: 14px; height: 14px; }
}
</style>
