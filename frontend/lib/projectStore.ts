import { create } from "zustand";

interface OpenFile {
  path: string;
  content: string;
  language: string | null;
  line_count: number;
  highlightFrom: number | null;
  highlightTo: number | null;
}

interface ProjectStore {
  openFile: OpenFile | null;
  setOpenFile: (file: OpenFile) => void;
  clearFile: () => void;
  setHighlight: (from: number, to: number) => void;
}

export const useProjectStore = create<ProjectStore>((set) => ({
  openFile: null,
  setOpenFile: (file) => set({ openFile: file }),
  clearFile: () => set({ openFile: null }),
  setHighlight: (from, to) =>
    set((state) =>
      state.openFile
        ? { openFile: { ...state.openFile, highlightFrom: from, highlightTo: to } }
        : state
    ),
}));
