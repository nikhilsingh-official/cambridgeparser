<script setup lang="ts">
// the wallpaper behind the browser header - fifty Cards at blur(14px).
// It used to build its own mock card objects with a hardcoded
// 'Paper 2: Extended MCQs' variant and a made-up `${code}/s24/21` code. Now it
// samples the real catalogue, so the blurred shapes are the same shapes the
// grid below is made of, and there is one card contract instead of two.
import { ref } from 'vue'
import Card from './Card.vue'
import { buildPaperEntries, condensedLabel } from '@/constants/paperCatalogue'
import { EXAM_SERIES_LABEL } from '@/lib/types/enums'
import { PaperProgress } from './browserFilter'
import type { PaperCard } from '@/lib/browser/usePaperBrowser'

// The whole catalogue, unfiltered - this is decoration, so variety is the
// only requirement.
const ALL = buildPaperEntries({ subjectCodes: [], examYears: [], series: [], variants: [] })

function getRandomCards(count = 10): PaperCard[] {
  const cards: PaperCard[] = []
  for (let i = 0; i < count; i++) {
    const entry = ALL[Math.floor(Math.random() * ALL.length)]
    const sessionLabel = `${EXAM_SERIES_LABEL[entry.series]} ${entry.examYear}`
    cards.push({
      ...entry,
      attempt: null,
      progress: PaperProgress.Unattempted,
      condensed: condensedLabel(entry),
      sessionLabel,
      lastAttemptedLabel: 'Never attempted',
      tags: [entry.qualification, sessionLabel],
      recommendation: null,
    })
  }
  return cards
}

const cardTracks = ref([
  getRandomCards().concat(getRandomCards()),
  getRandomCards().concat(getRandomCards()),
  getRandomCards().concat(getRandomCards()),
  getRandomCards().concat(getRandomCards()),
  getRandomCards().concat(getRandomCards()),
])

const scrollDurations = ref(
  Array.from({ length: 5 }, () =>
    `${Math.floor(Math.random() * 51) + 190}s`
  )
)
</script>

<template>
  <div class="blur-wrapper">
    <div
      v-for="(cards, i) in cardTracks"
      :key="i"
      class="track"
      :class="{ up: i < 3, down: i >= 3 }"
    >
      <div class="track-inner" :style="{ animationDuration: scrollDurations[i] }">
        <Card
          v-for="(card, index) in cards"
          :key="index"
          :card="card"
          decorative
        />
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
@keyframes scroll-up {
  0% {
    transform: translateY(0%);
  }
  100% {
    transform: translateY(-50%);
  }
}

@keyframes scroll-down {
  0% {
    transform: translateY(-50%);
  }
  100% {
    transform: translateY(0%);
  }
}

.blur-wrapper {
  width: 100%;
  height: 100%;
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  column-gap: 10px;
  filter: blur(14px);
  opacity: 0.3;
  pointer-events: none;
}

.track {
  width: 20vw;
  height: 100%;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  align-items: center;
  row-gap: 10px;
  padding: 10px;

  .track-inner {
    display: flex;
    flex-direction: column;
    row-gap: 10px;
    animation-iteration-count: infinite;
    animation-timing-function: linear;
  }

  &.up .track-inner {
    animation-name: scroll-up;
  }

  &.down .track-inner {
    animation-name: scroll-down;
  }
}
</style>