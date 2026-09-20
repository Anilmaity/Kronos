import { create } from "zustand";
import { STORAGE_KEYS } from "@/lib/storage";

type State = {
  userToken: string;
  setUserToken: (token: string) => void;
};

export const useUserToken = create<State>((set) => ({
  userToken:
    typeof window === "undefined"
      ? ""
      : localStorage.getItem(STORAGE_KEYS.token) ?? "",
  setUserToken: (token: string) => set({ userToken: token }),
}));
