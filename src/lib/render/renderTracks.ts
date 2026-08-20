import type { EventLogs } from "../utils/utilsTypes";
import type { DocumentButtonTracks } from "@/lib/buttons/buttonTypes";
import { renderTrackButton } from "@/lib/render/renderTrackButton";
import type { Ref } from "vue";

export function renderTracks(buttonTracks: DocumentButtonTracks, pageIndexes: number[], totalScale: Ref<number>, eventLogs: EventLogs) {
    const pdfViewer: HTMLIFrameElement = document.querySelector("#pdf-viewer") as HTMLIFrameElement;
    const viewer: Element | null | undefined = pdfViewer?.contentDocument?.querySelector(`#viewer`);
    const pages = viewer?.querySelectorAll('.page');
    if(!pages) return;

    console.log("Tracks:")
    console.log(buttonTracks)

    for(let pageIndex = 0; pageIndex < buttonTracks.length; pageIndex++) {

        if(!pageIndexes.includes(pageIndex)) continue;

        const page = pages[pageIndex];
        if(!page) continue;

        const pageTracks = buttonTracks[pageIndex];
        if(!pageTracks) continue;

        for(let trackIndex = 0; trackIndex < pageTracks.length; trackIndex++) {
            const track = pageTracks[trackIndex]!;

            const trackEl = document.createElement("div");

            trackEl.classList.add("button-track");

            trackEl.style.top = `${track.y * totalScale.value}px`;
            page.appendChild(trackEl);

            track.el = trackEl;

            track.buttons.forEach((btn) => {
                renderTrackButton(btn, eventLogs); 
                trackEl.appendChild(btn.el!);
            })

        }

    }

}