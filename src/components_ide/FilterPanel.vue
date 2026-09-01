<script setup>
import { computed } from 'vue'
import TagChips from '@/components_ide/TagChips.vue'
import {
  MATCH_ALL,
  MATCH_ANY,
  buildTagIndex,
  facetCounts,
  groupTagsBySection,
} from '@/lib/ide/tags'

// Search box + syllabus-tag facets, shared by the problems table ('page') and
// the IDE explorer ('compact'). The compact variant collapses the facet list
// behind a <details> so it does not swallow the narrow sidebar; the page
// variant leaves it open, since browsing by topic is the point of that screen.
const props = defineProps({
  // Every record in the corpus. Facets and their counts are derived from these,
  // so the panel needs no vocabulary of its own.
  records: {
    type: Array,
    default: () => [],
  },
  query: {
    type: String,
    default: '',
  },
  tags: {
    type: Array,
    default: () => [],
  },
  mode: {
    type: String,
    default: MATCH_ANY,
  },
  // Records left after filtering, shown as "n of m".
  resultCount: {
    type: Number,
    default: 0,
  },
  variant: {
    type: String,
    default: 'page', // 'page' | 'compact'
  },
})

const emit = defineEmits(['update:query', 'update:tags', 'update:mode'])

const groups = computed(() => groupTagsBySection(buildTagIndex(props.records)))
const counts = computed(() => facetCounts(props.records, props.query))
const activeCount = computed(() => props.tags.length)
const isFiltered = computed(() => activeCount.value > 0 || props.query.trim() !== '')

function toggleTag(slug) {
  const next = props.tags.includes(slug)
    ? props.tags.filter((existing) => existing !== slug)
    : [...props.tags, slug]
  emit('update:tags', next)
}

function clearAll() {
  emit('update:query', '')
  emit('update:tags', [])
}
</script>

<template>
  <div class="filter-panel" :class="`variant-${variant}`">
    <input
      class="filter-search"
      :value="query"
      type="search"
      placeholder="Search questions, mark schemes, tags"
      aria-label="Search questions, mark schemes and tags"
      @input="emit('update:query', $event.target.value)"
    >

    <div class="filter-status">
      <span class="count-pill">{{ resultCount }} of {{ records.length }}</span>
      <button
        v-if="isFiltered"
        class="ghost-button filter-clear"
        type="button"
        @click="clearAll"
      >Clear</button>
    </div>

    <details class="facets" :open="variant === 'page'">
      <summary>
        <span>Syllabus tags</span>
        <span v-if="activeCount" class="count-pill">{{ activeCount }} on</span>
      </summary>

      <div class="facet-mode">
        <span class="facet-mode-label">Match</span>
        <div class="view-toggle" role="group" aria-label="Tag match mode">
          <!-- expose the selected segmented-control value to assistive technology. -->
          <button
            type="button"
            :class="{ active: mode === MATCH_ANY }"
            :aria-pressed="mode === MATCH_ANY"
            title="Show questions carrying any of the selected tags"
            @click="emit('update:mode', MATCH_ANY)"
          >Any</button>
          <button
            type="button"
            :class="{ active: mode === MATCH_ALL }"
            :aria-pressed="mode === MATCH_ALL"
            title="Show only questions carrying every selected tag"
            @click="emit('update:mode', MATCH_ALL)"
          >All</button>
        </div>
      </div>

      <div class="facet-groups">
        <section v-for="group in groups" :key="group.section" class="facet-group">
          <h3>{{ group.section }} {{ group.label }}</h3>
          <TagChips
            :tags="group.tags"
            mode="toggle"
            size="small"
            :active="tags"
            :counts="counts"
            @toggle="toggleTag"
          />
        </section>
      </div>
    </details>
  </div>
</template>
