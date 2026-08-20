<script setup>
import CodeEditor from '@/components_ide/CodeEditor.vue'

defineProps({
  source: {
    type: String,
    required: true,
  },
  grading: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['update:source', 'run', 'format', 'submit'])
</script>

<template>
  <section class="panel editor-panel">
    <div class="panel-title-row">
      <h1>Editor</h1>
      <div class="editor-actions">
        <button class="primary-button" type="button" @click="emit('run')">Run</button>
        <button class="secondary-button" type="button" @click="emit('format')">Format</button>
        <button
          class="submit-button"
          type="button"
          :disabled="grading"
          @click="emit('submit')"
        >
          {{ grading ? 'Grading…' : 'Submit' }}
        </button>
      </div>
    </div>

    <CodeEditor :model-value="source" @update:model-value="emit('update:source', $event)" />
  </section>
</template>
