<script setup lang="ts">


</script>
<template>
<div class="rankings-container">
    <div class="pedestal bronze-ped">
    <div class="trophy bronze-trophy">
        <p class="hovering-text">Biology</p>
        <i class="fa-solid fa-trophy"></i>
        <p class="trophy-percent">85%</p>
      </div>
    </div>

    <div class="pedestal gold-ped">
      <div class="trophy gold-trophy">
        <p class="hovering-text">Chemistry</p>
        <i class="fa-solid fa-trophy"></i>
        <p class="trophy-percent">95%</p>
      </div>
    </div>

    <div class="pedestal silver-ped">
      <div class="trophy silver-trophy">
        <p class="hovering-text">Physics</p>
        <i class="fa-solid fa-trophy"></i>
        <p class="trophy-percent">90%</p>
      </div>
    </div>
  </div>
</template>  
<style scoped>

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

.trophy {
    position: absolute;
    left: 10%;
    width: 80%;
    aspect-ratio: 1/1;
    display: flex;
    justify-content: center;
    align-items: flex-end;
}

.trophy i {
    font-size: 200px;
}

.hovering-text {
    position: absolute;
    top: 20%;
    font-size: 20px;
    font-family: 'Poppins';
}

.trophy-percent {
    position: absolute;
    top: 57.5%;
    left: 50%;
    transform: translate(-50%, -50%);
    color: white;
    font-size: 35px;
    font-weight: 900;
}

.gold-trophy {
    color: gold;
    top: -25.175%;
}

.silver-trophy {
    color: silver;
    top: -24.75%;
}

.bronze-trophy {
    color: #CD7F32;
    top: -23.5%;
}

.gold-ped {
    position: absolute;
    top: 52%;
    width: 20%;
    aspect-ratio: 319/997;
    left: 42%;
    background-image: url(/public/model.png);
    background-repeat: no-repeat;
    background-position: center 0;
}

.rankings-container {
  width: 100%;
  height: 100%;
  position: relative;
  overflow: hidden;
}

.rankings-grid {
  width: 100%;
  height: 100%;
  position: relative;
}

</style>