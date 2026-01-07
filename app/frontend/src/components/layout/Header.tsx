import { Menu } from "lucide-react";
import { Link, useLocation } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import { Home, FileText, Newspaper, BarChart2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { useState } from "react";

export function Header() {
  const location = useLocation();
  const pathname = location.pathname;
  const [open, setOpen] = useState(false);

  const items = [
    { title: "Home", url: "/", icon: Home },
    { title: "Papers", url: "/papers", icon: FileText },
    { title: "News", url: "/news", icon: Newspaper },
    { title: "Reports", url: "/reports", icon: BarChart2 },
  ];

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container flex h-14 items-center">
        <Sheet open={open} onOpenChange={setOpen}>
          <SheetTrigger asChild>
            <Button variant="ghost" className="mr-2 px-0 text-base hover:bg-transparent focus-visible:bg-transparent focus-visible:ring-0 focus-visible:ring-offset-0 md:hidden">
              <Menu className="h-6 w-6" />
              <span className="sr-only">Toggle Menu</span>
            </Button>
          </SheetTrigger>
          <SheetContent side="left" className="pr-0">
             <div className="px-7">
               <Link to="/" className="flex items-center" onClick={() => setOpen(false)}>
                 <span className="font-bold">AI Insight Tracker</span>
               </Link>
             </div>
             <div className="flex flex-col gap-4 py-4">
                {items.map((item) => (
                  <Link
                    key={item.url}
                    to={item.url}
                    onClick={() => setOpen(false)}
                    className={cn(
                      "block px-2 py-1 text-lg",
                       pathname === item.url ? "font-semibold text-primary" : "text-muted-foreground"
                    )}
                  >
                    {item.title}
                  </Link>
                ))}
             </div>
          </SheetContent>
        </Sheet>
        <div className="mr-4 hidden md:flex">
          <Link to="/" className="mr-6 flex items-center space-x-2">
            <span className="hidden font-bold sm:inline-block">
              AI Insight Tracker
            </span>
          </Link>
        </div>
      </div>
    </header>
  );
}

