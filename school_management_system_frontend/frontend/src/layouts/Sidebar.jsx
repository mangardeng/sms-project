import { NavLink } from "react-router-dom";

import { useAuth } from "../context/AuthContext";
import { navItemsForRole } from "./navConfig";

export default function Sidebar({ open, onNavigate }) {
  const { user } = useAuth();
  const items = navItemsForRole(user?.role);

  return (
    <aside className={`sidebar ${open ? "open" : ""}`}>
      <div className="sidebar-brand">
        <span className="school-name">Greenfield SMS</span>
        <span className="school-tag">School Management System</span>
      </div>

      <nav className="sidebar-nav">
        {items.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            onClick={onNavigate}
            className={({ isActive }) => (isActive ? "active" : "")}
          >
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-footer">Signed in as {user?.role_display || user?.role}</div>
    </aside>
  );
}
