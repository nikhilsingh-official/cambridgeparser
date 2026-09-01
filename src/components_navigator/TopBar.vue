<script setup lang="ts">
import TopBarTimer from './TopBarTimer.vue';
import ZenMode from './ZenMode.vue';

// MCQNav owns the exam lifecycle; the timer only renders that state.
defineProps<{ running: boolean }>();
// MCQNav owns Zen Mode so it can change the surrounding solver layout.
const zenMode = defineModel<boolean>('zenMode', { default: false });

</script>
<template>
    <div class="top-bar-wrapper">
        <div class="zen-mode-wrapper">
            <ZenMode v-model="zenMode"></ZenMode>
        </div>
        <div class="timer-wrapper">
            <TopBarTimer :running="running"></TopBarTimer>
        </div>
        <div class="end-btn-wrapper">
        </div>
    </div>
</template>
<style lang="scss" scoped>
.top-bar-wrapper {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 100%;
    height: 100%;
    padding: 0 1vw;
}
.zen-mode-wrapper, .timer-wrapper, .end-btn-wrapper {
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    gap: 10px;
}
.zen-mode-wrapper {
    justify-content: flex-start;
}
.timer-wrapper {
    justify-content: center;
}
.end-btn-wrapper {
    justify-content: flex-end;
}
</style>
