import { Link, NavLink, useNavigate } from "react-router-dom";
import { useState } from "react";
import { useAuth } from "../auth.jsx";

export function Logo() {
  return (
    <Link to="/" className="logo" aria-label="RoomSync home">
      <svg width="30" height="30" viewBox="0 0 32 32" aria-hidden="true">
        <rect width="32" height="32" rx="9" fill="#4f46e5" />
        <path d="M7 22V13l9-6 9 6v9" fill="none" stroke="#fff" strokeWidth="2" strokeLinejoin="round" />
        <circle cx="12.5" cy="18" r="2.4" fill="#5eead4" /><circle cx="19.5" cy="18" r="2.4" fill="#fff" />
      </svg>
      <span>Room<b>Sync</b></span>
    </Link>
  );
}

export default function Layout({ children }) {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  const [open, setOpen] = useState(false);
  const links = user?.profile_complete
    ? [["/dashboard", "Dashboard"], ["/matches", "Roommates"], ["/preferences", "Preferences"], ["/profile", "Profile"]]
    : [];
  return (
    <div className="app">
      <header className="topbar">
        <div className="container topbar-inner">
          <Logo />
          <button className="burger" onClick={() => setOpen(!open)} aria-label="Menu">☰</button>
          <nav className={"nav " + (open ? "open" : "")} onClick={() => setOpen(false)}>
            {links.map(([to, t]) => <NavLink key={to} to={to}>{t}</NavLink>)}
            <NavLink to="/university">University Admin</NavLink>
            {user ? (
              <>
                {!user.profile_complete && <NavLink to="/onboarding">Finish profile</NavLink>}
                <button className="btn ghost sm" onClick={() => { logout(); nav("/"); }}>Log out</button>
              </>
            ) : (
              <><NavLink to="/login">Log in</NavLink><Link className="btn primary sm" to="/signup">Get started</Link></>
            )}
          </nav>
        </div>
      </header>
      <main>{children}</main>
      <footer className="footer"><div className="container">
        RoomSync is a university project. Compatibility scores are estimates from questionnaire answers, not guarantees.
        Demo students are synthetic and not real people.
      </div></footer>
    </div>
  );
}
