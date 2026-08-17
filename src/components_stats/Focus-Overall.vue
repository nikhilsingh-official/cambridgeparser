<template>
    <div class="focus-pie-container">
      focus pie chart
    </div>
    <div class="quickview-container quickview-container-1">
      microstats
    </div>
    <div class="quickview-container quickview-container-1">
      microstats
    </div>
    <div class="quickview-container quickview-container-1">
      microstats
    </div>
    <div class="quickview-container quickview-container-1">
      microstats
    </div>
    <div class="quickview-container quickview-container-2">
      microstats
    </div>
    <div class="quickview-container quickview-container-3">
      microstats
    </div>
    <div class="quickview-container quickview-container-4">
      microstats
    </div>
    <div class="quickview-container quickview-container-5">
      microstats
    </div>
    <div class="quickview-container quickview-container-6">
      microstats
    </div>
</template>
<style lang="scss" scoped>
    .focus-pie-container {
      grid-column: 1/7;
      grid-row: 1/12;
      background-color: $secondary-background;
      border-radius: 20px;
    }
    .quickview-container {
        background-color: $secondary-background;
        border-radius: 20px;
    }
    .quickview-container-1 {
        grid-column: 1/3;
        grid-row: 12/16;
    }
    .quickview-container-2 {
        grid-column: 3/5;
        grid-row: 12/16;
    }
    .quickview-container-3 {
        grid-column: 5/7;
        grid-row: 12/16;
    }
    .quickview-container-4 {
        grid-column: 1/3;
        grid-row: 16/20;
    }
    .quickview-container-5 {
        grid-column: 3/5;
        grid-row: 16/20;
    }
    .quickview-container-6 {
        grid-column: 5/7;
        grid-row: 16/20;
    }
</style>