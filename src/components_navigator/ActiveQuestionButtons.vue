<script setup lang="ts">
import { Copy, Flag, Star, Save } from 'lucide-vue-next';
// these four buttons were pure markup - no click handlers, no logging. That
// meant markedForReview / markedAsDifficult / markedForSave were 0 in every row
// ever written, which in enrichAnalytics pins markReviewScore, markDifficultScore
// and markSaveScore at 1.0. Those carry 0.4 of confidence, 0.4 of difficulty and
// 0.35 of interest, so three headline metrics were effectively constant.
// Wired here to the existing handleButtonClick -> addEventLog path.
import { ref } from 'vue';
import { handleButtonClick, type Button, type ButtonType } from '@/lib/buttons';
// event log and active question come from the shared exam session rather
// than props, so ToolsContainer (which sits in between and has no reason to
// know about either) stays untouched.
import { getExamSession } from './composable';

const { eventLogs, activeQuestionNumber } = getExamSession();

// one Button record per type, matching the shape lib/buttons expects.
// `parent` carries the question number that handleButtonClick logs against; it
// is refreshed on every click so the log always names the focused question.
const buttons = ref<Record<ButtonType, Button>>({
  Copy: { type: 'Copy', state: false },
  Flag: { type: 'Flag', state: false },
  Star: { type: 'Star', state: false },
  Save: { type: 'Save', state: false },
});

function onButtonClick(type: ButtonType) {
  const button = buttons.value[type];
  button.parent = { y: 0, questionNum: activeQuestionNumber(), buttons: [] };
  handleButtonClick(button, eventLogs());
}
</script>
<template>
<div class="flex-wrapper">
    <!-- added @click and the active-state class binding; markup otherwise unchanged. -->
    <button class="copy-question-btn" :class="{ 'btn-active': buttons.Copy.state }" @click="onButtonClick('Copy')"><Copy></Copy></button>
    <button class="flag-question-btn" :class="{ 'btn-active': buttons.Flag.state }" @click="onButtonClick('Flag')"><Flag></Flag></button>
    <button class="star-question-btn" :class="{ 'btn-active': buttons.Star.state }" @click="onButtonClick('Star')"><Star></Star></button>
    <button class="save-question-btn" :class="{ 'btn-active': buttons.Save.state }" @click="onButtonClick('Save')"><Save></Save></button>
</div>
</template>
<style lang="scss" scoped>
.flex-wrapper {
    display:flex; 
    align-items: center;
    justify-content: space-evenly;
    button {
        width: 3vw;
        aspect-ratio: 1/1;
        background-color: transparent;
        border: none;
        cursor: pointer;
    }
    .copy-question-btn {
        svg {
            stroke: $accent;
        }
    }
    .flag-question-btn {
        svg {
            stroke: $danger;
        }
    }
    .star-question-btn {
        svg {
            stroke: $warning;
        }
    }
    .save-question-btn {
        svg {
            stroke: $success;
        }
    }
    /* added so a toggled-on flag is visible. handleButtonClick also adds
       .btn-active / .btn-inactive to the element it owns; this styles ours. */
    .btn-active {
        svg {
            fill: currentColor;
            opacity: 1;
        }
    }
    button:not(.btn-active) {
        svg {
            opacity: 0.55;
        }
    }
}
</style>