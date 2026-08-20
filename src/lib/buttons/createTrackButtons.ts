import type { Button, ButtonType } from "./buttonTypes";

export function createTrackButtons(): Button[] {
  const buttonTypes: ButtonType[] = ["Copy", "Flag", "Star", "Save"];
  return buttonTypes.map(type => ({
    type, 
    state: false,
    el: undefined
  }))
}