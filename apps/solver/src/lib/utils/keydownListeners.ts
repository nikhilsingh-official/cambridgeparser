import type { Ref } from "vue";
import type { HighlightMode } from "./utilsTypes";

export function createKeydownHandlers(modeRef: Ref<HighlightMode>) {

  const handleKeydown = (e: KeyboardEvent) => {
    switch (e.code) {
      case "KeyC":
        modeRef.value = "correct";
        break;
      case "KeyE":
        modeRef.value = "eliminated";
        break;
    }
  };

  const register = (win: Window) => {
    win.addEventListener("keydown", handleKeydown);
  };

  const unregister = (win: Window) => {
    win.removeEventListener("keydown", handleKeydown);
  };

  return { register, unregister };
}