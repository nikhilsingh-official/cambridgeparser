<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from "vue";
import HighlightModeSlider from "./HighlightModeSlider.vue";
import ActiveQuestionButtons from "./ActiveQuestionButtons.vue";
import PaperControls from "./PaperControls.vue";
import { Wrench } from "lucide-vue-next";
import { getShowStates } from "./composable";

const container = ref<HTMLElement | null>(null);
const header = ref<HTMLElement | null>(null);

const { showTools } = getShowStates()

const isDragging = ref(false);
const pointerId = ref<number | null>(null);

const centerOffset = ref({ x: 0, y: 0 });

const PADDING = 24;
const MAGNET_DISTANCE = 16;
const CORNER_SNAP_DISTANCE = 32;

function onPointerDown(e: PointerEvent) {
  if (e.button !== 0 || !container.value) return;

  const rect = container.value.getBoundingClientRect();

  const centerX = rect.left + rect.width / 2;
  const centerY = rect.top + rect.height / 2;

  centerOffset.value = {
    x: e.clientX - centerX,
    y: e.clientY - centerY,
  };

  isDragging.value = true;
  pointerId.value = e.pointerId;

  container.value.setPointerCapture(e.pointerId);
  container.value.classList.add("is-dragging");

  window.addEventListener("pointermove", onPointerMove);
  window.addEventListener("pointerup", onPointerUp);
}

function onPointerMove(e: PointerEvent) {
  if (!isDragging.value || e.pointerId !== pointerId.value) return;
  if (!container.value) return;

  const rect = container.value.getBoundingClientRect();

  let centerX = e.clientX - centerOffset.value.x;
  let centerY = e.clientY - centerOffset.value.y;

  let left = centerX - rect.width / 2;
  let top = centerY - rect.height / 2;

  const minLeft = PADDING;
  const maxLeft = window.innerWidth - rect.width - PADDING;
  const minTop = PADDING;
  const maxTop = window.innerHeight - rect.height - PADDING;

  left = Math.min(Math.max(left, minLeft), maxLeft);
  top = Math.min(Math.max(top, minTop), maxTop);

  if (Math.abs(left - minLeft) < MAGNET_DISTANCE) left = minLeft;
  if (Math.abs(left - maxLeft) < MAGNET_DISTANCE) left = maxLeft;
  if (Math.abs(top - minTop) < MAGNET_DISTANCE) top = minTop;
  if (Math.abs(top - maxTop) < MAGNET_DISTANCE) top = maxTop;

  container.value.style.left = `${left}px`;
  container.value.style.top = `${top}px`;
}

function snapToCornerIfClose() {
  if (!container.value) return;

  const rect = container.value.getBoundingClientRect();

  const minLeft = PADDING;
  const maxLeft = window.innerWidth - rect.width - PADDING;
  const minTop = PADDING;
  const maxTop = window.innerHeight - rect.height - PADDING;

  const corners = [
    { left: minLeft, top: minTop },
    { left: maxLeft, top: minTop },
    { left: minLeft, top: maxTop },
    { left: maxLeft, top: maxTop },
  ];

  for (const corner of corners) {
    const dx = rect.left - corner.left;
    const dy = rect.top - corner.top;

    if (Math.hypot(dx, dy) < CORNER_SNAP_DISTANCE) {
      container.value.style.left = `${corner.left}px`;
      container.value.style.top = `${corner.top}px`;
      break;
    }
  }
}

function onPointerUp(e: PointerEvent) {
  if (e.pointerId !== pointerId.value || !container.value) return;

  container.value.releasePointerCapture(e.pointerId);

  snapToCornerIfClose();

  isDragging.value = false;
  pointerId.value = null;

  container.value.classList.remove("is-dragging");

  window.removeEventListener("pointermove", onPointerMove);
  window.removeEventListener("pointerup", onPointerUp);
}

onMounted(() => {
  if (!container.value || !header.value) return;

  const rect = container.value.getBoundingClientRect();
  container.value.style.left = `${PADDING}px`;
  container.value.style.top = `${window.innerHeight / 2 - rect.height / 2}px`;

  header.value.addEventListener("pointerdown", onPointerDown);
});

onBeforeUnmount(() => {
  header.value?.removeEventListener("pointerdown", onPointerDown);
  window.removeEventListener("pointermove", onPointerMove);
  window.removeEventListener("pointerup", onPointerUp);
});
</script>

<template>
  <div
    ref="container"
    class="tools-container"
    :aria-grabbed="isDragging ? 'true' : 'false'"
    role="button"
    tabindex="0"
    v-show="showTools"
  >
    <div class="header-wrapper" ref="header">
      <Wrench></Wrench>
      <h1>Tools</h1>
    </div>
    <div class="slider-wrapper">
      <h2>Interaction Mode</h2>
      <HighlightModeSlider></HighlightModeSlider>
    </div>
    <div class="buttons-wrapper">
      <h2>Question Actions</h2>
      <ActiveQuestionButtons></ActiveQuestionButtons>
    </div>
    <div class="paper-wrapper">
      <h2>Paper Controls</h2>
      <PaperControls></PaperControls>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.tools-container.is-dragging .header-wrapper {
  cursor: grabbing;
}
.header-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 7.5px;
  cursor: grab;
  user-select: none;
  touch-action: none;
  h1 {
    font-size: 22px;
    font-family: 'Inter';
    color: white;
  }
  svg {
    stroke: $accent;
  }
}

.slider-wrapper {
  h2 {
    font-size: 17px;
    font-family: 'Inter';
    color: white;
  }
}

.buttons-wrapper {
  h2 {
    font-size: 17px;
    font-family: 'Inter';
    color: white;
  }
}

.paper-wrapper {
  h2 {
    font-size: 17px;
    font-family: 'Inter';
    color: white;
  }
}

.tools-container {
  position: absolute;
  width: 300px;
  aspect-ratio: 1/1;
  top: 0;
  left: 0;
  transform: none;
  background-color: rgba(
    red($tertiary-background),
    green($tertiary-background),
    blue($tertiary-background),
    0.75
  );
  backdrop-filter: blur(3.75px);
  border-radius: 16px;
  z-index: 999;
  box-shadow:
    0 12px 36px rgba(
      red($secondary-background),
      green($secondary-background),
      blue($secondary-background),
      0.65
    ),
    0 0 40px rgba(
      red($secondary-background),
      green($secondary-background),
      blue($secondary-background),
      0.10
    );
  user-select: none;
  transition: box-shadow 160ms ease, transform 64ms linear;
  will-change: transform, box-shadow;
  display: grid;
  grid-template-areas:
    "header"
    "interaction"
    "actions"
    "paper";
  grid-template-rows:
    auto
    auto
    auto
    auto;
  gap: 12px;
  padding: 12px;
  color: inherit;
}

.tools-container.is-dragging {
  cursor: grabbing;
  box-shadow:
    0 28px 64px rgba(8, 12, 20, 0.7),
    0 0 88px rgba(80, 160, 255, 0.18);
  transition: none;
  transform: translate(var(--drag-x, 0px), var(--drag-y, 0px));
}

.tools-container::before {
  content: "";
  position: absolute;
  inset: 0;
  border-radius: inherit;
  pointer-events: none;
  filter: blur(32px);
  opacity: 0.85;
  background: radial-gradient(48% 48% at 20% 10%, rgba(red($accent), green($accent), blue($accent), 0.40), transparent 28%),
              radial-gradient(40% 40% at 80% 90%, rgba(red($accent), green($accent), blue($accent), 0.30), transparent 30%);
  z-index: -1;
  transform: translateZ(0);
}

@keyframes glow-pulse {
  0% { transform: scale(1); opacity: 0.70; }
  50% { transform: scale(1.03); opacity: 0.95; }
  100% { transform: scale(1); opacity: 0.70; }
}

.tools-container::before {
  animation: glow-pulse 3.5s ease-in-out infinite;
}

.tools-container:focus {
  outline: 2px solid rgba(red($accent), green($accent), blue($accent), 0.80);
}

@media (max-width: 420px) {
  .tools-container {
    width: 200px;
  }
}
</style>
