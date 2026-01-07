import { Outlet } from "react-router-dom";
import { Header } from "./Header";
import { AppSidebar } from "./AppSidebar";

export function Layout() {
  return (
    <div className="min-h-screen bg-background font-sans antialiased">
      <Header />
      <div className="flex container">
         <AppSidebar />
         <main className="flex-1 py-6 md:px-6 overflow-hidden">
            <Outlet />
         </main>
      </div>
    </div>
  );
}
