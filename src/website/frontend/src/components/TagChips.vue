<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'

// One tag surface, three behaviours:
//
//   static  — plain labels (the question panel, table rows)
//   link    — deep-links into the problems table filtered by that tag
//   toggle  — acts as a filter control, emitting the slug it was given
//
// A chip always carries its syllabus reference and description in the title
// attribute, so hovering a tag explains why the question earned it.
const props = defineProps({
  tags: {
    type: Array,
    default: () => [],
  },
  mode: {
    type: String,
    default: 'static', // 'static' | 'link' | 'toggle'
  },
  // Slugs to render as selected. Only meaningful in toggle mode.
  active: {
    type: Array,
    default: () => [],
  },
  // Per-slug counts shown after the label, as a Map. Only used in toggle mode.
  counts: {
    type: Object,
    default: null,
  },
  // Trim to this many chips and append a "+n" marker. 0 shows all of them.
  limit: {
    type: Number,
    default: 0,
  },
  size: {
    type: String,
    default: 'normal', // 'normal' | 'small'
  },
})

const emit = defineEmits(['toggle'])

const activeSet = computed(() => new Set(props.active))
const shown = computed(() => (
  props.limit > 0 ? props.tags.slice(0, props.limit) : props.tags
))
const overflow = computed(() => Math.max(0, props.tags.length - shown.value.length))

function titleFor(tag) {
  return `${tag.syllabus_ref} ${tag.section_label} — ${tag.description}`
}

function countFor(tag) {
  if (!props.counts) return null
  // A facet with no remaining matches still renders, greyed, so the vocabulary
  // does not appear to shift under the user as they narrow the search.
  return props.counts.get?.(tag.slug) ?? 0
}
</script>

<template>
  <ul v-if="shown.length" class="tag-chips" :class="[`size-${size}`, `mode-${mode}`]">
    <li v-for="tag in shown" :key="tag.slug">
      <RouterLink
        v-if="mode === 'link'"
        class="tag-chip"
        :to="{ name: 'problems', query: { tags: tag.slug } }"
        :title="titleFor(tag)"
      >{{ tag.label }}</RouterLink>

      <button
        v-else-if="mode === 'toggle'"
        class="tag-chip"
        type="button"
        :class="{ active: activeSet.has(tag.slug), empty: countFor(tag) === 0 }"
        :aria-pressed="activeSet.has(tag.slug)"
        :title="titleFor(tag)"
        @click="emit('toggle', tag.slug)"
      >
        {{ tag.label }}
        <span v-if="counts" class="tag-count">{{ countFor(tag) }}</span>
      </button>

      <span v-else class="tag-chip" :title="titleFor(tag)">{{ tag.label }}</span>
    </li>
    <li v-if="overflow" class="tag-overflow">+{{ overflow }}</li>
  </ul>
</template>
