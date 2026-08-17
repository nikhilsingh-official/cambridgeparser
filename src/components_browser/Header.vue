<script setup lang="ts">
import '@vueform/multiselect/themes/default.css'
import { ref } from 'vue'
import BlurredBackground from "./BlurredBackground.vue";
import Multiselect from '@vueform/multiselect'

const options = ['Wade Cooper', 'Arlene Mccoy', 'Devon Webb', 'Tom Cook']
const selected = ref([])

const options1 = ['Apple', 'Banana', 'Cherry']
const selected1 = ref(null)

const options2 = ['Red', 'Green', 'Blue']
const selected2 = ref(null)

const options3 = ['Cat', 'Dog', 'Rabbit']
const selected3 = ref(null)

const options4 = ['Toyota', 'Honda', 'Ford']
const selected4 = ref(null)

const options5 = ['Spring', 'Summer', 'Autumn', 'Winter']
const selected5 = ref(null)
</script>
<template>
    <div class="header-container">
      <div class="blurred-container">
        <BlurredBackground></BlurredBackground>
      </div>
      <div class="half text-container">
        <h1 class="header-text">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-compass"><circle cx="12" cy="12" r="10"></circle><polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76"></polygon></svg>
          Paper Browser
        </h1>
        <p class="subheading-text">
          Search and explore past paper questions by year, tag, or subject.
        </p>
      </div>
      <div class="half filter-container">
        <Multiselect 
          v-model="selected" 
          :options="options" 
          :taggable="true"
          mode="tags"
          :searchable="true"
          placeholder="Filter Subjects" 
        /> 
        <div class="time-filter">
          <Multiselect 
            v-model="selected2" 
            :options="options2" 
            :taggable="true"
            mode="tags"
            :searchable="true"
            placeholder="Years..." 
          />
          <Multiselect 
            v-model="selected3" 
            :options="options3" 
            :taggable="true"
            mode="tags"
            :searchable="true"
            placeholder="Seasons..." 
          />
          <Multiselect 
            v-model="selected4" 
            :options="options4" 
            :taggable="true"
            mode="tags"
            :searchable="true"
            placeholder="Variants..." 
          />
        </div>
        <Multiselect 
          v-model="selected5" 
          :options="options5" 
          :taggable="true"
          mode="tags"
          :searchable="true"
          placeholder="Tags..." 
        />
      </div>
    </div>
</template>
<style lang="scss" scoped>
.header-container {
    position: relative;
    width: 100%;
    height: 100%;
    display: flex;
}
.half {
  @extend %filler;
  padding: 3rem;
  z-index: 3;
}
.text-container {
  display: flex;
  flex-direction: column;
  justify-content: center;
  color: $text;
  .header-text {
    font-family: 'Inter';
    font-size: 50px;
    display: flex;
    align-items: center;
    column-gap: 10px;
    svg {
      height: 50px;
      aspect-ratio: 1/1;
      color: $accent;
    }
  }
  .subheading-text {
    position: relative;
    font-family: 'Lexend';
  }
}
.filter-container {
    display: flex;
    align-items: center;
    justify-content: center;
    flex-direction: column;
    row-gap: 10px;
    .time-filter {
      display: flex;
      column-gap: 10px;
      width: 100%;
    }
}
.multiselect {
  font-family: 'Lexend';
  border: none;
  background: $secondary-background;
  outline: none;
  transition: background 1s ease;

  &:hover {
    background-color: $tertiary-background;
  }

  ::v-deep .multiselect-tag {
    background-color: $primary-color;
  }

  ::v-deep .multiselect-tags-search {
    background-color: transparent;
    color: $text;
  }

  ::v-deep .multiselect-dropdown {
    background-color: $tertiary-background;
    color: $text;
    border: none;

    .multiselect-option {
      background-color: $tertiary-background;
    }

    .multiselect-option.is-pointed {
      background-color: $secondary-background;
      color: white !important;
    }

    .multiselect-no-results {
      color: $text !important;
    }
  }
}

::v-deep .multiselect.is-active {
  border: none !important;
  box-shadow: none !important;
}

.blurred-container {
  position: absolute;
  top: 0;
  left: -12.5%;
  width: 125%;
  height: 100%;
  z-index: 0;
}
</style>