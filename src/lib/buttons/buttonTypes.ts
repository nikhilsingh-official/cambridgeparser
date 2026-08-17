import { Copy, Flag, Star, Archive } from 'lucide'

export type ButtonTrack = { y: number; questionNum: number; el?: HTMLDivElement; buttons: Button[] }
export type PageButtonTracks = ButtonTrack[]
export type DocumentButtonTracks = PageButtonTracks[]
export const BUTTON_CONFIG = {
  Copy: Copy,
  Flag: Flag,
  Star: Star,
  Save: Archive
} as const;

export type ButtonType = keyof typeof BUTTON_CONFIG;
export type Button = {
  type: ButtonType;
  state: boolean;
  el?: HTMLButtonElement;
  parent?: ButtonTrack;
}