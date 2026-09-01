<script setup lang="ts">
import { Square, RotateCcw, Save } from 'lucide-vue-next';
import { onBeforeUnmount, ref } from 'vue';
// review mode disables the paper-level controls.
const props = defineProps<{ disabled?: boolean }>();
// stopping uses the same persisted end-exam lifecycle as the bottom bar.

const emit = defineEmits<{ (e: 'endExam'): void }>();
const confirming = ref(false);
let confirmTimer: ReturnType<typeof window.setTimeout> | undefined;

function stopPaper() {
    if (props.disabled) return;
    if (!confirming.value) {
        confirming.value = true;
        confirmTimer = window.setTimeout(() => { confirming.value = false; }, 4000);
        return;
    }
    emit('endExam');
}

onBeforeUnmount(() => {
    if (confirmTimer !== undefined) window.clearTimeout(confirmTimer);
});
</script>
<template>
<div class="flex-wrapper">
    <!-- a second click confirms the irreversible end action. -->
    <button
      class="stop-paper-btn"
      :class="{ armed: confirming }"
      :aria-label="confirming ? 'Confirm end paper' : 'End paper'"
      :title="confirming ? 'Click again to end and mark this paper' : 'End and mark this paper'"
      :disabled="props.disabled"
      @click="stopPaper"
    ><Square></Square></button>
    <!-- restart and mid-paper persistence have no implementation. Keeping
         them disabled is safer than suggesting an action succeeded. -->
    <button class="restart-paper-btn" aria-label="Restart paper is not available yet" title="Restart is not available yet" disabled><RotateCcw></RotateCcw></button>
    <button class="save-paper-btn" aria-label="Papers save when finished" title="Papers save when finished" disabled><Save></Save></button>
</div>
</template>
<style lang="scss" scoped>
.flex-wrapper {
    display:flex; 
    align-items: center;
    justify-content: space-evenly;
    button {
        width: 3.5vw;
        aspect-ratio: 1/1;
        background-color: transparent;
        border: none;
        cursor: pointer;

        &:disabled {
            cursor: not-allowed;
            opacity: 0.35;
        }
    }
    .stop-paper-btn {
        svg {
            stroke: $danger;
        }
        &.armed { outline: 2px solid $danger; }
    }
    .restart-paper-btn {
        svg {
            stroke: $warning;
        }
    }
    .save-paper-btn {
        svg {
            stroke: $success;
        }
    }
}
</style>
