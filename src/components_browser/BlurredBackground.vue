<script setup lang="ts">
import { ref } from 'vue'
import { codeToIcon, codeToSubject } from '../constants/codeMaps'
import Card from './Card.vue'

const subjectCodes = [
  "0620", "0625", "0610", "0580", "0607", "0606",
  "0478", "0417", "0460", "0495", "0457", "0455",
  "0452", "0500", "0475", "0520", "0530", "0411",
  "0697", "0410", "0680", "0400", "0445", "0470",
  "9990", "0450", "0454", "0413", "8001", "0471",
  "0648", "0490"
]

function getRandomCards(count = 10) {
  const cards = []
  for (let i = 0; i < count; i++) {
    const code = subjectCodes[Math.floor(Math.random() * subjectCodes.length)]
    cards.push({
      subject: codeToSubject[code] || 'Unknown Subject',
      code,
      variant: 'Paper 2: Extended MCQs',
      condensed: `${code}/s24/21`,
      icon: codeToIcon[code] || '',
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
          v-bind="card"
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