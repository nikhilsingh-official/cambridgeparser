<script setup lang="ts">
import { Square, RotateCcw, Save } from 'lucide-vue-next';
</script>
<template>
<div class="flex-wrapper">
    <button class="stop-paper-btn"><Square></Square></button>
    <button class="restart-paper-btn"><RotateCcw></RotateCcw></button>
    <button class="save-paper-btn"><Save></Save></button>
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
    }
    .stop-paper-btn {
        svg {
            stroke: $danger;
        }
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