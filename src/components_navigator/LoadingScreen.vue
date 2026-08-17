<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from "vue";
import lottie from "lottie-web";
import type { AnimationItem } from "lottie-web";
import animationData from "@/assets/soluer-loader.json";
import { ChevronLeft } from "lucide-vue-next";

defineProps<{
  state: boolean
}>()

const examVisible = ref(false);
const lottieContainer = ref<HTMLElement | null>(null);
let animation: AnimationItem | null;

const loading_messages = [
  "Preparing the PDF...",
  "Extracting highlights...",
  "Analyzing sections...",
  "Loading timers...",
  "Generating smart navigation...",
  "Scanning for annotations...",
  "Organizing question references...",
  "Finalizing workspace..."
];

const tips = [
  "Click on a question to start its timer!",
  "Press 'E' to switch to elimination mode!",
  "Check question statuses in the sidebar!",
  "Enhance focus using zen mode!"
];

const currentLoadingIndex = ref(0);
const currentTipIndex = ref(0);

let loadingInterval: number | undefined;
let tipInterval: number | undefined;

onMounted(() => {
  if (!lottieContainer.value) return;

  animation = lottie.loadAnimation({
    container: lottieContainer.value,
    renderer: "svg",
    loop: true,
    autoplay: true,
    animationData,
  });

  loadingInterval = window.setInterval(() => {
    currentLoadingIndex.value =
      (currentLoadingIndex.value + 1) % loading_messages.length;
  }, 1500);

  tipInterval = window.setInterval(() => {
    currentTipIndex.value = (currentTipIndex.value + 1) % tips.length;
  }, 3000);
});

const countdownStarted = ref(false);
const countdown = ref(3);
let countdownInterval: number | null = null;

function endLoadingScreen() {
  clearInterval(countdownInterval!);
  examVisible.value = true;
}

function startCountdown() {
  if (countdownInterval) return;

  countdownStarted.value = true;

  countdownInterval = window.setInterval(() => {
    countdown.value--;
    if(countdown.value == 0) {
      endLoadingScreen();
    }
  }, 1000);
}

onBeforeUnmount(() => {
  animation?.destroy();
  if (countdownInterval) clearInterval(countdownInterval)
  if (loadingInterval) clearInterval(loadingInterval);
  if (tipInterval) clearInterval(tipInterval);
});
</script>
<template>
<div :style="{ display: examVisible ? 'none' : 'flex' }" class="loading-screen">
    <div class="back-btn"><ChevronLeft class="icon" /> Back to Browser</div>
    <div class="centered-content">
      <div :style="{ display: !countdownStarted ? 'flex' : 'none' }" ref="lottieContainer" class="lottie"></div>
      <h3 :style="{ display: !countdownStarted ? 'flex' : 'none' }">{{ loading_messages[currentLoadingIndex] }}</h3>        
      <h5 :style="{ display: !countdownStarted ? 'flex' : 'none' }">Paper · 0625_w23_12</h5>
      <div class="button-container">
        <button :style="{ display: state && !countdownStarted ? 'flex' : 'none' }" @click="startCountdown">Start Exam</button>
      </div>
      <p :style="{ display: countdownStarted ? 'flex' : 'none' }">{{ countdown }}</p>
    </div>

    <Transition name="tip-fade" mode="out-in">
      <div :key="currentTipIndex" class="tip-wrapper">
          <h4 class="tip">Tip: {{ tips[currentTipIndex] }}</h4>
      </div>
    </Transition>
</div>
</template>
<style lang="scss" scoped>
.loading-screen {
    background-color: $secondary-background;
    background-image: 
        linear-gradient(to right, $background 1px, transparent 1px),
        linear-gradient(to bottom, $background 1px, transparent 1px);  background-size: 30px 30px;
    width: 100%;
    height: 100%;
    position: absolute;
    left: 0;
    top: 0;
    z-index: 999;
    color: $text;
    h4 {
        font-family: 'Inter';
    }

    .centered-content {
        position: absolute;
        top: 45%;
        left: 50%;
        transform: translate(-50%, -50%);
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        h1 {
            font-family: 'Inter';
        }
        h3 {
            font-family: 'Lexend';
        }
        h5 {
            font-family: 'Kode Mono';
            opacity: 0.5;
        }
        p {
          font-family: 'Lexend';
          font-size: 40px;
        }
        .button-container {
          width: 100%;
          padding: 1vw;
          display: flex;
          align-items: center;
          justify-content: center;
          button {
            cursor: pointer;
            font-family: 'Lexend';
            display: flex;
            align-items: center;
            justify-content: center;
            column-gap: 5px;
            border: $secondary-color 2px solid;
            padding: 0.67vw;
            border-radius: 50px;
            font-size: 13px;
            transition: background 1s ease, box-shadow 0.5s ease;
            color: $text;
            background-color: transparent;
            &:hover {
                background-color: $secondary-color;
                box-shadow: 0px 0px 5px 1px $accent;
            }
          }
        }
        .lottie {
            width: 300px;
            aspect-ratio: 1;
        }
    }

    .tip-wrapper {
        position: absolute;
        bottom: 10%;
        left: 50%;
        transform: translateX(-50%);
        .tip {
            opacity: 0.75;
        }
    }
}
.back-btn {
    position: absolute;
    top: 20px;
    left: 20px;
    cursor: pointer;
    font-family: 'Lexend';
    display: flex;
    align-items: center;
    justify-content: center;
    column-gap: 5px;
    border: $secondary-color 2px solid;
    padding: 0.67vw;
    border-radius: 50px;
    font-size: 13px;
    transition: background 1s ease, box-shadow 0.5s ease;
    color: $text;
    &:hover {
        background-color: $secondary-color;
        box-shadow: 0px 0px 5px 1px $accent;
    }
}

.back-btn .icon {
  width: 20px;
  height: 20px;
  stroke-width: 2.4;
}

.tip-fade-enter-active,
.tip-fade-leave-active {
  transition: opacity 0.5s ease;
}

.tip-fade-enter-from,
.tip-fade-leave-to {
  opacity: 0;
}

.tip-fade-enter-to,
.tip-fade-leave-from {
  opacity: 0.75;
}
</style>