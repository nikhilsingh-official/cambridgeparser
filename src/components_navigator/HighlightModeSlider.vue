<script setup lang="ts">
// rewritten. This used `defineModel({ type: Boolean })` and was mounted
// with no v-model, so its toggle drove a local boolean nothing read, and it
// never reflected the C/E keybinds. It now reads and writes the shared
// highlightMode directly, so switch, keys and paper cannot disagree.
import { getHighlightMode } from "./composable";

const { highlightMode, isCorrectMode, toggleMode } = getHighlightMode();
</script>

<template>
    <div class="wrapper">
        <p>Highlight Mode</p>
        <button
          type="button"
          role="switch"
          :aria-checked="isCorrectMode"
          :aria-label="`Highlight mode: ${highlightMode}. Press C for correct, E for eliminate.`"
          @click="toggleMode"
          class="toggle"
          :class="{ on: isCorrectMode }"
        >
          <span class="thumb" />
        </button>
        <p class="mode-label">{{ isCorrectMode ? 'Correct' : 'Eliminate' }}</p>
    </div>
</template>

<style scoped lang="scss">
.wrapper {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
}

p {
  font-family: $font-body;
  color: $text;
  font-size: 13.5px;
}

// fixed width so the row does not reflow when the word changes length
// ("Correct" vs "Eliminate") - the toggle used to shift sideways on every press.
.mode-label {
  min-width: 62px;
  text-align: right;
  font-family: $font-mono;
  font-size: 11px;
  letter-spacing: 0.03em;
}

.toggle {
  width: 44px;
  height: 24px;
  border-radius: $radius-pill;
  display: inline-flex;
  align-items: center;
  cursor: pointer;
  transition: background 0.25s ease;
  border: none;
  background: $danger;
  flex-shrink: 0;

  .thumb {
    width: 20px;
    height: 20px;
    border-radius: 50%;
    background: $text;
    transition: transform 0.25s ease;
    transform: translateX(2px);
  }

  &.on {
    background: $success;
    .thumb { transform: translateX(22px); }
  }
}
</style>
