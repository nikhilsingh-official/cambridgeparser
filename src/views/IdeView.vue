<script setup>
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import BlankFieldsPanel from '@/components_ide/BlankFieldsPanel.vue'
import EditorPanel from '@/components_ide/EditorPanel.vue'
import ProblemExplorer from '@/components_ide/ProblemExplorer.vue'
import QuestionPanel from '@/components_ide/QuestionPanel.vue'
import ResultsPanel from '@/components_ide/ResultsPanel.vue'
import TerminalPanel from '@/components_ide/TerminalPanel.vue'
import {
  assembleFillSource,
  fillBlankFields,
  isFillBlankQuestion,
  loadQuestionLayouts,
  loadQuestionRecords,
  markerLabel,
} from '@/lib/ide/records'
import { formatPseudocode } from '@/lib/ide/staticParser'
import { parsePseudocode } from '@/lib/ide/wasmParser'
import { gradeSubmission } from '@/lib/ide/grading'
// read-only. The submission itself is recorded server-side by
// the grade Edge Function, so this only asks what the database now says.
import { useIdeProgress } from '@/lib/ide/useIdeProgress'

const route = useRoute()
const router = useRouter()
const { progress, refresh: refreshProgress } = useIdeProgress()

const state = reactive({
  loading: true,
  error: '',
  records: [],
  layouts: {},
  selectedId: null,
  source: '',
  terminalText: 'Loading static question records...',
})

// Everything the mark scheme / grading reveals stays here, hidden until submit.
const results = reactive({
  show: false,
  submitting: false,
  grading: null,
  error: '',
})
const resultsRef = ref(null)

const selectedRecord = computed(() => (
  state.records.find((record) => record.id === state.selectedId) || null
))
const selectedLayout = computed(() => (
  state.selectedId == null ? null : state.layouts[String(state.selectedId)] || null
))

// Fill-in-the-blank questions are answered by typing into the question's blanks
// rather than the code editor, so the editor and its Run button are hidden and
// the answer is assembled from the separate fields panel on submit.
const isFillBlank = computed(() => isFillBlankQuestion(
  selectedRecord.value,
  selectedLayout.value?.question,
))
const fillValues = reactive({})

const showEditor = computed(() => !isFillBlank.value)
const showBlankFields = computed(() => isFillBlank.value)

// The blanks for the fields panel: each blank in reading order with the text of
// the line it sits on as its context. Derived from the question layout tokens so
// the keys match the fillValues store used by assembleFillSource.
const blankFields = computed(() => {
  const layout = selectedLayout.value?.question
  return fillBlankFields(layout).map((blank, i) => ({
    key: blank.key,
    index: i + 1,
    context: blank.context,
  }))
})

function clearFillValues() {
  for (const key of Object.keys(fillValues)) delete fillValues[key]
}

// Rebuild pseudocode from a positioned layout with the blanks filled in: group
// tokens by reconstructed line, order each line left-to-right, and substitute
// the typed value for each blank. Approximate spacing is fine -- the grader
// reads the completed code, it is not re-typeset.
function sourceKey(id) {
  return `cambridge-ide-source:${id}`
}

function loadSource(id) {
  return window.localStorage.getItem(sourceKey(id)) || ''
}

function resetResults() {
  results.show = false
  results.submitting = false
  results.grading = null
  results.error = ''
}

function selectRecord(id, replace = false) {
  if (id == null) return
  state.selectedId = Number(id)
  state.source = loadSource(state.selectedId)
  clearFillValues()
  resetResults()
  const record = selectedRecord.value
  state.terminalText = record
    ? `Loaded ${record.paper_code || ''} ${markerLabel(record)}. Write your answer, then Run or Submit.`
    : 'No record selected.'

  // route renamed to the merged router's name.
  const target = { name: 'IdeRecord', params: { id: state.selectedId } }
  if (replace) router.replace(target)
  else router.push(target)
}

async function runParser() {
  if (!state.source.trim()) {
    state.terminalText = '(editor is empty)'
    return
  }

  state.terminalText = 'Compiling...'
  try {
    const result = await parsePseudocode(state.source)
    const lines = []
    // Program output first (the compiler currently emits none, but this stays
    // correct if execution is added later).
    if (result.stdout) lines.push(result.stdout)
    for (const diagnostic of result.diagnostics) {
      const where = diagnostic.column
        ? `line ${diagnostic.line}:${diagnostic.column}`
        : `line ${diagnostic.line}`
      lines.push(`${diagnostic.severity}: ${where}: ${diagnostic.message}`)
      if (diagnostic.hint) lines.push(`  hint: ${diagnostic.hint}`)
    }
    if (result.ok && !result.stdout) lines.push('✓ Parsed OK — no diagnostics.')
    state.terminalText = lines.join('\n')
  } catch (error) {
    state.terminalText = `Compiler error: ${String(error.message || error)}`
  }
}

async function submitAnswer() {
  const record = selectedRecord.value
  if (!record) return

  // Fill-blank answers come from the question's blanks; everything else from the
  // editor. Assemble the completed pseudocode either way.
  const source = isFillBlank.value
    ? assembleFillSource(selectedLayout.value?.question, fillValues)
    : state.source
  if (!source.trim()) {
    state.terminalText = isFillBlank.value
      ? '(nothing to submit — no blanks filled in)'
      : '(nothing to submit — the editor is empty)'
    return
  }

  results.grading = null
  results.error = ''
  results.submitting = true
  results.show = true
  await nextTick()
  resultsRef.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })

  try {
    // A blank-answer sheet is intentionally not reconstructed pseudocode: PDF
    // extraction can omit fixed operators. The AI grades its ordered answers
    // against the server's trusted question and rubric.
    const parse = isFillBlank.value
      ? { ok: false, statements: [], diagnostics: [] }
      : await parsePseudocode(source)
    results.grading = await gradeSubmission(
      record,
      source,
      parse,
      isFillBlank.value ? 'fill_blank_sheet' : 'pseudocode',
    )
    // the endpoint has already written the attempt by the time it answers,
    // so re-reading here is what moves the explorer badge. Not awaited into the
    // same try as the grade: a stale badge must not turn a successful marking
    // into an error message.
    refreshProgress().catch(() => {})
  } catch (error) {
    results.error = String(error.message || error)
  } finally {
    results.submitting = false
  }
}

function clearTerminal() {
  state.terminalText = 'Ready.'
}

function updateSource(value) {
  state.source = value
  if (state.selectedId != null) {
    window.localStorage.setItem(sourceKey(state.selectedId), value)
  }
}

function formatSource() {
  updateSource(formatPseudocode(state.source))
}

onMounted(async () => {
  try {
    const [recordsPayload, layoutsPayload] = await Promise.all([
      loadQuestionRecords(),
      loadQuestionLayouts(),
    ])
    state.records = recordsPayload.records || []
    state.layouts = layoutsPayload.layouts || {}
    const routeId = Number(route.params.id)
    const selected = state.records.some((record) => record.id === routeId)
      ? routeId
      : state.records[0]?.id
    selectRecord(selected, true)
    state.terminalText = `Loaded ${state.records.length} records and ${Object.keys(state.layouts).length} reconstructed layouts.`
  } catch (error) {
    state.error = String(error.message || error)
    state.terminalText = state.error
  } finally {
    state.loading = false
  }
})

watch(
  () => route.params.id,
  (id) => {
    if (!state.records.length) return
    const numericId = Number(id)
    if (Number.isInteger(numericId) && numericId !== state.selectedId) {
      selectRecord(numericId, true)
    }
  },
)
</script>

<template>
  <div class="ide-page" data-page="ide">
    <main class="ide-shell">
      <ProblemExplorer
        :records="state.records"
        :selected-id="state.selectedId"
        :progress="progress"
        @select="selectRecord"
      />

      <div class="workspace">
        <div v-if="state.error" class="error-box">{{ state.error }}</div>
        <div v-else-if="state.loading" class="notice">Loading records...</div>

        <div class="work-grid">
          <QuestionPanel
            :record="selectedRecord"
            :layout="selectedLayout"
          />
          <EditorPanel
            v-if="showEditor"
            :source="state.source"
            :grading="results.submitting"
            @update:source="updateSource"
            @run="runParser"
            @format="formatSource"
            @submit="submitAnswer"
          />
          <BlankFieldsPanel
            v-else-if="showBlankFields"
            :fields="blankFields"
            :blanks="fillValues"
            :grading="results.submitting"
            @submit="submitAnswer"
          />
        </div>

        <TerminalPanel :text="state.terminalText" @clear="clearTerminal" />
      </div>
    </main>

    <div ref="resultsRef">
      <ResultsPanel
        v-if="results.show"
        :record="selectedRecord"
        :grading="results.grading"
        :submitting="results.submitting"
        :error="results.error"
        @close="results.show = false"
      />
    </div>
  </div>
</template>
