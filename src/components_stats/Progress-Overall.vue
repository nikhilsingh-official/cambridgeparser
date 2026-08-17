<template>
    <div class="multi-line-container">
        multiline
    </div>
    <div class="progress-line-container">
        line progression
    </div>
    <div class="donut-container">
        donut
    </div>
    <div class="quickview-container quickview-container-7">    
        microstat  
    </div>
    <div class="quickview-container quickview-container-6">
        microstat
    </div>
    <div class="quickview-container quickview-container-5">
        microstat
    </div>
    <div class="quickview-container quickview-container-4">
        microstat
    </div>
    <div class="quickview-container quickview-container-3">
        microstat
    </div>
    <div class="quickview-container quickview-container-1">
        microstat
    </div>
    <div class="quickview-container quickview-container-2">
        microstat
    </div>
</template>
<style lang="scss" scoped>
    .multi-line-container {
        grid-column: 1/15;
        grid-row: 1/13;
        background-color: $secondary-background;
        border-radius: 20px;
    }
    .progress-line-container {
        grid-column: 3/21;
        grid-row: 13/21;
        background-color: $secondary-background;
        border-radius: 20px;
    }
    .donut-container {
        grid-column: 15/19;
        grid-row: 1/9;
        background-color: $secondary-background;
        border-radius: 20px;
    }
    .quickview-container-7 {
        grid-column: 15/17;
        grid-row: 9/13;
    }
    .quickview-container-6 {
        grid-column: 17/19;
        grid-row: 9/13;
    }
    .quickview-container-5 {
        grid-column: 19/21;
        grid-row: 1/5;
    }
    .quickview-container-4 {
        grid-column: 19/21;
        grid-row: 5/9;
    }
    .quickview-container-3 {
        grid-column: 19/21;
        grid-row: 9/13;
    }
    .quickview-container-1 {
        grid-column: 1/3;
        grid-row: 17/21;
    }
    .quickview-container-2 {
        grid-column: 1/3;
        grid-row: 13/17;
    }
    .quickview-container {
        background-color: $secondary-background;
        border-radius: 20px;
    }
</style>