<script setup lang="ts">
import { Copy, Flag, Star, Save } from 'lucide-vue-next';
// Flag, Star, and Save use the existing toggle/logging path. Copy is a
// one-shot clipboard action and logs only after the write succeeds.
import { computed, onBeforeUnmount, ref } from 'vue';
// per-question flag state shared with the Overview panel.
import { QuestionFlag, getQuestion, toggleFlag } from '@/lib/state/examState';
import { handleButtonClick, type Button, type ButtonType } from '@/lib/buttons';
// event log and active question come from the shared exam session rather
// than props, so ToolsContainer (which sits in between and has no reason to
// know about either) stays untouched.
import { getExamSession } from './composable';
// Copy is a one-shot action, so log it directly instead of toggling state.
import { logButton } from '@/lib/utils/addEventLog';
import { ButtonAction } from '@/lib/types/enums';

const { eventLogs, activeQuestionNumber, activeQuestionText } = getExamSession();

// review mode renders the saved state without permitting further changes.
const props = defineProps<{ disabled?: boolean }>();

// Copy has no toggle state; only the three persistent flags use Button.
// `parent` carries the question number that handleButtonClick logs against; it
// is refreshed on every click so the log always names the focused question.
type ToggleButtonType = Exclude<ButtonType, 'Copy'>;
const buttons = ref<Record<ToggleButtonType, Button>>({
  Flag: { type: 'Flag', state: false },
  Star: { type: 'Star', state: false },
  Save: { type: 'Save', state: false },
});

// BUG FIX - these three button states were global, not per question. Flagging
// question 3 left the Flag button lit when the student moved to question 4, so
// the panel asserted a flag that did not exist on that question. State now lives
// per question in examState, and the buttons render the ACTIVE question's flags.
const FLAG_FOR_BUTTON: Record<ToggleButtonType, QuestionFlag> = {
  Flag: QuestionFlag.Flagged,
  Star: QuestionFlag.Difficult,
  Save: QuestionFlag.Saved,
};

const activeFlags = computed(() => {
  const q = getQuestion(activeQuestionNumber());
  return {
    Flag: q?.flagged ?? false,
    Star: q?.difficult ?? false,
    Save: q?.saved ?? false,
  } as Record<ToggleButtonType, boolean>;
});

// focus areas are registered asynchronously; never create/log question 0
// while the paper is still loading or before the student selects a question.
const hasActiveQuestion = computed(() => activeQuestionNumber() > 0);

function onButtonClick(type: ToggleButtonType) {
  if (props.disabled || !hasActiveQuestion.value) return;
  const questionNum = activeQuestionNumber();
  const button = buttons.value[type];
  // handleButtonClick derives Selection/Deselection from state. Synchronize
  // it with the active question before toggling so another question's prior
  // button state cannot invert the logged action.
  button.state = activeFlags.value[type];
  button.parent = { y: 0, questionNum, buttons: [] };
  handleButtonClick(button, eventLogs());

  const flag = FLAG_FOR_BUTTON[type];
  toggleFlag(questionNum, flag);
}

// the segmented question was always available in MCQNav; it simply was not
// exposed to this nested toolbar. Copy that existing parsed text and announce
// the result without creating a second PDF extraction path.
const copyStatus = ref<'idle' | 'copied' | 'failed'>('idle');
let copyStatusTimer: number | null = null;
const canCopy = computed(() => hasActiveQuestion.value && !!activeQuestionText());
const copyLabel = computed(() => {
  if (copyStatus.value === 'copied') return 'Question copied';
  if (copyStatus.value === 'failed') return 'Question could not be copied';
  return canCopy.value ? 'Copy active question' : 'Select a question to copy it';
});

async function copyActiveQuestion() {
  if (props.disabled) return;
  const questionNumber = activeQuestionNumber();
  const text = activeQuestionText();
  if (!text || questionNumber < 1) return;

  try {
    await navigator.clipboard.writeText(text);
    logButton(eventLogs(), 'Copy', ButtonAction.Selection, questionNumber);
    copyStatus.value = 'copied';
  } catch (error) {
    console.error('copy question failed', error);
    copyStatus.value = 'failed';
  }

  if (copyStatusTimer !== null) window.clearTimeout(copyStatusTimer);
  copyStatusTimer = window.setTimeout(() => { copyStatus.value = 'idle'; }, 2_000);
}

onBeforeUnmount(() => {
  if (copyStatusTimer !== null) window.clearTimeout(copyStatusTimer);
});
</script>
<template>
  <div class="flex-wrapper">
    <!-- bound to activeFlags, which is per question. These previously read
         buttons.X.state, a single global toggle that stayed lit across questions. -->
    <button
      class="copy-question-btn"
      :aria-label="copyLabel"
      :title="copyLabel"
      :disabled="props.disabled || !canCopy"
      @click="copyActiveQuestion"
    ><Copy></Copy></button>
    <span class="copy-status" aria-live="polite">
      {{ copyStatus === 'idle' ? '' : copyLabel }}
    </span>
    <button
      class="flag-question-btn"
      aria-label="Flag active question"
      :class="{ 'btn-active': activeFlags.Flag }"
      :disabled="props.disabled || !hasActiveQuestion"
      @click="onButtonClick('Flag')"
    ><Flag></Flag></button>
    <button
      class="star-question-btn"
      aria-label="Mark active question as difficult"
      :class="{ 'btn-active': activeFlags.Star }"
      :disabled="props.disabled || !hasActiveQuestion"
      @click="onButtonClick('Star')"
    ><Star></Star></button>
    <button
      class="save-question-btn"
      aria-label="Save active question"
      :class="{ 'btn-active': activeFlags.Save }"
      :disabled="props.disabled || !hasActiveQuestion"
      @click="onButtonClick('Save')"
    ><Save></Save></button>
  </div>
</template>
<style lang="scss" scoped>
.flex-wrapper {
  /* anchor the visually-hidden clipboard status inside the toolbar. */
  position: relative;
    display:flex; 
    align-items: center;
    justify-content: space-evenly;
    button {
        width: 3vw;
        aspect-ratio: 1/1;
        background-color: transparent;
        border: none;
        cursor: pointer;

        &:disabled {
            cursor: not-allowed;
            opacity: 0.35;
        }
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

  /* announce clipboard success/failure without adding toolbar clutter. */
  .copy-status {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border: 0;
  }
}
</style>
