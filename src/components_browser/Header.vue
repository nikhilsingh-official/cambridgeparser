<script setup lang="ts">
// this header was a mock. Its five multiselects offered ['Wade Cooper',
// 'Arlene Mccoy', ...], ['Red','Green','Blue'], ['Cat','Dog','Rabbit'],
// ['Toyota','Honda','Ford'] and the four seasons, all bound to refs nothing
// read - so the browser could not be filtered at all. They are now bound to
// the shared BrowserFilter and their options come from the paper catalogue.
import Multiselect from '@vueform/multiselect'
import BlurredBackground from './BlurredBackground.vue'
import { computed } from 'vue'
import { CATALOGUE_SUBJECTS, CATALOGUE_YEARS } from '@/constants/paperCatalogue'
import { EXAM_SERIES_LABEL, ExamSeries } from '@/lib/types/enums'
import {
  PAPER_PROGRESS_LABEL, PaperProgress, defaultFilter, type BrowserFilter,
} from './browserFilter'

// two-way, so the page owns the filter and this component only edits it.
const filter = defineModel<BrowserFilter>({ required: true })

// how many papers the current filter yields, passed down rather than
// recomputed - the page has already built the list.
const props = defineProps<{ resultCount: number; totalCount: number }>()

const subjectOptions = CATALOGUE_SUBJECTS.map(s => ({
  value: s.code,
  label: `${s.subject} (${s.code})`,
}))

const yearOptions = CATALOGUE_YEARS.map(y => ({ value: y, label: String(y) }))

const seriesOptions = (Object.keys(EXAM_SERIES_LABEL) as ExamSeries[]).map(s => ({
  value: s,
  label: EXAM_SERIES_LABEL[s],
}))

// 1-3 rather than a distinct-over-the-catalogue, because every syllabus in
// it is sat as variants 1-3. Derived would be the same three numbers with more
// machinery.
const variantOptions = [1, 2, 3].map(v => ({ value: v, label: `Variant ${v}` }))

const progressOptions = (Object.values(PaperProgress) as PaperProgress[]).map(p => ({
  value: p,
  label: PAPER_PROGRESS_LABEL[p],
}))

// a filter that matches nothing is otherwise indistinguishable from a
// broken page - the grid just goes blank. The subheading says which it is.
const summary = computed(() => {
  if (props.totalCount === 0) return 'Loading papers...'
  if (props.resultCount === 0) return 'No papers match these filters.'
  return `${props.resultCount} paper${props.resultCount === 1 ? '' : 's'} - pick one to sit it.`
})

const isDefault = computed(() => {
  const d = defaultFilter()
  const f = filter.value
  const same = (a: unknown[], b: unknown[]) =>
    a.length === b.length && a.every(v => (b as unknown[]).includes(v))
  return (
    same(f.subjectCodes, d.subjectCodes) &&
    same(f.examYears, d.examYears) &&
    same(f.series, d.series) &&
    same(f.variants, d.variants) &&
    same(f.progress, d.progress)
  )
})

function reset() {
  // The parent owns a const reactive object, so reset its fields in place;
  // replacing the defineModel value emits an assignment the parent cannot make.
  Object.assign(filter.value, defaultFilter())
}
</script>
<template>
    <div class="header-container">
      <div class="blurred-container">
        <BlurredBackground></BlurredBackground>
      </div>
      <div class="half text-container">
        <h1 class="header-text">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-compass"><circle cx="12" cy="12" r="10"></circle><polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76"></polygon></svg>
          Paper Browser
        </h1>
        <p class="subheading-text">
          Search and explore past paper questions by year, tag, or subject.
        </p>
        <!-- the live result count. Replaces nothing - there was no
             feedback at all that a filter had done anything. -->
        <p class="result-text">{{ summary }}</p>
        <button v-if="!isDefault" class="reset-btn" @click="reset">Reset filters</button>
      </div>
      <div class="half filter-container">
        <Multiselect
          v-model="filter.subjectCodes"
          :options="subjectOptions"
          mode="tags"
          :searchable="true"
          :close-on-select="false"
          placeholder="All subjects"
        />
        <div class="time-filter">
          <Multiselect
            v-model="filter.examYears"
            :options="yearOptions"
            mode="tags"
            :searchable="true"
            :close-on-select="false"
            placeholder="Years..."
          />
          <Multiselect
            v-model="filter.series"
            :options="seriesOptions"
            mode="tags"
            :searchable="false"
            :close-on-select="false"
            placeholder="Seasons..."
          />
          <Multiselect
            v-model="filter.variants"
            :options="variantOptions"
            mode="tags"
            :searchable="false"
            :close-on-select="false"
            placeholder="Variants..."
          />
        </div>
        <Multiselect
          v-model="filter.progress"
          :options="progressOptions"
          mode="tags"
          :searchable="false"
          :close-on-select="false"
          placeholder="Any progress..."
        />
      </div>
    </div>
</template>
<style lang="scss" scoped>
.header-container {
    position: relative;
    width: 100%;
    height: 100%;
    display: flex;
}
.half {
  @extend %filler;
  padding: 3rem;
  z-index: 3;
}
.text-container {
  display: flex;
  flex-direction: column;
  justify-content: center;
  color: $text;
  .header-text {
    font-family: 'Inter';
    font-size: 50px;
    display: flex;
    align-items: center;
    column-gap: 10px;
    svg {
      height: 50px;
      aspect-ratio: 1/1;
      color: $accent;
    }
  }
  .subheading-text {
    position: relative;
    font-family: 'Lexend';
  }
  /* added with the result count and reset control. */
  .result-text {
    position: relative;
    font-family: 'Lexend';
    font-weight: 300;
    opacity: 0.7;
    margin-top: 0.5rem;
  }
  .reset-btn {
    position: relative;
    margin-top: 1rem;
    width: fit-content;
    padding: 0.5rem 1rem;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-family: 'Lexend';
    color: $text;
    background: $secondary-background;
    transition: background 0.3s ease;

    &:hover { background: $tertiary-background; }
  }
}
.filter-container {
    display: flex;
    align-items: center;
    justify-content: center;
    flex-direction: column;
    row-gap: 10px;
    .time-filter {
      display: flex;
      column-gap: 10px;
      width: 100%;
    }
}
.multiselect {
  /* Vue 3's functional :deep() syntax replaces deprecated ::v-deep
     combinators for the third-party multiselect internals below. */
  font-family: 'Lexend';
  border: none;
  background: $secondary-background;
  outline: none;
  transition: background 1s ease;

  &:hover {
    background-color: $tertiary-background;
  }

  :deep(.multiselect-tag) {
    background-color: $primary-color;
  }

  :deep(.multiselect-tags-search) {
    background-color: transparent;
    color: $text;
  }

  :deep(.multiselect-dropdown) {
    background-color: $tertiary-background;
    color: $text;
    border: none;

    .multiselect-option {
      background-color: $tertiary-background;
    }

    .multiselect-option.is-pointed {
      background-color: $secondary-background;
      color: white !important;
    }

    .multiselect-no-results {
      color: $text !important;
    }
  }
}

:deep(.multiselect.is-active) {
  border: none !important;
  box-shadow: none !important;
}

.blurred-container {
  position: absolute;
  top: 0;
  left: -12.5%;
  width: 125%;
  height: 100%;
  z-index: 0;
}
</style>
