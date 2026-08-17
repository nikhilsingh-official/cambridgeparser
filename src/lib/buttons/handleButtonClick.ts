import { addEventLog } from "../utils/addEventLog";
import type { EventLogs } from "../utils/utilsTypes";
import type { Button } from "./buttonTypes";

export function handleButtonClick(button: Button, eventLogs: EventLogs) {
  if(!button.state) {
    button.state = true;
    if(button.el) {
      button.el.classList.add("btn-active");
      button.el.classList.remove("btn-inactive");
    }
    addEventLog(eventLogs, button.type, "Selection", button.parent!.questionNum, undefined);
  } else {
    button.state = false;
    if(button.el) {
      button.el.classList.add("btn-inactive");
      button.el.classList.remove("btn-active");
    }
    addEventLog(eventLogs, button.type, "Deselection", button.parent!.questionNum, undefined);
  }
}