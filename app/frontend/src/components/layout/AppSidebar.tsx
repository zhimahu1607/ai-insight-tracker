import { Link, useLocation } from "react-router-dom";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Home, FileText, Newspaper, BarChart2 } from "lucide-react";

export function AppSidebar() {
  const location = useLocation();
  const pathname = location.pathname;

  const items = [
    { title: "Reports", url: "/reports", icon: BarChart2 },
    { title: "Papers", url: "/papers", icon: FileText },
    { title: "News", url: "/news", icon: Newspaper },
  ];

  return (
    <div className="pb-12 w-64 border-r hidden md:block h-[calc(100vh-3.5rem)] sticky top-14 overflow-y-auto">
      <div className="space-y-4 py-4">
        <div className="px-3 py-2">
          <h2 className="mb-2 px-4 text-lg font-semibold tracking-tight">
            Discover
          </h2>
          <div className="space-y-1">
            {items.map((item) => (
              <Button
                key={item.url}
                variant={pathname === item.url ? "secondary" : "ghost"}
                className={cn(
                  "w-full justify-start",
                  pathname === item.url && "bg-secondary"
                )}
                asChild
              >
                <Link to={item.url}>
                  <item.icon className="mr-2 h-4 w-4" />
                  {item.title}
                </Link>
              </Button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

