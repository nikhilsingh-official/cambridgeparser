<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import FilterPanel from '@/components/FilterPanel.vue'
import TagChips from '@/components/TagChips.vue'
import { loadQuestionRecords, recordSummary } from '@/services/records'
import {
  MATCH_ANY,
  filterRecords,
  recordTags,
  tagsFromQueryParam,
  tagsToQueryParam,
} from '@/services/tags'

const route = useRoute()
const router = useRouter()

const records = ref([])
const error = ref('')

// Filter state lives in the URL: a filtered table is linkable, the browser Back
// button steps through filters, and the tag chips on a question can deep-link
// straight into "every question tagged bubble-sort".
const query = ref(String(route.query.q || ''))
const tags = ref(tagsFromQueryParam(route.query.tags))
const mode = ref(route.query.match === 'all' ? 'all' : MATCH_ANY)

const filteredRecords = computed(() => filterRecords(records.value, {
  query: query.value,
  tags: tags.value,
  mode: mode.value,
}))

watch([query, tags, mode], () => {
  router.replace({
    name: 'problems',
    query: {
      ...(query.value.trim() ? { q: query.value } : {}),
      ...(tags.value.length ? { tags: tagsToQueryParam(tags.value) } : {}),
      ...(mode.value === 'all' ? { match: 'all' } : {}),
    },
  })
})

// Follow deep links arriving while the view is already mounted (a tag chip
// clicked from another route lands here without remounting).
watch(() => route.query, (next) => {
  const nextQuery = String(next.q || '')
  const nextTags = tagsFromQueryParam(next.tags)
  const nextMode = next.match === 'all' ? 'all' : MATCH_ANY
  if (nextQuery !== query.value) query.value = nextQuery
  if (nextTags.join(',') !== tags.value.join(',')) tags.value = nextTags
  if (nextMode !== mode.value) mode.value = nextMode
})

onMounted(async () => {
  try {
    records.value = (await loadQuestionRecords()).records || []
  } catch (caught) {
    error.value = String(caught.message || caught)
  }
})
</script>

<template>
  <main class="page-shell" data-page="problems">
    <section class="panel page-panel">
      <div class="panel-title-row">
        <h1>Generated Problems</h1>
        <span class="count-pill">{{ records.length }} records</span>
      </div>

      <div v-if="error" class="error-box">{{ error }}</div>

      <div class="page-controls">
        <FilterPanel
          :records="records"
          :query="query"
          :tags="tags"
          :mode="mode"
          :result-count="filteredRecords.length"
          variant="page"
          @update:query="query = $event"
          @update:tags="tags = $event"
          @update:mode="mode = $event"
        />
      </div>

      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Paper</th>
              <th>Question</th>
              <th>Marks</th>
              <th>Points</th>
              <th>Question Text</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="record in filteredRecords" :key="record.id">
              <td><RouterLink :to="{ name: 'record', params: { id: record.id } }">{{ record.id }}</RouterLink></td>
              <td>{{ recordSummary(record).paperCode }}</td>
              <td>{{ recordSummary(record).label }}</td>
              <td>{{ recordSummary(record).marks }}</td>
              <td>{{ recordSummary(record).pointCount }}</td>
              <td>
                <p class="row-text">{{ recordSummary(record).questionText.slice(0, 140) }}</p>
                <TagChips :tags="recordTags(record)" mode="link" size="small" />
              </td>
            </tr>
          </tbody>
        </table>

        <p v-if="records.length && !filteredRecords.length" class="notice">
          No questions match these filters.
        </p>
      </div>
    </section>
  </main>
</template>
