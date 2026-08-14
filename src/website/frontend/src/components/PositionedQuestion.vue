<script setup>
import { computed, reactive } from 'vue'
import { isFillBlankQuestion } from '@/services/records'

const props = defineProps({
  record: {
    type: Object,
    required: true,
  },
  layout: {
    type: Object,
    default: null,
  },
  // When false the blanks render as static placeholders (used for the read-only
  // context view). When true, a fill-in-the-blank question's blanks become
  // editable inputs.
  interactive: {
    type: Boolean,
    default: true,
  },
  // Optional external store for blank values, keyed by `${page}:${index}`. When
  // omitted (e.g. the context view) an internal store is used. Sharing the
  // caller's reactive object lets the IDE read the answers back for grading.
  blanks: {
    type: Object,
    default: null,
  },
})

const internalBlanks = reactive({})
const blankStore = computed(() => props.blanks || internalBlanks)

const useInputs = computed(() => (
  props.interactive && isFillBlankQuestion(props.record, props.layout)
))
const pages = computed(() => props.layout?.pages || [])

function tokenStyle(token) {
  return {
    left: `${token.x}px`,
    top: `${token.y}px`,
    width: `${token.w}px`,
    height: `${token.h}px`,
    fontSize: `${Math.max(10, token.h * 0.66)}px`,
  }
}

function pageStyle(page) {
  return {
    width: `${page.width}px`,
    height: `${page.height}px`,
  }
}

function blankKey(page, index) {
  return `${page.page_index}:${index}`
}

function blankStyle(token) {
  return {
    ...tokenStyle(token),
    fontSize: `${Math.max(10, token.h * 0.6)}px`,
  }
}
</script>

<template>
  <div v-if="pages.length" class="positioned-question">
    <div
      v-for="page in pages"
      :key="page.page_index"
      class="layout-page"
      :style="pageStyle(page)"
    >
      <template v-for="(token, index) in page.tokens" :key="`${page.page_index}:${index}`">
        <input
          v-if="token.kind === 'blank' && useInputs"
          v-model="blankStore[blankKey(page, index)]"
          class="layout-blank"
          type="text"
          :style="blankStyle(token)"
          aria-label="Answer blank"
        >
        <span
          v-else-if="token.kind === 'blank'"
          class="layout-blank-static"
          :style="blankStyle(token)"
          aria-hidden="true"
        />
        <span
          v-else
          class="layout-token"
          :class="{ mono: token.mono }"
          :style="tokenStyle(token)"
        >{{ token.text }}</span>
      </template>
    </div>
  </div>

  <div v-else class="qview-body fallback-text">{{ record.question_text }}</div>
</template>
