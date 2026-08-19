<template>
    <div class="heatmap-container">
        heatmap
    </div>
    <div class="session-line-container">
        session-line-container
    </div>
    <div class="session-log">
        session-log
    </div>
    <div class="quickview-container quickview-container-1">
        microstat
    </div>
    <div class="quickview-container quickview-container-2">
        microstat
    </div>
    <div class="quickview-container quickview-container-3">
        microstat
    </div>
    <div class="quickview-container quickview-container-4">
        microstat
    </div>
</template>
<style lang="scss" scoped>
    .heatmap-container {
        grid-column: 7/21;
        grid-row: 9/21;
        background-color: $secondary-background;
        border-radius: 20px;
    }
    .session-line-container {
        grid-column: 3/19;
        grid-row: 1/9;
        background-color: $secondary-background;
        border-radius: 20px;
    }
    .session-log {
        grid-column: 1/7;
        grid-row: 9/21;
        background-color: $secondary-background;
        border-radius: 20px;
    }
    .quickview-container {
        background-color: $secondary-background;
        border-radius: 20px;
    }
    .quickview-container-1 {
        grid-column: 1/3;
        grid-row: 1/5;
    }
    .quickview-container-2 {
        grid-column: 1/3;
        grid-row: 5/9;
    }
    .quickview-container-3 {
        grid-column: 19/21;
        grid-row: 1/5;
    }
    .quickview-container-4 {
        grid-column: 19/21;
        grid-row: 5/9;
    }
</style>