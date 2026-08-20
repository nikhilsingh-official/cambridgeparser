<template>
    <div class="quick-preview-container">
        <div class="quick-preview">
            <div class="grid-square streak-square">
                <h4 class="grid-square-header"><svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-flame-icon lucide-flame"><path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z"/></svg> streak</h4>
                <div class="grid-square-text">
                    <p class="main-text">10 days</p>
                    <p class="sub-text">longest: 21 days</p>
                </div>
            </div>
            <div class="grid-square paper-square">
                <h4 class="grid-square-header"><svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-notepad-text-icon lucide-notepad-text"><path d="M8 2v4"/><path d="M12 2v4"/><path d="M16 2v4"/><rect width="16" height="18" x="4" y="4" rx="2"/><path d="M8 10h6"/><path d="M8 14h8"/><path d="M8 18h5"/></svg> papers</h4>
                <div class="grid-square-text">
                    <p class="main-text">352</p>
                    <p class="sub-text">number of papers</p>
                </div>
            </div>
            <div class="grid-square time-square">
                <h4 class="grid-square-header"><svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-clock"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg> time</h4>
                <div class="grid-square-text">
                    <p class="main-text">12h 17m</p>
                    <p class="sub-text">total time solving</p>
                </div>
            </div>
            <div class="grid-square accuracy-square">
                <h4 class="grid-square-header"><svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-target"><circle cx="12" cy="12" r="10"></circle><circle cx="12" cy="12" r="6"></circle><circle cx="12" cy="12" r="2"></circle></svg> accuracy</h4>
                <div class="grid-square-text">
                    <p class="main-text">157/170</p>
                    <p class="sub-text">correct over total</p>
                </div>
            </div>
        </div>
    </div>
</template>
<style lang="scss" scoped>
.quick-preview-container {
  grid-row: 13 / 20;
  grid-column: 13 / 18;
  display: flex;
  align-items: center;
  justify-content: center;
}

.quick-preview {
  height: 100%;
  border-radius: 10px;
  aspect-ratio: 1 / 1;
  display: grid;
  grid-template-columns: 1fr 1fr;
  grid-template-rows: 1fr 1fr;
  gap: 10px;
  padding: 10px;
}

.grid-square {
  background-color: $secondary-background;
  border-radius: 10px;
  display: flex;
  flex-direction: column;
  align-items: center;
  cursor: pointer;
  padding: 1rem;
  svg {
    transition: color 1s ease, fill 1s ease;
  }
  .grid-square-header {
    display: flex;
    align-items: center;
    justify-content: center;
    column-gap: 7.5px;
    font-family: 'Inter';
    font-size: 20px;
    margin-bottom: auto;
    padding: 0.5rem;
  }
  .grid-square-text {
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-direction: column;
    font-family: 'Lexend';
    font-weight: 300;
    .main-text {
      margin-top: auto;
    }
    .sub-text {
      color: lightgrey;
      font-size: 12px;
      margin-top: auto;
    }
  }
}

@mixin hover-effect-grid-square($color, $fill) {
  &:hover {
    svg {
      color: $color;
      fill: $fill;
    }
  }
}

.streak-square {
  @include hover-effect-grid-square(red, orange)
}

.paper-square, .time-square, .accuracy-square {
  @include hover-effect-grid-square($primary-color, $accent)
}
</style>