<script setup>
import { onMounted } from 'vue';

onMounted(() => {
    const track = document.querySelector(".carousel-track");
    const items = document.querySelectorAll(".carousel-item");
    const indicators = document.querySelectorAll(".carousel-item-indicator");
    const topLabel = document.querySelector(".top-label");
    
    const itemCount = items.length - 2;
    const itemWidth = items[0].clientWidth;
    let index = 1;
    let slideDuration = 10000;
    let isTransitioning = false;
    
    const indexMappings = [`<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-compass"><circle cx="12" cy="12" r="10"></circle><polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76"></polygon></svg> &middot; <p class="top-label-text"> paper browser </p>`, `                            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-bar-chart-2"><line x1="18" y1="20" x2="18" y2="10"></line><line x1="12" y1="20" x2="12" y2="4"></line><line x1="6" y1="20" x2="6" y2="14"></line></svg> &middot; <p class="top-label-text"> stats </p>`];
    
    indicators.forEach(line => {
      const fill = document.createElement("div");
      fill.className = "progress-fill";
      line.appendChild(fill);
    });
    
    track.style.transform = `translateX(-${index * itemWidth}px)`;
    
    function goToSlide(newIndex) {
      if (isTransitioning) return;
      isTransitioning = true;
    
      if(newIndex == itemCount + 1) {
        topLabel.innerHTML = indexMappings[0];
      } else {
        topLabel.innerHTML = indexMappings[newIndex - 1];
      }
  
      index = newIndex;
      track.style.transition = "transform 0.6s ease-in-out";
      track.style.transform = `translateX(-${index * itemWidth}px)`;
  
      updateIndicators();
    }
    
    track.addEventListener("transitionend", () => {
      if (index === 0) {
        index = itemCount;
        track.style.transition = "none";
        track.style.transform = `translateX(-${index * itemWidth}px)`;
      } else if (index === itemCount + 1) {
        index = 1;
        track.style.transition = "none";
        track.style.transform = `translateX(-${index * itemWidth}px)`;
      }
  
      isTransitioning = false;
    });
    
    function updateIndicators() {
      const current = (index - 1 + itemCount) % itemCount;
    
      indicators.forEach((line, i) => {
        const fill = line.querySelector(".progress-fill");
        fill.style.transition = "none";
        fill.style.left = "-100%";
      });
  
      setTimeout(() => {
        indicators.forEach((line, i) => {
          const fill = line.querySelector(".progress-fill");
          fill.style.transition = i === current ? `left ${slideDuration}ms linear` : "none";
          fill.style.left = i <= current ? "0%" : "-100%";
        });
      }, 50);
    }
    
    function startAutoSlide() {
      setInterval(() => {
        goToSlide(index + 1);
      }, slideDuration);
    }
    
    updateIndicators();
    startAutoSlide();
})

</script>
<template>
    <div class="cta">
        <div class = "hero-carousel">
            <div class="top-label">
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-compass"><circle cx="12" cy="12" r="10"></circle><polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76"></polygon></svg>
                &middot;
                <p class="top-label-text">
                    paper browser
                </p>
            </div>
            <div class="carousel-item-indicator-container">
                <div class="carousel-item-indicator"></div>
                <div class="carousel-item-indicator"></div>
            </div>
            <div class="carousel-track">
                <div class="carousel-item">
                    <div class="cta-text-container">
                        <h1>Track Your Progress</h1>
                        <p>View your strengths, spot weaknesses, and watch your improvement over time.</p>
                        <button class="cta-redirect">Open Stats Dashboard 
                            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" 
                                 viewBox="0 0 24 24" fill="none" stroke="currentColor" 
                                 stroke-width="2" stroke-linecap="round" stroke-linejoin="round" 
                                 class="feather feather-chevron-right">
                                <polyline points="9 18 15 12 9 6"></polyline>
                            </svg>
                        </button>
                    </div>
                    <img src="@/assets/images/stats.png" class="cta-img" data-type="stats">
                </div>
                <div class="carousel-item">
                    <div class="cta-text-container">
                        <h1>Ready to Test Yourself?</h1>
                        <p>Dive into our full archive of past paper questions.</p>
                        <button class="cta-redirect">Open Paper Browser <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-chevron-right"><polyline points="9 18 15 12 9 6"></polyline></svg></button>
                    </div>
                    <img src="@/assets/images/paper.png" class="cta-img" data-type="paper">
                </div>
                <div class="carousel-item">
                    <div class="cta-text-container">
                        <h1>Track Your Progress</h1>
                        <p>View your strengths, spot weaknesses, and watch your improvement over time.</p>
                        <button class="cta-redirect">Open Stats Dashboard 
                            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" 
                                 viewBox="0 0 24 24" fill="none" stroke="currentColor" 
                                 stroke-width="2" stroke-linecap="round" stroke-linejoin="round" 
                                 class="feather feather-chevron-right">
                                <polyline points="9 18 15 12 9 6"></polyline>
                            </svg>
                        </button>
                    </div>
                    <img src="@/assets/images/stats.png" class="cta-img" data-type="stats">
                </div>
                <div class="carousel-item">
                    <div class="cta-text-container">
                        <h1>Ready to Test Yourself?</h1>
                        <p>Dive into our full archive of past paper questions.</p>
                        <button class="cta-redirect">Open Paper Browser <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-chevron-right"><polyline points="9 18 15 12 9 6"></polyline></svg></button>
                    </div>
                    <img src="@/assets/images/paper.png" class="cta-img" data-type="paper">
                </div>
            </div>
        </div>
    </div>
</template>
<style lang="scss">
.cta {
  position: relative;
  grid-row: 3 / 12;
  grid-column: 4 / 18;
  background-color: $primary-color;
  border-radius: 10px;
  overflow: hidden;
}

.top-label {
  position: absolute;
  z-index: 3;
  top: 5%;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  justify-content: center;
  column-gap: 5px;
  opacity: 0.6;

  .top-label-text {
    font-family: "Kode Mono";
    font-weight: 100;
  }
}

.carousel-item-indicator-container {
  position: absolute;
  z-index: 3;
  top: 85%;
  left: 50%;
  transform: translateX(-50%);
  width: 15%;
  aspect-ratio: 6 / 1;
  background-color: rgba(0, 0, 0, 0.15);
  border-radius: 5px;
  display: flex;
  justify-content: space-evenly;
  align-items: center;
  column-gap: 20px;
  padding: 0 20px;
}

.carousel-item-indicator {
  position: relative;
  width: 100%;
  height: 1px;
  background-color: transparent;
  overflow: hidden;

  .progress-fill {
    position: absolute;
    top: 0;
    left: -100%;
    width: 100%;
    height: 100%;
    background-color: white;
    transition: left 4s linear;
  }
}

.cta-img {
  height: 150%;
  aspect-ratio: 1 / 1;
  position: absolute;
  right: -10%;

  &[data-type="paper"] {
    top: 0;
    transform: rotate(-45deg);
  }

  &[data-type="stats"] {
    top: -5%;
    transform: rotate(-10deg);
  }
}

.cta-text-container {
  font-family: 'Inter';
  display: flex;
  flex-direction: column;
  row-gap: 3px;
}

.cta-redirect {
  display: flex;
  align-items: center;
  width: fit-content;
  justify-content: center;
  margin-top: 15px;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background-color: $secondary-color;
  border: 1px solid $secondary-color-lightened;
  border-radius: 10px;
  cursor: pointer;

  svg {
    vertical-align: middle;
  }
}

.hero-carousel {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
}

.carousel-track {
  position: relative;
  width: 400%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.carousel-item {
  position: relative;
  width: 100%;
  height: 100%;
  padding: 3rem;
  display: flex;
  overflow: hidden;
  align-items: center;

  &:nth-child(2) {
    background-image: 
      linear-gradient(to right, $primary-color-lightened 1px, transparent 1px),
      linear-gradient(to bottom, $primary-color-lightened 1px, transparent 1px);
    background-size: 30px 30px;
    background-repeat: repeat;
  }

  &:nth-child(3) {
    background-color: $primary-color-darkened;
    background-image: radial-gradient(circle, $primary-color 1.5px, transparent 1.5px);
    background-size: 30px 30px;
    background-repeat: repeat;
  }
}
</style>