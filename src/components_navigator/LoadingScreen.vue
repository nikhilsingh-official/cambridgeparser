<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from "vue";
import lottie from "lottie-web";
import type { AnimationItem } from "lottie-web";
import animationData from "@/assets/soluer-loader.json";
import { ChevronLeft } from "lucide-vue-next";

// `schema` added so the paper code is the real one rather than the
// hardcoded '0625_w23_12' the template used to print.
defineProps<{
  state: boolean
  schema?: string
}>()

// this component previously swallowed the start of the exam entirely - it
// flipped a LOCAL `examVisible` flag and declared no emits, so MCQNav's
// startExam() was never called and no attempt was ever opened. It now tells the
// parent, which is what actually begins the attempt.
const emit = defineEmits<{ (e: 'start'): void; (e: 'back'): void }>();

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

  // PERFORMANCE. This animation was the single most expensive thing on the
  // loading screen. Measured on a real GPU (tests/perf/solver-cpu.mjs, HEADED=1):
  //
  //   svg renderer                20% of one core,  61 layouts/sec
  //   canvas renderer             16% of one core,   3 layouts/sec
  //   canvas + setSubframe(false) 10% of one core,   3 layouts/sec
  //
  // Two separate wins:
  //
  // 1. renderer "canvas" instead of "svg". lottie's SVG renderer animates by
  //    writing transform/path attributes onto SVG nodes, and every such write
  //    invalidates layout for the SVG subtree - hence 61 layouts a second, one
  //    per frame. Canvas draws into a bitmap and touches no DOM, so layout
  //    drops to nothing. This matters more than the CPU number suggests:
  //    layout runs on the main thread and blocks interaction, whereas
  //    rasterisation is largely handed to the GPU.
  //
  // 2. setSubframe(false). The animation is authored at 30fps but rAF fires at
  //    the display's 60Hz, and by default lottie interpolates at fractional
  //    frames - so it was rendering twice per authored frame for no visible
  //    benefit. Snapping to whole frames halves the work.
  //
  // dpr is pinned rather than left to devicePixelRatio: the canvas renderer
  // rasterises at a fixed size, and on a 3x phone screen an unpinned dpr would
  // quietly make this 9x the pixels. 2 is the point past which it stops being
  // visible on a 300px decorative spinner.
  animation = lottie.loadAnimation({
    container: lottieContainer.value,
    renderer: "canvas",
    loop: true,
    autoplay: true,
    animationData,
    rendererSettings: {
      dpr: Math.min(window.devicePixelRatio || 1, 2),
    },
  });
  animation.setSubframe(false);

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
  // tell MCQNav first so the attempt is opened and the event epoch is set
  // before the paper is revealed, then play the overlay out.
  emit('start');
  examVisible.value = true;
}

function startCountdown() {
  if (countdownInterval) return;

  countdownStarted.value = true;
  // the lottie is display:none from here on, but `display: none` does not
  // stop lottie - it keeps its rAF loop running and keeps computing frames
  // nobody can see. Pause it explicitly.
  animation?.pause();

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
<!-- was `display: none`, which snapped the paper into view. A Transition
     lets the overlay fade and lift away, revealing the paper underneath. -->
<Transition name="screen-fade">
<div v-if="!examVisible" class="loading-screen">
    <div class="back-btn" @click="emit('back')"><ChevronLeft class="icon" /> Back to Browser</div>
    <div class="centered-content">
      <div :style="{ display: !countdownStarted ? 'flex' : 'none' }" ref="lottieContainer" class="lottie"></div>
      <h3 :style="{ display: !countdownStarted ? 'flex' : 'none' }">{{ loading_messages[currentLoadingIndex] }}</h3>        
      <h5 :style="{ display: !countdownStarted ? 'flex' : 'none' }">Paper · {{ schema ?? '—' }}</h5>
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
</Transition>
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

/* the start screen lifting away to reveal the paper. Slightly longer on
   leave than enter so the reveal reads as deliberate rather than a cut. */
.screen-fade-leave-active {
  transition: opacity 0.55s ease, transform 0.55s ease;
}
.screen-fade-enter-active {
  transition: opacity 0.3s ease;
}
.screen-fade-leave-to {
  opacity: 0;
  transform: scale(1.04);
}
.screen-fade-enter-from {
  opacity: 0;
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