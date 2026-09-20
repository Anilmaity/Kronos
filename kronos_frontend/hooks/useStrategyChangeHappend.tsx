import { create } from "zustand";

type State = {
  strategyChangeHappend: boolean;
  setStrategyChangeHappend: (value: boolean) => void;
};

export const useStrategyChangeHappend = create<State>((set) => ({
  strategyChangeHappend: false,
  setStrategyChangeHappend: (value: boolean) =>
    set({ strategyChangeHappend: value }),
}));
