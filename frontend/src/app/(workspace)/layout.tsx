import { Sidebar } from "@/components/layout/Sidebar";
import { FloatingAssistant } from "@/components/agent/FloatingAssistant";

export default function WorkspaceLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex h-screen w-full overflow-hidden bg-background">
      <Sidebar />
      <main className="relative flex-1 overflow-y-auto">
        {children}
        <FloatingAssistant />
      </main>
    </div>
  );
}