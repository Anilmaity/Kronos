// Components
import ClientOnly from "@/components/clientOnly";
import Sidebar from "./_components/sidebar";
import Navbar from "./_components/navbar";
import NavScroll from "./navScroll";

export default function Layout({ children }: { readonly children: React.ReactNode }) {
  return (
    <ClientOnly>
      <div className="w-full lg:max-w-[1440px] mx-auto flex flex-col min-h-full">
        <Navbar />
        <div className="flex items-start min-h-full">
          <Sidebar />
          <div className="w-full min-h-full px-1 xs:px-4 md:px-6 lg:px-10 xl:px-16 py-[42px] mx-auto overflow-y-auto">
            <NavScroll>{children}</NavScroll>
          </div>
        </div>
      </div>
    </ClientOnly>
  );
}
