//  React - Next default
import React from "react";

// Components
import Navbar from "./_components/navbar";
import ClientOnly from "./_components/clientOnlyMinimal";

export default function MinimalLayout({
  children,
}: {
 readonly children: React.ReactNode;
}) {
  return (
    <ClientOnly>
      <div className="w-full max-w-[1440px] mx-auto flex flex-col min-h-full">
        <Navbar />
        <div className="w-full min-h-full mx-auto">{children}</div>
      </div>
    </ClientOnly>
  );
}
