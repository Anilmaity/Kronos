import { create } from "zustand";

interface NavbarState {
  isOpen: boolean;
  toggle: () => void;
  onOpen: () => void;
  onClose: () => void;
}

export const useNavbar = create<NavbarState>((set) => ({
  isOpen: false,
  toggle: () => set((state) => ({ isOpen: !state.isOpen })),
  onOpen: () => set({ isOpen: true }),
  onClose: () => set({ isOpen: false }),
}));
