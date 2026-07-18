import { NavLink } from "react-router-dom";
import { useRole, type Role } from "../layout/RoleContext";

const links = [
  { to: "/", label: "Home" },
  { to: "/documents", label: "Document Library" },
  { to: "/graph", label: "Knowledge Graph" },
  { to: "/copilot", label: "Copilot" },
  { to: "/maintenance", label: "Maintenance & RCA" },
  { to: "/admin", label: "Admin" },
];

const roles: Role[] = ["Field Technician", "Maintenance Engineer", "RCA Lead", "Admin"];

export default function Sidebar() {
  const { role, setRole } = useRole();
  return (
    <aside className="flex w-64 flex-shrink-0 flex-col border-r border-slate-200 bg-white p-4">
      <div className="mb-6">
        <h1 className="text-lg font-bold text-brand-600">Inspiron</h1>
        <p className="text-xs text-slate-500">Industrial Knowledge Intelligence</p>
      </div>
      <nav className="flex flex-1 flex-col gap-1">
        {links.map((link) => (
          <NavLink
            key={link.to}
            to={link.to}
            end={link.to === "/"}
            className={({ isActive }) =>
              `rounded-md px-3 py-2 text-sm font-medium ${
                isActive ? "bg-brand-50 text-brand-700" : "text-slate-600 hover:bg-slate-100"
              }`
            }
          >
            {link.label}
          </NavLink>
        ))}
      </nav>
      <div className="mt-6 border-t border-slate-200 pt-4">
        <label className="text-xs font-medium text-slate-500" htmlFor="role-select">
          Viewing as
        </label>
        <select
          id="role-select"
          className="mt-1 w-full rounded-md border border-slate-300 p-2 text-sm"
          value={role}
          onChange={(e) => setRole(e.target.value as Role)}
        >
          {roles.map((r) => (
            <option key={r} value={r}>
              {r}
            </option>
          ))}
        </select>
      </div>
    </aside>
  );
}
