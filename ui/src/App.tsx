import { NavLink, Route, Routes } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import Reports from "./pages/Reports";
import ReportDetail from "./pages/ReportDetail";
import ReportSettings from "./pages/ReportSettings";
import Historicals from "./pages/Historicals";
import Logs from "./pages/Logs";
import Alerts from "./pages/Alerts";

export default function App() {
  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">USDA Monitor</div>
        <nav>
          <NavLink to="/" end>
            Dashboard
          </NavLink>
          <NavLink to="/reports">Reports</NavLink>
          <NavLink to="/logs">Logs</NavLink>
          <NavLink to="/alerts">Alerts</NavLink>
        </nav>
      </aside>
      <main className="content">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/reports" element={<Reports />} />
          <Route path="/reports/:id" element={<ReportDetail />} />
          <Route path="/reports/:id/settings" element={<ReportSettings />} />
          <Route path="/reports/:id/historicals" element={<Historicals />} />
          <Route path="/logs" element={<Logs />} />
          <Route path="/alerts" element={<Alerts />} />
        </Routes>
      </main>
    </div>
  );
}
