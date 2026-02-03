import { SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { AppSidebar, MobileNav, MobileHeader } from "./AppSidebar";

interface AppLayoutProps {
  children: React.ReactNode;
}

export function AppLayout({ children }: AppLayoutProps) {
  return (
    <SidebarProvider defaultOpen={true}>
      <div className="min-h-screen flex w-full bg-background">
        {/* Desktop Sidebar */}
        <div className="hidden md:block">
          <AppSidebar />
        </div>

        {/* Main Content */}
        <main className="flex-1 flex flex-col min-h-screen">
          {/* Mobile Header */}
          <MobileHeader />

          {/* Desktop Header */}
          <header className="hidden md:flex items-center gap-4 p-4 border-b border-border/50">
            <SidebarTrigger />
          </header>

          {/* Page Content */}
          <div className="flex-1 p-4 md:p-6 pb-20 md:pb-6 overflow-auto">
            {children}
          </div>
        </main>

        {/* Mobile Bottom Navigation */}
        <MobileNav />
      </div>
    </SidebarProvider>
  );
}
