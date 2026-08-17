<script setup lang="ts">
import ProgressOverall from './Progress-Overall.vue';
import EngagementOverall from './Engagement-Overall.vue';
import FocusOverall from './Focus-Overall.vue';
import CardStrip from './CardStrip.vue';
import Multiselect from '@vueform/multiselect';
import Sidebar from '@/components/Sidebar.vue';
import { ref } from 'vue';

const options = ['Wade Cooper', 'Arlene Mccoy', 'Devon Webb', 'Tom Cook']
const selected = ref([])

const options1 = ['Apple', 'Banana', 'Cherry']
const selected1 = ref(null)

const options2 = ['Red', 'Green', 'Blue']
const selected2 = ref(null)
</script>
<template>
    <Sidebar></Sidebar>
    <div class="grid-container">
        <div class="top-card-strip-container">
            <CardStrip :bottom="false"></CardStrip>
        </div>
        <!--<div class="questions-list-container">
            <QuestionsList></QuestionsList>
        </div>-->
        <div class="header-container">
            <div class="text-container">
                <div class="header-box">
                    <svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-bar-chart-2"><line x1="18" y1="20" x2="18" y2="10"></line><line x1="12" y1="20" x2="12" y2="4"></line><line x1="6" y1="20" x2="6" y2="14"></line></svg>
                    <h1>Statistics</h1>
                </div>
                <p class="subtext">Lorem ipsum dolor sit amet consectetur adipisicing elit. Quisquam optio ab delectus, dolore voluptatem, error rem ipsa ullam sapiente possimus natus excepturi! Incidunt nostrum sit modi libero harum commodi saepe!</p>
                <div class="flex-container">
                    <Multiselect 
                      v-model="selected" 
                      :options="options" 
                      :searchable="true"
                      placeholder="Years..." 
                    />
                    <Multiselect 
                      v-model="selected1" 
                      :options="options1" 
                      :searchable="true"
                      placeholder="Seasons..." 
                    />
                    <Multiselect 
                      v-model="selected2" 
                      :options="options2" 
                      :searchable="true"
                      placeholder="Variants..." 
                    />
                </div>
            </div>
            <div class="pie-container">

            </div>
        </div>
        <div class="section-container progress-container">
            <div class="section-header">
                <h1 class="section-inner-header progress-header"><svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-trending-up-down-icon lucide-trending-up-down"><path d="M14.828 14.828 21 21"/><path d="M21 16v5h-5"/><path d="m21 3-9 9-4-4-6 6"/><path d="M21 8V3h-5"/></svg> progress</h1>
                <div class="expand-btn">
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-chevron-down-icon lucide-chevron-down"><path d="m6 9 6 6 6-6"/></svg>
                </div>
            </div>
            <div class="section-body">
                <ProgressOverall></ProgressOverall>
            </div>
        </div>
        <div class="section-container engagement-container">
            <div class="section-header">
                <h1 class="section-inner-header"><svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-activity-icon lucide-activity"><path d="M22 12h-2.48a2 2 0 0 0-1.93 1.46l-2.35 8.36a.25.25 0 0 1-.48 0L9.24 2.18a.25.25 0 0 0-.48 0l-2.35 8.36A2 2 0 0 1 4.49 12H2"/></svg> engagement</h1>
                <div class="expand-btn">
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-chevron-down-icon lucide-chevron-down"><path d="m6 9 6 6 6-6"/></svg>
                </div>
            </div>
            <div class="section-body">
                <EngagementOverall></EngagementOverall>
            </div>
        </div>
        <div class="section-container focus-container">
            <div class="section-header">
                <h1 class="section-inner-header"><svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-crosshair-icon lucide-crosshair"><circle cx="12" cy="12" r="10"/><line x1="22" x2="18" y1="12" y2="12"/><line x1="6" x2="2" y1="12" y2="12"/><line x1="12" x2="12" y1="6" y2="2"/><line x1="12" x2="12" y1="22" y2="18"/></svg> focuses</h1>
                <div class="expand-btn">
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-chevron-down-icon lucide-chevron-down"><path d="m6 9 6 6 6-6"/></svg>
                </div>
            </div>
            <div class="section-body">
                <FocusOverall></FocusOverall>
            </div>
        </div>
    </div>
</template>
<style lang="scss" scoped>
.flex-container {
  display: flex;
  padding: 10px;
  column-gap: 10px;

  .multiselect {
    background: $secondary-background;
    border-radius: 10px;
    padding: 6px 10px;
    font-size: 0.9rem;
    color: $text;
    border: none;
    outline: none;
    transition: background 1s ease;

    &:hover {
        background-color: $tertiary-background;
        ::v-deep .multiselect-search {
            background-color: $tertiary-background;
        }
    }

    ::v-deep .multiselect-search {
        transition: background 1s ease;
        background: $secondary-background;
        font-family: 'Lexend';
        color: $text;
    }
    ::v-deep .multiselect-placeholder {
        font-family: 'Lexend';
    }
    ::v-deep .multiselect-dropdown {
        background-color: $tertiary-background;
        border: none;
    }
    ::v-deep .multiselect-option {
        background-color: $tertiary-background;
        color: $text;
        font-family: 'Lexend';
    }
    ::v-deep .multiselect-option.is-pointed {
      background-color: $secondary-background;
      color: white !important;
    }

    ::v-deep .multiselect-no-results {
      font-family: 'Lexend';
      color: $text !important;
    }

    ::v-deep .multiselect-single-label {
        font-family: 'Lexend';
    }

    ::v-deep .multiselect-clear .multiselect-clear-icon {
        &:hover {
            background-color: white !important;
        }
    }
  }
}

.grid-container {
    width: 100%;
    height: 400%;
    padding-left: 5vw;
    display: grid;
    grid-template-columns: repeat(20, 1fr);
    grid-template-rows: repeat(40, 1fr);
    background-color: $background;
}
.top-card-strip-container {
    grid-column: 1/21;
    grid-row: 1/2;
}
.header-container {
    grid-column: 1/21;
    grid-row: 3/10;
    display: flex;
    .text-container {
        display: flex;
        flex-direction: column;
        justify-content: center;
        padding: 4rem;
        .header-box {
            font-size: 50px;
            font-family: 'Inter';
            display: flex;
            align-items: center;
            column-gap: 10px;
            color: $text;
            svg {
                color: $accent;
            }
        }
        .subtext {
            color: $text;
            font-family: 'Lexend';
            font-size: 15px;
        }
    }
    .pie-container {
        height: 100%;
        aspect-ratio: 1/1;
        background-color: $secondary-background;
        margin-right: 4rem;
        border-radius: 20px;
    }
}
.focus-container {
    grid-column: 1/21;
    grid-row: 31/41;
}
.engagement-container {
    grid-column: 1/21;
    grid-row: 21/31;
}
.progress-container {
    grid-column: 1/21;
    grid-row: 11/21;
}
.section-container {
    display: flex;
    flex-direction: column;
    margin: 0 4rem;
    .section-header {
        width: 100%;
        display: flex;
        align-items: center;
        color: $text;
        padding: 2.5rem 3rem;
        cursor: pointer;
        .section-inner-header {
            display: flex;
            align-items: center;
            column-gap: 20px;
            font-family: 'Inter';
            font-weight: 400;
            margin-right: auto;
            svg {
                color: $accent;
            }
        }
        .progress-header {
            svg {
                margin-top: 10px;
            }
        }
        .expand-btn {
            margin-left: auto;
            color: $accent;
        }
    }
    .section-body {
        width: 100%;
        height: 100%;
        display: grid;
        grid-template-columns: repeat(20, 1fr);
        grid-template-rows: repeat(20, 1fr);
        padding: 1rem;
        gap: 1rem;
    }
}
</style>