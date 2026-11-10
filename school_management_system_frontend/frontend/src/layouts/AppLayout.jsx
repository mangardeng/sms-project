import { useState } from "react";
import { Outlet, useLocation } from "react-router-dom";

import { NAV_ITEMS } from "./navConfig";
import Sidebar from "./Sidebar";
import Topbar from "./Topbar";

function titleForPath(pathname) {
  const match = NAV_ITEMS.find((item) => pathname.startsWith(item.to));
  return match?.label || "Dashboard";
}

export default function AppLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const location = useLocation();

  return (
    <div className="app-shell">
      <Sidebar open={sidebarOpen} onNavigate={() => setSidebarOpen(false)} />
      <div className="main-column">
        <Topbar title={titleForPath(location.pathname)} onToggleSidebar={() => setSidebarOpen((o) => !o)} />
        <main className="content-area">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
