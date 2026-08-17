<script setup lang="ts">
import PedestalBlock from './Pedestal-Block.vue';
</script>
<template>

<div class="page-container">
    <PedestalBlock></PedestalBlock>
</div>

</template>
<style scoped>

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

.page-container {
    width: 100%;
    height: 100%;
    display:  flex;
    align-items: center;
    justify-content: center;
    background-image: radial-gradient(circle, #242424 12px, #121212);
    background-size: 20px 20px;
}

</style>