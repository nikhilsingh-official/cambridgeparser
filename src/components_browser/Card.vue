<script setup lang="ts">
import { computed, defineProps, type CSSProperties } from 'vue'
import Tag from './Tag.vue'
import { codeToBg } from '../constants/codeMaps';

// `color` was used in the template (<Tag :color="color">) but never
// declared as a prop, so it resolved to nothing at runtime and Tag always fell
// back to its default. Declared here and destructured so it actually arrives.
const { subject, code, icon, color } = defineProps<{
  subject: string;
  code: string;
  variant: string;
  condensed: string;
  icon: string;
  color?: string;
}>();

const scienceSubjects = ["0620", "0625", "0610", "0654", "0653", "0680", "0697"];

const bgPositionStyle = computed<CSSProperties>(() => ({
  left: scienceSubjects.includes(code) ? '50%' : '0%',
  position: 'absolute',
  top: '0%'
}));
</script>
<template>
    <div class = "card-container">
        <img class = "bg-pattern" :src="codeToBg[code]" :style="bgPositionStyle"/>
        <div class = "bg-icon" v-html="icon"></div>
        <div class = "expand-sliver-up"></div>
        <div class = "expand-sliver-down"></div>
        <div class = "sliver-color"></div>
        <div class = "card-content">
            <div class = "card-header">
                <div class = "icon-container">
                    <span class="icon" v-html="icon"></span>
                </div>
                <div class = "pending-indicator-container">
                    <i class="fa-regular fa-clock pending-icon pulse"></i>
                </div>       
                <div class = "done-indicator-container">
                    <i class="fa-solid fa-square-check done-indicator"></i>     
                    <i class="fa-regular fa-square-check done-indicator done-indicator-filling"></i>  
                </div>
            </div>
            <div class = "card-body">
                <div class = "body-left">
                    <p class = "paper-type">{{ variant }}</p>
                    <h2 class = "subject-header">{{subject}}</h2>
                    <h4 class = "code-text">{{code}}</h4>
                </div>
                <div class = "time-indicator-container">
                    <p class = "last-attempted-date"><i class="fa-solid fa-clock-rotate-left time-indicator"></i> 3 days ago</p>
                </div>
            </div>
            <div class = "tags">
                <Tag :text="'Recommended'" :color="color"></Tag>
            </div>
            <div class = "card-footer">
                <p>{{ condensed }}</p>
                <div class = "arrow-container">
                    <i class="fa-solid fa-chevron-right arrow-popup"></i>
                    <i class="fa-solid fa-chevron-right arrow-popup"></i>
                    <i class="fa-solid fa-chevron-right arrow-popup"></i>
                </div>
            </div>
        </div>
    </div>
</template>

<style lang="scss" scoped>
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}
.subject-header {
  white-space: nowrap;        
  overflow: hidden;            
  text-overflow: ellipsis;    
  max-width: 90%;
  text-align: left;
  font-family: 'Inter';
  color: $text;
  text-transform: lowercase;
}
.code-text {
    color: $text;
    font-family: 'Lexend';
    font-weight: 200;
}
.card-container {
    position: relative;
    background-color: $secondary-background;
    width: 100%;
    aspect-ratio: 1/1;
    cursor: pointer;
    transition: transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out;
    display: flex;
    border-radius: 10px;
    overflow: hidden;
    z-index: 4;
}
.bg-pattern {
    z-index: 0;
    opacity: 0.1;
    width: 100%;
    aspect-ratio: 1/1;
    object-fit: cover;
}
.bg-icon {
    position: absolute;
    top: 50%;
    transform: translateY(-50%);
    right: -15%;
    opacity: 0.5;
    color: $text;
    width: 7.5vw;
    height: 7.5vw;
    color: $primary-color;
}
.sliver-color {
    position: absolute;
    width: 2px;
    height: 100%;
    background: radial-gradient(circle, #fdfddd, $primary-color);    
}
.expand-sliver-up {
    position: absolute;
    width: 2px;
    height: 50%;
    transition: height 1s ease-in-out;
    background-color: $secondary-background;
    z-index: 3;
}
.expand-sliver-down {
    position: absolute;
    top: 100%;
    width: 2px;
    height: 100%;
    transition: height 1s ease-in-out;
    background-color: $secondary-background;
    z-index: 3;
    transform: translateY(-50%);
}
.card-content {
    position: relative;
    z-index: 3;
    height: 100%;
    width: calc(100% - 2px);
    display: flex;
    flex-direction: column;
    padding: 2rem;
    align-self: right;
}
.card-container:hover {
    transform: scale(1.01);
    box-shadow: 0 0 16px 4px $primary-color;
}
.card-container:hover .expand-sliver-up,
.card-container:hover .expand-sliver-down {
    height: 0;
}
.arrow-container {
    display: flex;
    align-items: center;
    justify-content: left;
    width: 5%;
    height: 100%;
    position: relative;
}
.arrow-container i {
    font-size: 25px;
}
.tags {
    width: 100%;
    height: 100%;
    flex: 0.6;
    display: flex;
    overflow-y: hidden;
    overflow-x: scroll;
}
::-webkit-scrollbar {
    height: 0;
}
.arrow-popup {
    position: absolute;
    left: 0;
    top: 50%;
    transform: translateY(-50%);
    transition: left 0.4s ease-in-out, transform 0.4s ease-in-out;
}
.card-container:hover .arrow-popup:nth-child(2) {
    transition-delay: 0.05s;
}

.card-container:hover .arrow-popup:nth-child(3) {
    transition-delay: 0.1s;
}
.card-container:hover .arrow-popup {
    color: $primary-color;
    transform: translateY(-50%) scale(1.1);
}
.card-container:hover .arrow-popup:nth-child(2) {
    left: -10px;
}
.card-container:hover .arrow-popup:nth-child(3) {
    left: -20px;
}
.card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex: 1.3;
    font-family: 'Inter';
}
.card-body {
    flex: 5;
    display: flex;
    align-items: center;
    justify-content: space-between;
    width: 100%;
}
.last-attempted-date {
    font-size: 13px;
    font-family: 'Lexend';
    color: $text;
    opacity: 0.8;
    font-weight: 320;
}
.time-indicator-container {
    margin-right: 3px;
    min-width: 30%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
}
.body-left {
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items:flex-start;
    height: 100%;
    width: 100%;
    overflow: hidden;
}
.paper-type {
    font-size: 12px;
    color: lightgray;
    color: $text;
    font-family: 'Lexend';
    font-weight: 500;
    text-transform: lowercase;
}
.card-footer {
    margin-top: 20px;
    flex: 1;
    display: flex;
    justify-content: space-between;
    align-items: center;
    color: $text;
    font-family: 'Lexend';
    font-weight: 200;
}
.card-footer p {
    font-size: 13px;
}
.icon-container {
  position: relative;
  height: 100%;
  aspect-ratio: 1 / 1;
  border-radius: 2px;
  font-size: 25px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.icon-container::before {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  width: 150%;
  height: 150%;
  background: $primary-color;
  border-radius: 50%;
  transform: translate(-50%, -50%) scale(0);
  transition: transform 0.6s ease-out;
  pointer-events: none;
}
.card-container:hover .icon-container::before {
  transform: translate(-50%, -50%) scale(1);
}
.icon {
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
    color: $text;
    width: 75%;
    height: 75%;
    z-index: 5;
}
.done-indicator-container {
    height: 100%;
    width: 10%;
    position: relative;
}
.done-indicator {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    font-size: 26px;
    padding-right: 4%;
    z-index: 4;
    color: white;
    transition: color 0.5s ease-in-out;
}
.done-indicator-filling {
    color: transparent;
    z-index: 3;
}
.card-container:hover .done-indicator {
    color: $primary-color;
}
.card-container:hover .done-indicator-filling {
    color: white;
}
.pending-indicator-container {
    display: none;
    font-size: 26px;
}
.pending-icon {
    transition: color 0.5s ease-in-out;
}

@keyframes pulseClock {
    0% { transform: scale(1); opacity: 0.8; }
    50% { transform: scale(1.1); opacity: 1; }
    100% { transform: scale(1); opacity: 0.8; }
}

.pulse {
    animation: pulseClock 3s ease-in-out infinite;
}

.card-container:hover .pending-icon {
    color: red;
}
</style>