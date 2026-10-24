import type { Metadata } from "next";
import { Header } from "@/components/layout/Header";
import { MobileNav } from "@/components/layout/MobileNav";
import { FloatingAssistant } from "@/components/agent/FloatingAssistant";

export const metadata: Metadata = {
  robots: {
    index: false,
    follow: false,
  },
};

export default function WorkspaceLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col h-screen w-full overflow-hidden bg-background text-foreground">
      <Header />
      <main className="relative flex-1 min-h-0 overflow-y-auto pb-16 md:pb-0">
        {children}
        <FloatingAssistant />
      </main>
      <MobileNav />
    </div>
  );
}