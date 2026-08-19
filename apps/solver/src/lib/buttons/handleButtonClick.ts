// switched to the typed button constructor.
import { logButton } from "../utils/addEventLog";
import { ButtonAction } from "@/lib/types/enums";
import type { EventLogs } from "../utils/utilsTypes";
import type { Button } from "./buttonTypes";

export function handleButtonClick(button: Button, eventLogs: EventLogs) {
  if(!button.state) {
    button.state = true;
    if(button.el) {
      button.el.classList.add("btn-active");
      button.el.classList.remove("btn-inactive");
    }
    logButton(eventLogs, button.type, ButtonAction.Selection, button.parent!.questionNum);
  } else {
    button.state = false;
    if(button.el) {
      button.el.classList.add("btn-inactive");
      button.el.classList.remove("btn-active");
    }
    logButton(eventLogs, button.type, ButtonAction.Deselection, button.parent!.questionNum);
  }
}