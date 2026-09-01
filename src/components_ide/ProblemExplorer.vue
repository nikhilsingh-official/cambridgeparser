<script setup>
import { computed, ref } from 'vue'
import FilterPanel from '@/components_ide/FilterPanel.vue'
import TagChips from '@/components_ide/TagChips.vue'
import { recordSummary } from '@/lib/ide/records'
import { MATCH_ANY, filterRecords, recordTags } from '@/lib/ide/tags'

const props = defineProps({
  records: {
    type: Array,
    required: true,
  },
  selectedId: {
    type: Number,
    default: null,
  },
  // per-question status, keyed by record id as a string. A Map rather than
  // an object because the explorer does one lookup per rendered row against a
  // list of hundreds. Empty signed out, which is why the badge is v-if'd rather
  // than rendered as an empty state.
  progress: {
    type: Map,
    default: () => new Map(),
  },
})

const emit = defineEmits(['select'])

const query = ref('')
const tags = ref([])
const mode = ref(MATCH_ANY)

const filteredRecords = computed(() => filterRecords(props.records, {
  query: query.value,
  tags: tags.value,
  mode: mode.value,
}))

// 'not_started' rows exist in the table but mean the same thing as no row
// at all, so both come back as null and the badge is not rendered.
function statusOf(record) {
  const row = props.progress.get(String(record.id))
  if (!row || row.status === 'not_started') return null
  return row.status
}

function statusTitle(record) {
  const row = props.progress.get(String(record.id))
  if (!row) return ''
  const tries = `${row.attempts} submission${row.attempts === 1 ? '' : 's'}`
  return `Best ${row.best_score}/${row.max_marks} over ${tries}`
}

// Counted over every record, not over the filtered view: "8 solved" should not
// change because a search box is narrowing the list below it.
const solvedCount = computed(() => props.records.reduce(
  (n, record) => n + (statusOf(record) === 'solved' ? 1 : 0), 0,
))
</script>

<template>
  <aside class="explorer">
    <div class="explorer-header">
      <h2>Problems</h2>
      <span>{{ solvedCount ? `${solvedCount} / ${records.length} solved` : records.length }}</span>
    </div>

    <FilterPanel
      :records="records"
      :query="query"
      :tags="tags"
      :mode="mode"
      :result-count="filteredRecords.length"
      variant="compact"
      @update:query="query = $event"
      @update:tags="tags = $event"
      @update:mode="mode = $event"
    />

    <div class="problem-list">
      <button
        v-for="record in filteredRecords"
        :key="record.id"
        class="problem-link"
        :class="{ active: record.id === selectedId }"
        type="button"
        @click="emit('select', record.id)"
      >
        <span class="problem-title">
          <strong>{{ recordSummary(record).paperCode }}</strong>
          <!-- The status of a question is worth more than the paper it came
               from when you are scanning for what to do next, so it sits on
               the same line rather than below the tags. -->
          <span
            v-if="statusOf(record)"
            class="problem-status"
            :class="statusOf(record)"
            :title="statusTitle(record)"
          >{{ statusOf(record) === 'solved' ? 'solved' : 'tried' }}</span>
        </span>
        <span>{{ recordSummary(record).label }} | {{ recordSummary(record).marks }} mark(s)</span>
        <small>{{ recordSummary(record).questionText.slice(0, 90) }}</small>
        <!-- Two chips keep the row to a scannable height; the rest are on the
             question panel once the problem is open. -->
        <TagChips :tags="recordTags(record)" size="small" :limit="2" />
      </button>

      <p v-if="records.length && !filteredRecords.length" class="notice">
        No questions match these filters.
      </p>
    </div>
  </aside>
</template>
