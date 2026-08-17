<script lang="ts">

</script>
<template>
<div class="page-container">
    <div class="subject-header">
        <div class="icon-background">
            <i class="fa-solid fa-flask"></i>
        </div>
        <div class="subject-header-icon">
            <i class="fa-solid fa-flask-vial"></i>
            <h2>Chemistry</h2>
            <p>0620</p>
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

.page-container {
    width: 100%;
    height: 100%;
}

.subject-header {
    position: relative;
    background-color: #8cd908;
    width: 100%;
    height: 80%;
    overflow: hidden;
}

.subject-header-icon {
    position: absolute;
    top: 20%;
    left: 50%;
    transform: translateX(-50%);
    width: 15%;
    aspect-ratio: 1/1;
    border-radius: 50%;
    background-color: #242424;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-direction: column;
}

.subject-header-icon i {
    font-size: 40px;
}

.icon-background {
    position: absolute;
    top: 0;
    height: 100%;
    width: 80%;
    left: 50%;
    background-size: cover;
    background-repeat: no-repeat;
    background-position: center center;
    display: flex;
    align-items: center;
    justify-content: flex-end;
}

.icon-background i {
    font-size: 35vw;
    transform: translateX(-50%);
    opacity: 0.6;
}
</style>