<script setup lang="ts">
import { Copy, Flag, Star, Save } from 'lucide-vue-next';
</script>
<template>
<div class="flex-wrapper">
    <button class="copy-question-btn"><Copy></Copy></button>
    <button class="flag-question-btn"><Flag></Flag></button>
    <button class="star-question-btn"><Star></Star></button>
    <button class="save-question-btn"><Save></Save></button>
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
}
</style>