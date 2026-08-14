<script setup>
import { computed, ref } from 'vue'
import { cleanContextText, markerLabel, marksFor } from '@/services/records'
import { recordTags } from '@/services/tags'
import PositionedQuestion from '@/components/PositionedQuestion.vue'
import TagChips from '@/components/TagChips.vue'

const props = defineProps({
  record: {
    type: Object,
    default: null,
  },
  // Layout entry: { question, context, image, context_image } — each layout is a
  // positioned token model; each image is { src, width, height } (or null).
  layout: {
    type: Object,
    default: null,
  },
  // 'image' (default, trusted) or 'position' (reconstructed-from-text tokens).
  viewMode: {
    type: String,
    default: 'image',
  },
  // Fill-in-the-blank mode. In *position* mode the blanks are inline and this
  // panel owns Submit; in *image* mode the blanks live in BlankFieldsPanel.
  fillMode: {
    type: Boolean,
    default: false,
  },
  // Shared blank-value store, read back by the IDE to assemble the submission.
  blanks: {
    type: Object,
    default: null,
  },
  grading: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['submit', 'update:viewMode'])

// The mark scheme stays hidden until the answer is submitted (see ResultsPanel);
// here we only offer the *question* context, which is safe to read while working.
const showContext = ref(false)

// Tags name the technique the question wants ("post-condition-loop",
// "linear-search"), which on some questions is half the thing being assessed.
// They stay behind a toggle for the same reason the mark scheme does, rather
// than sitting open next to a problem the student has not attempted yet.
const showTags = ref(false)
const tags = computed(() => recordTags(props.record))

const RESOURCES_BASE = `${import.meta.env.BASE_URL}resources/`

const questionLayout = computed(() => props.layout?.question || null)
const contextLayout = computed(() => props.layout?.context || null)
const questionImage = computed(() => props.layout?.image || null)
const contextImage = computed(() => props.layout?.context_image || null)
const contextText = computed(() => cleanContextText(props.record))
const hasContext = computed(
  () => Boolean(contextLayout.value) || Boolean(contextImage.value) || Boolean(contextText.value),
)

function imageUrl(image) {
  return `${RESOURCES_BASE}${image.src}`
}

// Image is the default, but fall back to the positional view if no image was
// rendered for this record so the panel is never blank.
const useQuestionImage = computed(() => props.viewMode === 'image' && Boolean(questionImage.value))
const useContextImage = computed(() => props.viewMode === 'image' && Boolean(contextImage.value))

// Inline editable blanks only in position mode; in image mode the inputs are in
// the separate fields panel, so the question renders read-only there.
const questionInteractive = computed(() => props.fillMode && props.viewMode === 'position')
// This panel owns Submit only when the blanks are inline (position mode).
const ownsSubmit = computed(() => props.fillMode && props.viewMode === 'position')
</script>

<template>
  <section class="panel question-panel">
    <template v-if="record">
      <div class="panel-title-row">
        <h1>Question</h1>
        <div class="question-head-actions">
          <div class="view-toggle" role="group" aria-label="Question view">
            <button
              type="button"
              :class="{ active: viewMode === 'image' }"
              @click="emit('update:viewMode', 'image')"
            >Image</button>
            <button
              type="button"
              :class="{ active: viewMode === 'position' }"
              @click="emit('update:viewMode', 'position')"
            >Position</button>
          </div>
          <button
            v-if="hasContext"
            class="toggle-button"
            :class="{ active: showContext }"
            type="button"
            @click="showContext = !showContext"
          >
            {{ showContext ? 'Hide context' : 'Show context' }}
          </button>
          <button
            v-if="tags.length"
            class="toggle-button"
            :class="{ active: showTags }"
            type="button"
            :aria-expanded="showTags"
            @click="showTags = !showTags"
          >
            {{ showTags ? 'Hide tags' : 'Tags' }}
          </button>
          <span class="count-pill">{{ marksFor(record) }} marks</span>
          <button
            v-if="ownsSubmit"
            class="submit-button"
            type="button"
            :disabled="grading"
            @click="emit('submit')"
          >
            {{ grading ? 'Grading…' : 'Submit' }}
          </button>
        </div>
      </div>

      <p class="question-meta">{{ record.paper_code }} | {{ markerLabel(record) }}</p>

      <TagChips v-if="showTags" :tags="tags" mode="link" class="question-tags" />

      <div class="qview">
        <section v-if="showContext" class="question-context" aria-label="Question context">
          <h2>Context</h2>
          <img
            v-if="useContextImage"
            class="question-image"
            :src="imageUrl(contextImage)"
            alt="Question context"
          >
          <PositionedQuestion
            v-else-if="contextLayout"
            :record="record"
            :layout="contextLayout"
            :interactive="false"
          />
          <p v-else-if="!contextText" class="notice">No additional context for this question.</p>
          <pre v-else class="context-text">{{ contextText }}</pre>
        </section>

        <img
          v-if="useQuestionImage"
          class="question-image"
          :src="imageUrl(questionImage)"
          alt="Question"
        >
        <PositionedQuestion
          v-else
          :record="record"
          :layout="questionLayout"
          :interactive="questionInteractive"
          :blanks="blanks"
        />
      </div>
    </template>

    <template v-else>
      <div class="panel-title-row">
        <h1>Question</h1>
      </div>
      <div class="empty-panel">No question selected.</div>
    </template>
  </section>
</template>
