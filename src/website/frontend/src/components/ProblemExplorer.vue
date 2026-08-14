<script setup>
import { computed, ref } from 'vue'
import FilterPanel from '@/components/FilterPanel.vue'
import TagChips from '@/components/TagChips.vue'
import { recordSummary } from '@/services/records'
import { MATCH_ANY, filterRecords, recordTags } from '@/services/tags'

const props = defineProps({
  records: {
    type: Array,
    required: true,
  },
  selectedId: {
    type: Number,
    default: null,
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
</script>

<template>
  <aside class="explorer">
    <div class="explorer-header">
      <h2>Problems</h2>
      <span>{{ records.length }}</span>
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
        <strong>{{ recordSummary(record).paperCode }}</strong>
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
