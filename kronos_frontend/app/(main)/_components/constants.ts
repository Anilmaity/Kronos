// Icons
import { IconType } from "react-icons";
import {
  MdDashboard,
  MdArchive,
  MdOutlineHub,
  MdOutlineTimeline,
  MdCandlestickChart,
} from "react-icons/md";
import { HiChartPie, HiDocumentText } from "react-icons/hi";
import { FaRectangleList } from "react-icons/fa6";
import { IoSettingsOutline, IoFlashOutline } from "react-icons/io5";

export interface SidebarLinks {
  title: string;
  icon: IconType;
  path: string;
}
export interface SidebarLinkArrayProps extends SidebarLinks {}

export const sidebarLinkArray: SidebarLinkArrayProps[] = [
  {
    title: "Dashboard",
    path: "/dashboard",
    icon: MdDashboard,
  },
  {
    title: "Chart",
    path: "/chart",
    icon: MdCandlestickChart,
  },
  {
    title: "Accounts",
    path: "/accounts",
    icon: HiChartPie,
  },
  {
    title: "Marketplace",
    path: "/marketplace",
    icon: FaRectangleList,
  },
  {
    title: "Backtests",
    path: "/backtests",
    icon: FaRectangleList,
  },
  {
    title: "Signals",
    path: "/signals",
    icon: IoFlashOutline,
  },
  {
    title: "Archive",
    path: "/archive",
    icon: MdArchive,
  },
  {
    title: "Strategy Manager",
    path: "/manager",
    icon: MdOutlineHub,
  },
  {
    title: "Manager Backtest",
    path: "/manager-backtest",
    icon: MdOutlineTimeline,
  },
  {
    title: "Reports",
    path: "/reports",
    icon: HiDocumentText,
  },
  {
    title: "Settings",
    path: "/settings",
    icon: IoSettingsOutline,
  },
];
