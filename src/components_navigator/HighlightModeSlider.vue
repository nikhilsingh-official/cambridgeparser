<script setup>
import { computed } from "vue";

const modelValue = defineModel({ type: Boolean, default: true });
const label = computed(() =>
  modelValue.value ? "Correct" : "Eliminate"
)
</script>

<template>
    <div class="wrapper">
        <p>Highlight Mode</p>
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
        <p>{{ label }}</p>
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
  transition: background 0.25s ease;
  border: none;
  background: $danger;
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
    .thumb {
      transform: translateX(22px);
    }
  }
}
</style>