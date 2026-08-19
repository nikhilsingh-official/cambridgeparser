<script setup>
import { computed } from "vue";

const modelValue = defineModel({ type: Boolean, default: false });
</script>

<template>
    <p>Zen Mode</p>
    <button
      type="button"
      role="switch"
      :aria-checked="modelValue"
      @click="modelValue = !modelValue"
      class="toggle"
      :class="{ on: modelValue }"
    >
      <span class="thumb" />
    </button>
</template>

<style scoped lang="scss">
p {
  font-family: 'Inter';
  color: $text;
  font-size: 13.5px;
}

.toggle {
  width: 44px;
  height: 24px;
  border-radius: 9999px;
  display: inline-flex;
  align-items: center;
  cursor: pointer;
  background: $tertiary-background;
  transition: background 0.25s ease;
  border: none;

  .thumb {
    width: 20px;
    height: 20px;
    border-radius: 50%;
    background: $text;
    transition: transform 0.25s ease;
    transform: translate(2px);
  }

  &.on {
    background: $accent;
    .thumb {
      transform: translateX(22px);
    }
  }
}
</style>