<script setup lang="ts">
import { computed, type CSSProperties } from 'vue';
import { codeToBg, codeToSubject, categoryToIcon, categoryToText, categoryIsSubjectSpecific } from '../constants/codeMaps';
// the `category` prop was `number`, which accepted any integer including
// ones with no card behind them. StatCategory restricts it to the 17 that exist.
import type { StatCategory } from '@/lib/types/enums';

const { category, text, metricData } = defineProps<{
  category: StatCategory;
  text: string;
  metricData: string;
}>();

// these three were plain `let`/`const` evaluated ONCE at setup, from
// destructured props. That was invisible while CardStrip rendered a fixed
// `testStats` array - the props never changed - but the strip is now computed
// from live attempts, and v-for reuses component instances across a data
// change. The result was cards showing one card's heading over another card's
// value: whatever each slot held on the very first render, when the query had
// not resolved and every total was zero.
//
// `computed` re-derives when the props do. The same reason bgPositionStyle
// below was already a computed.
const finalText = computed(() =>
  categoryIsSubjectSpecific[category] ? codeToSubject[text] + " " + text : text);

const header = computed(() => categoryToText[category]);

const scienceSubjects: string[] = ["0620", "0625", "0610", "0654", "0653", "0680", "0697"];

const background = computed(() =>
  categoryIsSubjectSpecific[category] ? codeToBg[text] : codeToBg["default"]);

const bgPositionStyle = computed<CSSProperties>(() => ({
  left: scienceSubjects.includes(text) ? '50%' : '0%'
}));

</script>
<template>
    <div class="card-container">
        <div class="half text-half">
            <div class="header-box">
                <p>{{ header }}</p>
                <h3>{{ finalText }}</h3>
            </div>
            <h5>{{ metricData }}</h5>
        </div>
        <img class = "bg-pattern" :src="background" :style="bgPositionStyle"/>
        <div class="icon-badge" v-html="categoryToIcon[category]"></div>
        <div class = "bg-icon" v-html="categoryToIcon[category]"></div>
    </div>
</template>
<style lang="scss" scoped>
.card-container {
    position: relative;
    width: 100%;
    height: 100%;
    border-radius: 10px;
    display: flex;
    background-color: $secondary-background;
    overflow: hidden;
    padding: 1rem
}
.half {
    @extend %filler;
}
.bg-pattern {
    z-index: 0;
    opacity: 0.1;
    width: 100%;
    aspect-ratio: 1/1;
    object-fit: cover;
    position: absolute;
    top: -50%;
}
.text-half {
    display: flex;
    flex-direction: column;
    justify-content: center;
    color: $text;
    row-gap: 10px;
    .header-box {
        display: flex;
        flex-direction: column;
    }
    p {
        font-family: 'Lexend';
        font-weight: 200;
    }
    h3 {
        font-family: 'Inter';
        font-weight: 700;
    }
    h5 {
        font-family: 'Kode Mono';
    }
}
.icon-badge {
    position: absolute;
    top: 0;
    right: 0;
    border-radius: 50%;
    margin: 10px;
    padding: 7.5px;
    width: 35px;
    aspect-ratio: 1/1;
    color: $accent;
    border: $primary-color 1px solid;
    display: flex;
    align-items: center;
    justify-content: center;
    svg {
        object-fit: contain;
    }
    background-color: $background;
    z-index: 7;
    box-shadow: 0 0 5px 3px $primary-color;
}
.bg-icon {
    position: absolute;
    top: 70%;
    transform: translate(-50%, -50%);
    left: 75%;
    opacity: 0.4;
    color: $text;
    width: 40%;
    aspect-ratio: 1/1;
    color: $primary-color;
    z-index: 5;
}
</style>