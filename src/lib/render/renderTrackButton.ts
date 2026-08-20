import type { EventLogs } from "../utils/utilsTypes";
import {createElement } from 'lucide'
import { BUTTON_CONFIG, type Button } from "@/lib/buttons/buttonTypes";
import { handleButtonClick } from "@/lib/buttons/handleButtonClick";

export function renderTrackButton(button: Button, eventLogs: EventLogs) {

    const buttonElement = document.createElement("button");
    buttonElement.classList.add("track-button");

    buttonElement.addEventListener("click", () => {
      handleButtonClick(button, eventLogs);
    });

    const icon = BUTTON_CONFIG[button.type];

    buttonElement.appendChild(createElement(icon));

    button.el = buttonElement;

}