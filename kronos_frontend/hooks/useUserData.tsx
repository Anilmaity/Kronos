import { UserDetailsProps } from "@/types";
import { create } from "zustand";

interface UserDataProps {
  userData: UserDetailsProps;
  setUserData: (userData: UserDetailsProps) => void;
}

const initialState: UserDetailsProps = {
  id: "",
  email: "",
  firstName: "",
  lastName: "",
  isActive: false,
  isStaff: false,
  dateJoined: "",
  balance: 0,
  clientCode: "",
  username: "",
  profileImage: "",
  profileDescription: "",
  isSuperuser: false,
  todayTotalProfitLoss: 0,
};

export const useUserData = create<UserDataProps>((set) => ({
  userData: initialState,
  setUserData: (userData: UserDetailsProps) => set({ userData }),
}));
