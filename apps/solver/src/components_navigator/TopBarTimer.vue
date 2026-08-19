<script setup lang="ts">
import { Timer } from 'lucide-vue-next';
</script>
<template>
    <div class="timer-wrapper"><Timer></Timer> 12:20</div>
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