<script setup>
import { computed, ref } from 'vue'
import {
  imageIsAvailable,
  rememberUnavailableImage,
} from '@/lib/ide/imageAvailability'
import { markerLabel, marksFor } from '@/lib/ide/records'
import { recordTags } from '@/lib/ide/tags'
import SelectableQuestionImage from '@/components_ide/SelectableQuestionImage.vue'
import TagChips from '@/components_ide/TagChips.vue'

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
})

// The mark scheme stays hidden until the answer is submitted (see ResultsPanel);
// here we only offer the *question* context, which is safe to read while working.
const showContext = ref(false)

// Tags name the technique the question wants ("post-condition-loop",
// "linear-search"), which on some questions is half the thing being assessed.
// They stay behind a toggle for the same reason the mark scheme does, rather
// than sitting open next to a problem the student has not attempted yet.
const showTags = ref(false)
const tags = computed(() => recordTags(props.record))
const unavailableImages = ref(new Set())

const questionLayout = computed(() => props.layout?.question || null)
const contextLayout = computed(() => props.layout?.context || null)
const questionImage = computed(() => props.layout?.image || null)
const contextImage = computed(() => props.layout?.context_image || null)
const hasContext = computed(() => Boolean(contextImage.value))

function markImageUnavailable(image) {
  rememberUnavailableImage(unavailableImages.value, image)
}

const useQuestionImage = computed(
  () => imageIsAvailable(questionImage.value, unavailableImages.value),
)
const useContextImage = computed(
  () => imageIsAvailable(contextImage.value, unavailableImages.value),
)
</script>

<template>
  <section class="panel question-panel">
    <template v-if="record">
      <div class="panel-title-row">
        <h1>Question</h1>
        <div class="question-head-actions">
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
        </div>
      </div>

      <p class="question-meta">{{ record.paper_code }} | {{ markerLabel(record) }}</p>

      <TagChips v-if="showTags" :tags="tags" mode="link" class="question-tags" />

      <div class="qview">
        <section v-if="showContext" class="question-context" aria-label="Question context">
          <h2>Context</h2>
          <SelectableQuestionImage
            v-if="useContextImage"
            :layout="contextLayout"
            :image="contextImage"
            alt="Question context"
            @error="markImageUnavailable(contextImage)"
          />
          <p v-else class="notice">Question context image unavailable.</p>
        </section>

        <SelectableQuestionImage
          v-if="useQuestionImage"
          :layout="questionLayout"
          :image="questionImage"
          alt="Question"
          @error="markImageUnavailable(questionImage)"
        />
        <p v-else class="notice">Question image unavailable.</p>
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
