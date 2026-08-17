<script lang="ts" setup>
import { onMounted } from 'vue';

const colors = ['hsl(200, 100%, 60%)', 'hsl(220, 100%, 55%)', 'hsl(260, 100%, 60%)'];
const numWaves = colors.length;
const resolution = 60;

type WaveConfig = {
    frequency: number;
    amplitude: number;
    speed: number;
    phase: number;
};

const waveConfigs: WaveConfig[][] = [];

for (let z = 0; z < numWaves; z++) {
    const configs: WaveConfig[] = [];
    for (let i = 0; i < 4; i++) {
        configs.push({
            frequency: 0.002 + Math.random() * 0.012,
            amplitude: 0.02 + Math.random() * 0.03,
            speed: 0.001 + Math.random() * 0.003,
            phase: Math.random() * Math.PI * 3,
        });
    }
    waveConfigs.push(configs);
}

function generateWaveY(
    x: number,
    time: number,
    baselineY: number,
    height: number,
    configs: WaveConfig[]
): number {
    time /= 10;
    let y = 0;

    for (let i = 0; i < configs.length; i++) {
        const { frequency, amplitude, speed, phase } = configs[i];
        
        if(i % 2 == 0) {
            y += Math.sin(x * frequency + time * speed + phase) * amplitude;
        } else {
            y += Math.cos(x * frequency + time * speed + phase) * amplitude;
        }

        //cartoony effect
        //if (i % 2 === 0) {
        //    y += Math.sin(x * (frequency + (0.005 + Math.random() * 0.0002)) + time * speed * (0.001 + Math.random() * 0.001) + phase) * amplitude;
        //}
    }

    return baselineY - y * height;
}

onMounted(() => {
    const canvas = document.querySelector(".wave-canvas") as HTMLCanvasElement;
    const ctx = canvas.getContext('2d') as CanvasRenderingContext2D;

    const resizeCanvas = () => {
        canvas.width = canvas.clientWidth;
        canvas.height = canvas.clientHeight;
    };

    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);

    const draw = (time: number) => {
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        for (let z = 0; z < numWaves; z++) {
            const baselineY = ((z + 0.5) / numWaves) * canvas.height;
            const lineValues: [number, number][] = [];

            for (let x = 0; x <= canvas.width; x += resolution) {
                lineValues.push([x, generateWaveY(x, time, baselineY, canvas.height, waveConfigs[z])]);
            }
            lineValues.push([canvas.width, generateWaveY(canvas.width, time, baselineY, canvas.height, waveConfigs[z])]);

            ctx.beginPath();
            ctx.moveTo(lineValues[0][0], lineValues[0][1]);

            for (let i = 1; i < lineValues.length - 1; i++) {
                const xc = (lineValues[i][0] + lineValues[i + 1][0]) / 2;
                const yc = (lineValues[i][1] + lineValues[i + 1][1]) / 2;
                ctx.quadraticCurveTo(lineValues[i][0], lineValues[i][1], xc, yc);
            }

            ctx.lineTo(canvas.width, canvas.height);
            ctx.lineTo(0, canvas.height);
            ctx.closePath();

            ctx.fillStyle = colors[z % colors.length];
            ctx.globalAlpha = 0.6;
            ctx.fill();
            ctx.globalAlpha = 1.0;
        }

        requestAnimationFrame(draw);
    };

    requestAnimationFrame(draw);
});
</script>
<template>
    <div class="page-container">
        <canvas class="wave-canvas"></canvas>
        <div class="icon-container">
            <i class="fa-solid fa-flask-vial"></i>
            <h2>Chemistry</h2>
            <p>0620</p>
        </div>
        <!-- TOC Idea
        <div class="icon-underlay icon-underlay-1">
            <i class="fa-solid fa-chart-line"></i>
            <p>Progress Chart</p>
        </div>
        <div class="icon-underlay icon-underlay-2">
            <i class="fa-solid fa-chart-pie"></i>
            <p>Pie Chart</p>
        </div>
        <div class="icon-underlay icon-underlay-3">
            <i class="fa-solid fa-hexagon-nodes"></i>
            <p>Radar Chart</p>
        </div>
        <div class="icon-underlay icon-underlay-4">
            <i class="fa-solid fa-fire-flame-curved"></i>
            <p>Heatmap</p>
        </div>-->
        <div class="chart-container">
            <div class="chart-header">
                <p>Progress Chart</p>
            </div>
            <div class="chart-flex-container">
                <div class="chart">
                    
                </div>
                <div class="chart-metadata">
                    <div class="improvement-indicator">
                        <i class="fa-solid fa-arrow-up"></i> 12%
                    </div>
                    <div class="progress-circle">
                        <div class="circle-outer">
                            <div class="circle-inner">
                                <p>98%</p>
                            </div>
                        </div>
                        <svg id="progress-svg" xmlns="http://www.w3.org/2000/svg" version="1.1" width="160px" height="160px">
                            <defs>
                                <linearGradient id="GradientColor">
                                <stop offset="0%" stop-color="#DA22FF" />
                                <stop offset="100%" stop-color="#9733EE" />
                                </linearGradient>
                            </defs>
                            <circle cx="80" cy="80" r="70" stroke-linecap="round" />
                        </svg>
                    </div>
                    <div class="text-metadata">

                    </div>
                </div>
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
    background: linear-gradient(to bottom, hsl(210, 100%, 8%), hsl(220, 100%, 12%));
    position: relative;
    overflow-x: hidden;
}
.icon-container {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: 15%;
    aspect-ratio: 1/1;
    border-radius: 50%;
    background-color: hsl(210, 100%, 8%);
    z-index: 5;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-direction: column;
    z-index: 5;
}
.chart-container {
    width: 100%;
    height: 100%;
    display: flex;
    flex-direction: column;
}
.chart-header {
    width: 100%;
    height: 10%;
    display: flex;
    align-items: center;
    padding: 2vw;
    font-size: 30px;
    font-family: "Poppins";
}
.chart-flex-container {
    width: 100%;
    height: 90%;
    display: flex;
}
.chart {
    width: 100%;
    height: 100%;
}
.chart-metadata {
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-direction: column;
}
.progress-circle {
    width: 150px;
    aspect-ratio: 1/1;
    position: relative;
}
.circle-outer {
    width: 100%;
    height: 100%;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 6px 6px 10px -1px rgba(0, 0, 0, 1), 
    -6px -6px 10px -1px #001429cc;
}
.circle-inner {
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: "Poppins";
    font-weight: 700;
    font-size: 26px;
    width: 75%;
    height: 75%;
    border-radius: inherit;
    box-shadow: inset 6px 6px 10px -1px rgba(0, 0, 0, 1), inset -6px -6px 10px -1px #001429cc,  -0.5px -0.5px 0 #001429,  0.5px 0.5px 0 rgba(0, 0, 0, 0.15), 0 12px 10px -10px rgba(0, 0, 0, 0.05);
}
.progress {
  stroke: blue;
  stroke-dasharray: 314;
  stroke-dashoffset: calc(314 - (314 * 0.75));
  transition: stroke-dashoffset 0.5s ease;
}
@keyframes fadeInFromBottom {
    0% {
        opacity: 0;
        transform: translateY(30px);
    }
    100% {
        opacity: 1;
        transform: translateY(0);
    }
}
/*@keyframes shoot-1 {
    0% {
        top: 50%;
        left: 50%;
    }
    100% {
        top: 20%;
        left: 30%;
    }
}
@keyframes shoot-2 {
    0% {
        top: 50%;
        left: 50%;
    }
    100% {
        top: 80%;
        left: 30%;
    }
}
@keyframes shoot-3 {
    0% {
        top: 50%;
        left: 50%;
    }
    100% {
        top: 20%;
        left: 70%;
    }
}
@keyframes shoot-4 {
    0% {
        top: 50%;
        left: 50%;
    }
    100% {
        top: 80%;
        left: 70%;
    }
}
.icon-underlay {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: 10%;
    aspect-ratio: 1/1;
    border-radius: 50%;
    background-color: hsl(210, 100%, 10%);
    z-index: 4;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-direction: column;
    border: 1px solid hsl(210, 100%, 12%);
    cursor: pointer;
}
.icon-underlay-1 {
    animation: shoot-1 1s ease-in-out forwards;
}
.icon-underlay-2 {
    animation: shoot-2 1s ease-in-out forwards;
    animation-delay: 200ms;
}
.icon-underlay-3 {
    animation: shoot-3 1s ease-in-out forwards;
    animation-delay: 400ms;
}
.icon-underlay-4 {
    animation: shoot-4 1s ease-in-out forwards;
    animation-delay: 600ms;
}*/
.wave-canvas {
    width: 100%;
    height: 100%;
    z-index: 4;
}
.improvement-indicator {
    color: lightgreen;
    font-size: 30px;
}
circle {
    fill: none;
    stroke: url(#GradientColor);
    stroke-width: 10%;
    stroke-dashoffset: 440;
    stroke-dasharray: 660;
    transition: stroke-dasharray 1s ease linear;
}
#progress-svg {
    position: absolute;
    top: 0;
    left: 0;
    transform: rotate(180deg);
}
</style>