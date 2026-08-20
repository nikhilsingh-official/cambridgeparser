<script setup>
defineProps({
  text: {
    type: String,
    required: true,
  },
})

const emit = defineEmits(['clear'])
</script>

<template>
  <section class="terminal-panel" aria-label="Compiler terminal">
    <div class="terminal-toolbar">
      <strong>Terminal</strong>
      <div class="terminal-actions">
        <button class="ghost-button" type="button" @click="emit('clear')">Clear</button>
      </div>
    </div>

    <pre class="terminal-output">{{ text }}</pre>
  </section>
</template>
