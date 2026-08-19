<script setup lang="ts">
import { defineProps, withDefaults } from 'vue'

const {text, color} = withDefaults(defineProps<{
  text?: string;
  color?: string;
}>(), {
  text: "hi",
  color: "blue"
});
</script>

<template>
    <div class = "tag-container">
        <p>{{ text }}</p>
    </div>
</template>

<style scoped>
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}
.tag-container {
    background-color: v-bind('color');
    width: fit-content;
    border-radius: 4px;
    height: 100%;
    padding-left: 10px;
    padding-right: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
}
</style>