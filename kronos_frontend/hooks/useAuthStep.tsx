import { create } from "zustand";
import { STORAGE_KEYS } from "@/lib/storage";

type AuthStep = "LOGIN" | "OTP";

interface AuthStepState {
  step: AuthStep;
  setStep: (step: AuthStep) => void;
}

export const useAuthStep = create<AuthStepState>((set) => ({
  step:
    typeof window === "undefined"
      ? "LOGIN"
      : (localStorage.getItem(STORAGE_KEYS.authStep) as AuthStep) || "LOGIN",
  setStep: (step) => {
    set({ step });
    localStorage.setItem(STORAGE_KEYS.authStep, step);
  },
}));
