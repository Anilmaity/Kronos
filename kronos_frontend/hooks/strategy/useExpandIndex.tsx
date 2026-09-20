import { create } from "zustand";

type ExpandIndexStore = {
  expandIndex: number[];
  setExpandIndex: (index: number[]) => void;
};

export const useExpandIndex = create<ExpandIndexStore>((set) => ({
  expandIndex: [],
  setExpandIndex: (index) => set(() => ({ expandIndex: index })),
}));