<script setup lang="ts">
// use Vue's reactive-destructure default syntax. The removed `color` prop
// had no template use and no caller, and withDefaults disabled this transform.
const { text = 'hi' } = defineProps<{
  text?: string;
}>();
</script>

<template>
    <div class = "tag-container">
        <p>{{ text }}</p>
    </div>
</template>

<style lang="scss" scoped>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}
.tag-container {
  background-color: $tertiary-background;
  width: fit-content;
  border-radius: 4px;
  height: 100%;
  padding-left: 10px;
  padding-right: 10px;
  padding-top: 10px;
  padding-bottom: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: 'Lexend';
  color: $text;
}
</style>
