<script setup>
// Right-hand panel for fill-in-the-blank questions. Because a
// flat question image can't host inline inputs, each blank gets its own row: a
// description (the text of the line the blank sits on — its "context") and an
// input. Values are written into the shared `blanks` store keyed by the blank's
// id so the IDE can assemble the completed pseudocode for grading.

defineProps({
  fields: {
    type: Array,
    default: () => [],
  },
  blanks: {
    type: Object,
    required: true,
  },
  grading: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['submit'])
</script>

<template>
  <section class="panel blanks-panel">
    <div class="panel-title-row">
      <h1>Fill in the blanks</h1>
      <button
        class="submit-button"
        type="button"
        :disabled="grading"
        @click="emit('submit')"
      >
        {{ grading ? 'Grading…' : 'Submit' }}
      </button>
    </div>

    <div class="blanks-body">
      <p v-if="!fields.length" class="notice">No blanks detected for this question.</p>

      <div v-for="field in fields" :key="field.key" class="blank-field">
        <label :for="`blank-${field.key}`" class="blank-context">
          <span class="blank-index">{{ field.index }}</span>
          <span class="blank-line">{{ field.context || '(blank)' }}</span>
        </label>
        <input
          :id="`blank-${field.key}`"
          v-model="blanks[field.key]"
          class="blank-input"
          type="text"
          autocomplete="off"
          spellcheck="false"
          placeholder="Your answer"
        >
      </div>
    </div>
  </section>
</template>
