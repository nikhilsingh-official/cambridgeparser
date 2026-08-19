<script setup lang="ts">
import CardGrid from './CardGrid.vue';
import {ref, type Ref, onMounted } from 'vue';

interface Card {
  color: string;
  subject: string;
  code: string;
  variant: string;
  condensed: string;
  icon: string;
}

const props = defineProps<{
  selectedSubjects: string[]
}>();

const totalCards: Card[] = [
  { color: '#2f855a', subject: 'Chemistry', code: '0620', variant: 'Paper 2: Extended MCQs', condensed: '0620/w24/21', icon: 'fa-solid fa-flask-vial' },
  { color: '#3182ce', subject: 'Physics', code: '0625', variant: 'Paper 2: Extended MCQs', condensed: '0625/s24/22', icon: 'fa-solid fa-atom' },
  { color: '#c53030', subject: 'Biology', code: '0610', variant: 'Paper 2: Extended MCQs', condensed: '0610/s24/21', icon: 'fa-solid fa-dna' },
  { color: '#b7791f', subject: 'Mathematics', code: '0580', variant: 'Paper 1: Core', condensed: '0580/w23/11', icon: 'fa-solid fa-square-root-variable' },
  { color: '#2c7a7b', subject: 'Economics', code: '0455', variant: 'Paper 2: Structured Questions', condensed: '0455/m23/22', icon: 'fa-solid fa-chart-line' },
  { color: '#4c51bf', subject: 'Computer Science', code: '0478', variant: 'Paper 1: Theory', condensed: '0478/w23/11', icon: 'fa-solid fa-desktop' },
  { color: '#c05621', subject: 'Business Studies', code: '0450', variant: 'Paper 2: Case Study', condensed: '0450/s23/21', icon: 'fa-solid fa-briefcase' },
  { color: '#2b6cb0', subject: 'History', code: '0470', variant: 'Paper 1: Structured Essay', condensed: '0470/w23/11', icon: 'fa-solid fa-landmark' },
  { color: '#b83280', subject: 'Geography', code: '0460', variant: 'Paper 2: Skills', condensed: '0460/s24/12', icon: 'fa-solid fa-globe' },
  { color: '#38a169', subject: 'English Language', code: '0500', variant: 'Paper 1: Reading', condensed: '0500/s24/11', icon: 'fa-solid fa-book-open' },
  { color: '#97266d', subject: 'Literature in English', code: '0475', variant: 'Paper 2: Drama', condensed: '0475/m24/21', icon: 'fa-solid fa-masks-theater' },
  { color: '#2c5282', subject: 'French', code: '0520', variant: 'Paper 2: Reading', condensed: '0520/w24/22', icon: 'fa-solid fa-language' },
  { color: '#276749', subject: 'Spanish', code: '0530', variant: 'Paper 1: Listening', condensed: '0530/m24/11', icon: 'fa-solid fa-headphones' },
  { color: '#b7791f', subject: 'Art & Design', code: '0400', variant: 'Paper 1: Observational Study', condensed: '0400/s24/11', icon: 'fa-solid fa-palette' },
  { color: '#6b46c1', subject: 'Music', code: '0410', variant: 'Paper 2: Listening', condensed: '0410/w23/21', icon: 'fa-solid fa-music' },
  { color: '#2f855a', subject: 'ICT', code: '0417', variant: 'Paper 1: Theory', condensed: '0417/s23/11', icon: 'fa-solid fa-keyboard' },
  { color: '#b7791f', subject: 'Environmental Management', code: '0680', variant: 'Paper 2: Case Studies', condensed: '0680/s23/21', icon: 'fa-solid fa-recycle' },
  { color: '#3182ce', subject: 'Global Perspectives', code: '0457', variant: 'Paper 1: Written Exam', condensed: '0457/w24/11', icon: 'fa-solid fa-earth-asia' },
  { color: '#c53030', subject: 'Sociology', code: '0495', variant: 'Paper 1: Structured Questions', condensed: '0495/w23/11', icon: 'fa-solid fa-people-group' },
  { color: '#2f855a', subject: 'Religious Studies', code: '0490', variant: 'Paper 2: World Religions', condensed: '0490/s23/22', icon: 'fa-solid fa-hands-praying' },
  { color: '#b7791f', subject: 'Design & Technology', code: '0445', variant: 'Paper 1: Product Design', condensed: '0445/w24/11', icon: 'fa-solid fa-drafting-compass' },
  { color: '#319795', subject: 'Drama', code: '0411', variant: 'Paper 1: Performance', condensed: '0411/s24/11', icon: 'fa-solid fa-theater-masks' },
  { color: '#c05621', subject: 'Accounting', code: '0452', variant: 'Paper 1: Theory', condensed: '0452/w23/11', icon: 'fa-solid fa-file-invoice-dollar' },
  { color: '#38a169', subject: 'Enterprise', code: '0454', variant: 'Paper 1: Case Study', condensed: '0454/s23/12', icon: 'fa-solid fa-building' },
  { color: '#dd6b20', subject: 'Travel & Tourism', code: '0471', variant: 'Paper 1: Core Content', condensed: '0471/m24/11', icon: 'fa-solid fa-plane-departure' },
  { color: '#a0aec0', subject: 'Food & Nutrition', code: '0648', variant: 'Paper 2: Practical', condensed: '0648/s23/21', icon: 'fa-solid fa-utensils' },
  { color: '#2b6cb0', subject: 'Marine Science', code: '0697', variant: 'Paper 1: Theory', condensed: '0697/w24/11', icon: 'fa-solid fa-water' },
  { color: '#d69e2e', subject: 'Psychology', code: '9990', variant: 'Paper 1: Core Studies', condensed: '9990/s23/11', icon: 'fa-solid fa-brain' },
  { color: '#319795', subject: 'Physical Education', code: '0413', variant: 'Paper 1: Theory', condensed: '0413/s23/11', icon: 'fa-solid fa-dumbbell' },
  { color: '#4a5568', subject: 'General Paper', code: '8001', variant: 'Paper 1: Essay', condensed: '8001/w23/11', icon: 'fa-solid fa-pen-nib' },
];

let cards: Ref<Card[]> = ref(totalCards);

console.log(cards.value)

const selectedSubj = ref('');
function handleSubjectChange() {
  if(selectedSubj.value == '') {
    cards.value = totalCards;
  } else {
    cards.value = totalCards.filter(card => card.subject == selectedSubj.value);
  }
}

const sortOrder = ref('desc');

function handleSortChange() {
  cards.value.sort((a, b) => {
    const codeA = parseInt(a.code);
    const codeB = parseInt(b.code);

    if (codeA !== codeB) {
      return sortOrder.value === 'asc' 
        ? codeA - codeB 
        : codeB - codeA;
    }

    const [_, sessionA_and_yearA, variantA] = a.condensed.split('/');
    const [__, sessionB_and_yearB, variantB] = b.condensed.split('/');

    let sessionA = sessionA_and_yearA[0]
    let yearA = sessionA_and_yearA.slice(1, 3);

    let sessionB = sessionB_and_yearB[0]
    let yearB = sessionB_and_yearB.slice(1, 3);

    const yearDiff = parseInt(yearA) - parseInt(yearB);
    if (yearDiff !== 0) {
      return sortOrder.value === 'asc' ? yearDiff : -yearDiff;
    }

    const seasonDiff = sessionA.localeCompare(sessionB);
    if (seasonDiff !== 0) {
      return sortOrder.value === 'asc' ? seasonDiff : -seasonDiff;
    }

    const variantDiff = parseInt(variantA) - parseInt(variantB);
    return sortOrder.value === 'asc' ? variantDiff : -variantDiff;
  });
}

onMounted(() => {
  const cursor_follower = document.querySelector(".glow-cursor") as HTMLElement;

  let mouseX = 0;
  let mouseY = 0;

  const updateCursorPosition = () => {
    const x = mouseX + window.scrollX;
    const y = mouseY + window.scrollY;

    cursor_follower.animate({
      left: `${x}px`,
      top: `${y}px`
    }, {duration: 3000, fill: 'forwards'})
  };

  document.addEventListener('mousemove', (event) => {
    mouseX = event.clientX;
    mouseY = event.clientY;
    updateCursorPosition();
  });

  document.addEventListener('scroll', updateCursorPosition);

  let delete_btns = document.querySelectorAll(".delete-btn");
  delete_btns.forEach(btn => {
    btn.addEventListener('click', () => {
      let select = document.querySelector(`.${(btn as HTMLElement).dataset.target}`)
      if(!select) return;
      (select as HTMLSelectElement).value = "";
      selectedSubj.value = '';
      handleSubjectChange()
    })
  })

});


</script>

<template>
  <div class = "blur-layer">
    <div class = "glow-cursor">

    </div>
  </div>
  <div class="main-container">
    <div class = "flex-select-btn">
      <select class="subject-selector" @change="handleSubjectChange" v-model="selectedSubj">
       <option value="" disabled default>Select a subject...</option>
       <option v-for="(item) in selectedSubjects" :key="item" :value="item">{{ item }}</option>
     </select>
     <button class = "delete-btn" data-target="subject-selector">
        <i class="fa-solid fa-trash"></i>
     </button>
    </div>
    <select class="subject-sort" v-model="sortOrder" @change="handleSortChange">
      <option value="desc">Latest</option>
      <option value="asc">Oldest</option>
    </select>
    <div class = "grid-wrapper">
      <CardGrid :array="cards"></CardGrid>
    </div>
  </div>
</template>

<style scoped>
.main-container {
  position: relative;
  width: 100%;
  height: 200%;
  z-index: 4;
  display: flex;
  align-items: center;
  flex-direction: column;
  overflow-x: hidden;
}
.grid-wrapper {
  width: 80%;
  height: 200%;
}
.glow-cursor {
  position: absolute;
  width: 250px;
  height: 250px;
  border-radius: 50%;
  background: linear-gradient(to right, #3182ce, #ddd);
  transform: translate(-50%, -50%);
}
.blur-layer {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 200%;
  filter: blur(100px);
  overflow-x: hidden;
}
.flex-select-btn {
  display: flex;
  column-gap: 10px;
} 
.delete-btn {
  color: red;
}
</style>
