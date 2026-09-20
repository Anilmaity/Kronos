"use client";
import { ScaleLoader } from "react-spinners";

const Loader = () => {
  return (
    <div className="h-[70vh] flex flex-col gap-4 justify-center items-center">
      <ScaleLoader
        height={28}
        width={3}
        radius={1}
        margin={3}
        color="var(--tv-accent)"
      />
      <span className="text-xs" style={{ color: "var(--tv-text-soft)" }}>
        Loading
      </span>
    </div>
  );
};

export default Loader;
