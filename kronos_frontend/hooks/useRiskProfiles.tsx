import { RiskProfileTableData } from "@/app/(main)/accountprofile/_components/main";
import { create } from "zustand";

interface UseRiskProfilesState {
  riskProfiles: RiskProfileTableData[];
  setRiskProfiles: (riskProfiles: RiskProfileTableData[]) => void;
}

export const useRiskProfiles = create<UseRiskProfilesState>((set) => ({
  riskProfiles: [],
  setRiskProfiles: (riskProfiles) => set({ riskProfiles }),
}));
