<script setup>
import { computed } from 'vue'
import { markerLabel } from '@/services/records'

const props = defineProps({
  record: {
    type: Object,
    default: null,
  },
  // grading-result/v1 payload, or null before a response arrives.
  grading: {
    type: Object,
    default: null,
  },
  submitting: {
    type: Boolean,
    default: false,
  },
  error: {
    type: String,
    default: '',
  },
})

const emit = defineEmits(['close'])

const markScheme = computed(() => props.grading?.mark_scheme || props.record?.mark_scheme || {})
const markingPoints = computed(() => markScheme.value.marking_points || [])
const answerText = computed(() => markScheme.value.answer_text || '')
const result = computed(() => props.grading?.result || null)
const points = computed(() => result.value?.points || [])

function marksLabel(point) {
  const marks = point.marks ?? 1
  return `${marks} mark${marks === 1 ? '' : 's'}`
}
</script>

<template>
  <section class="results-panel" aria-label="Submission results">
    <div class="results-header">
      <h1>Results — {{ record?.paper_code }} {{ record ? markerLabel(record) : '' }}</h1>
      <button class="ghost-button" type="button" @click="emit('close')">Close</button>
    </div>

    <div class="results-grid">
      <!-- Mark scheme: hidden until now, revealed on submit. -->
      <section class="results-card">
        <h2>Mark Scheme</h2>
        <div v-if="markingPoints.length" class="mark-points">
          <div v-for="point in markingPoints" :key="point.id" class="mark-point">
            <strong>{{ point.id }}</strong>
            <span>{{ point.text }}</span>
            <small>{{ marksLabel(point) }} | {{ point.style || 'unknown' }}</small>
          </div>
        </div>
        <p v-else class="notice">No structured marking points were extracted.</p>

        <details class="ms-answer">
          <summary>Mark-scheme answer text</summary>
          <pre class="plain-pre">{{ answerText || 'No answer text.' }}</pre>
        </details>
      </section>

      <!-- Grading AI output. -->
      <section class="results-card">
        <div class="grading-title">
          <h2>AI Grading</h2>
          <span v-if="grading?.dry_run" class="dry-badge">dry run</span>
          <span v-else-if="grading?.model" class="model-badge">{{ grading.model }}</span>
        </div>

        <div v-if="submitting" class="notice">Grading your answer…</div>
        <div v-else-if="error" class="error-box">{{ error }}</div>
        <div v-else-if="grading && !grading.ok" class="error-box">
          Grading failed: {{ grading.error }}
        </div>

        <template v-else-if="result">
          <div class="score-row">
            <span class="score">{{ result.total_awarded }} / {{ result.max_marks }}</span>
            <span class="score-label">marks awarded</span>
          </div>

          <div v-for="point in points" :key="point.marking_point_id" class="grade-point">
            <div class="grade-point-head">
              <span class="award" :class="{ yes: point.awarded }">
                {{ point.awarded ? '✓' : '✗' }}
              </span>
              <strong>{{ point.marking_point_id }}</strong>
              <small>{{ point.marks_awarded }} mark(s)</small>
              <small v-if="point.confidence" class="confidence">{{ point.confidence }}</small>
            </div>
            <p v-if="point.evidence" class="evidence">{{ point.evidence }}</p>
            <ul v-if="point.concerns && point.concerns.length" class="concerns">
              <li v-for="(concern, index) in point.concerns" :key="index">{{ concern }}</li>
            </ul>
          </div>

          <p v-if="result.overall_explanation" class="overall">{{ result.overall_explanation }}</p>
        </template>

        <div v-else class="notice">Submit an answer to see grading.</div>
      </section>
    </div>
  </section>
</template>
