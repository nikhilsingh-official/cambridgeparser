<script setup lang="ts">
import { Timer } from 'lucide-vue-next';
// the previous timer was the literal string "12:20". This clock is driven
// by the exam lifecycle and freezes at completion for a truthful review view.
import { computed, onBeforeUnmount, ref, watch } from 'vue';

const props = defineProps<{ running: boolean }>();
const elapsedSeconds = ref(0);
let intervalId: number | null = null;
let startedAt = 0;

function updateElapsed() {
    if (!startedAt) return;
    elapsedSeconds.value = Math.max(
        0,
        Math.floor((performance.now() - startedAt) / 1000),
    );
}

function stopTimer() {
    if (intervalId !== null) window.clearInterval(intervalId);
    intervalId = null;
}

watch(
    () => props.running,
    (running) => {
        if (!running) {
            updateElapsed();
            stopTimer();
            return;
        }

        startedAt = performance.now() - elapsedSeconds.value * 1000;
        updateElapsed();
        stopTimer();
        intervalId = window.setInterval(updateElapsed, 250);
    },
    { immediate: true },
);

onBeforeUnmount(stopTimer);

const displayTime = computed(() => {
    const minutes = Math.floor(elapsedSeconds.value / 60);
    const seconds = elapsedSeconds.value % 60;
    return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
});
</script>
<template>
    <div class="timer-wrapper" aria-label="Elapsed exam time" aria-live="off">
        <Timer></Timer> {{ displayTime }}
    </div>
</template>
<style lang="scss" scoped>
.timer-wrapper {
    font-family: 'Kode Mono';
    font-weight: 550;
    color: $text;
    display: flex;
    align-items: center;
    justify-content: center;
    column-gap: 5px;
    svg {
        margin-top: -5px;
    }
}
</style>