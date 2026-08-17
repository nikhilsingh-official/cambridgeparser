<template>
    <div class="rankings-box large">
        <div class="card-header">
            <div class="side-left">
                <div class="icon-header-container">
                    <i class="fa-solid fa-trophy"></i>
                </div>
                <p>Chemistry</p>
            </div>
            <div class="side-right">
                <i class="fa-solid fa-fire"></i>
                5
            </div>
        </div>
        <div class="card-body">
            <div class="percentage-container">
                95%
            </div>
            <div class="global-container">
                Better than 75% of the world!
            </div>
            <div class="meta-container">
                <div class="meta-mini">
                    <div class="mini-header">
                        <p>Papers Solved</p>
                    </div>
                    <div class="mini-main">
                        <p>23</p>
                    </div>
                </div>
                <div class="meta-mini">
                    <div class="mini-header">
                        <p>Qs Solved</p>
                    </div>
                    <div class="mini-main">
                        <p>117</p>
                    </div>
                </div>
                <div class="meta-mini">
                    <div class="mini-header">
                        <p>Total Time</p>
                    </div>
                    <div class="mini-main">
                        <p>112h 17m</p>
                    </div>
                </div>
            </div>
        </div>            
    </div>
</template>
<style scoped>
.rankings-box {
  position: absolute;
  border-radius: 8px;
  background-color: #202020;
  display: flex;
  flex-direction: column;
}

.large {
  width: 20%;
  aspect-ratio: 1/1;
  top: 30%;
  left: 50%;
  transform: translate(-50%, -50%);
}

.medium {
  width: 19%;
  aspect-ratio: 1/1;
  top: calc(40% + 80px);
  left: calc(63% + 100px);
  transform: translate(-50%, -50%);
}

.small {
  width: 18%;
  aspect-ratio: 1/1;
  top: calc(43% + 160px);
  left: calc(30.5% + 40px);
  transform: translate(-50%, -50%);
}

.card-header {
    display: flex;
    width: 100%;
    height: 12.5%;
    align-items: center;
    border-bottom-right-radius: 8px;
    border-bottom-left-radius: 8px;
    background-color: #141414;
}

.icon-header-container {
    height: 100%;
    aspect-ratio: 1/1;
    display: flex;
    align-items: center;
    justify-content: center;
}

.card-body {
    width: 100%;
    height: 88.5%;
    display: flex;
    flex-direction: column;
}

.percentage-container {
    height: 60%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 50px;
    font-weight: 700;
}

.global-container {
    font-size: 0.8vw;
    height: 7.5%;
    text-align: center;
}

.side-left {
    display: flex;
    align-items: center;
    height: 100%;
    width: 100%;
}

.side-right {
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    text-align: right;
    justify-content: flex-end;
    padding-right: 4%;
    column-gap: 5px;
}

.side-right i {
    color: red;
    background-color: orange;
    clip-path: polygon( 35.558% 1.055%,35.558% 1.055%,36.107% 0.67%,36.703% 0.372%,37.332% 0.161%,37.985% 0.035%,38.65% -0.005%,39.314% 0.041%,39.967% 0.172%,40.597% 0.388%,41.192% 0.689%,41.741% 1.074%,41.741% 1.074%,43.578% 2.604%,45.392% 4.157%,47.183% 5.734%,48.952% 7.336%,50.698% 8.962%,52.421% 10.614%,54.121% 12.292%,55.798% 13.995%,57.453% 15.724%,59.085% 17.48%,59.085% 17.48%,59.831% 16.63%,60.597% 15.769%,61.382% 14.903%,62.185% 14.036%,63.005% 13.174%,63.842% 12.321%,64.695% 11.482%,65.563% 10.663%,66.447% 9.868%,67.344% 9.102%,67.344% 9.102%,67.9% 8.711%,68.502% 8.408%,69.138% 8.192%,69.798% 8.062%,70.469% 8.02%,71.14% 8.065%,71.799% 8.198%,72.436% 8.418%,73.038% 8.726%,73.594% 9.121%,73.594% 9.121%,75.874% 11.114%,78.08% 13.217%,80.205% 15.413%,82.245% 17.689%,84.196% 20.029%,86.054% 22.419%,87.813% 24.842%,89.469% 27.285%,91.018% 29.732%,92.455% 32.168%,92.455% 32.168%,93.768% 34.561%,94.98% 36.95%,96.083% 39.318%,97.069% 41.65%,97.927% 43.931%,98.649% 46.145%,99.227% 48.276%,99.65% 50.31%,99.911% 52.231%,100% 54.023%,100% 54.023%,99.349% 61.367%,97.461% 68.375%,94.44% 74.945%,90.384% 80.973%,85.396% 86.357%,79.576% 90.994%,73.026% 94.779%,65.846% 97.611%,58.137% 99.386%,50% 100%,50% 100%,41.787% 99.385%,34.034% 97.609%,26.836% 94.775%,20.289% 90.987%,14.487% 86.348%,9.526% 80.961%,5.501% 74.93%,2.509% 68.358%,0.643% 61.348%,0% 54.004%,0% 54.004%,0.117% 51.706%,0.463% 49.319%,1.025% 46.853%,1.793% 44.32%,2.757% 41.729%,3.905% 39.091%,5.228% 36.416%,6.714% 33.716%,8.353% 31.001%,10.134% 28.281%,10.134% 28.281%,12.078% 25.511%,14.171% 22.727%,16.406% 19.938%,18.778% 17.153%,21.281% 14.382%,23.909% 11.634%,26.656% 8.918%,29.518% 6.243%,32.487% 3.619%,35.558% 1.055% );
}

.meta-container {
    height: 32.5%;
    border-bottom-right-radius: 8px;
    border-bottom-left-radius: 8px;
    padding: 5% 12% 5% 12%;
    display: flex;
    align-items: center;
    justify-content: space-between;
}

.meta-mini {
    width: 30%;
    height: 100%;
    display: flex;
    flex-direction: column;
}

.mini-header {
    padding: 1%;
    flex: 1;
    font-size: 0.5vw;
    text-align: center;
}

.mini-main {
    flex: 4;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.8vw;
    font-weight: 700;
}

.fa-trophy {
    color: gold;
}

.fa-medal {
    color: silver;
}

.fa-award {
    color: #CD7F32;
}
</style>