import { useState } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth.jsx";
import { Alert } from "../components/Bits.jsx";

export default function AuthPage({ mode }) {
  const { user, login, signup } = useAuth();
  const nav = useNavigate();
  const loc = useLocation();
  const [f, setF] = useState({ name: "", email: "", password: "" });
  const [err, setErr] = useState(""); const [busy, setBusy] = useState(false);
  const isSignup = mode === "signup";
  if (user) return <Navigate to={user.profile_complete ? "/dashboard" : "/onboarding"} replace />;

  const submit = async (e) => {
    e.preventDefault(); setErr(""); setBusy(true);
    try {
      const me = isSignup ? await signup(f.name, f.email, f.password) : await login(f.email, f.password);
      nav(me?.profile_complete ? loc.state?.from || "/dashboard" : "/onboarding", { replace: true });
    } catch (e2) { setErr(e2.message); } finally { setBusy(false); }
  };
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  return (
    <div className="container narrow section">
      <div className="card auth">
        <h2>{isSignup ? "Create your account" : "Welcome back"}</h2>
        <form onSubmit={submit} className="stack" noValidate>
          {isSignup && <label>Full name<input value={f.name} onChange={set("name")} autoComplete="name" required /></label>}
          <label>Email<input type="email" value={f.email} onChange={set("email")} autoComplete="email" required /></label>
          <label>Password<input type="password" value={f.password} onChange={set("password")} minLength={8}
            autoComplete={isSignup ? "new-password" : "current-password"} required />
            {isSignup && <span className="hint">At least 8 characters.</span>}</label>
          {err && <Alert tone="error">{err}</Alert>}
          <button className="btn primary" disabled={busy}>{busy ? "Please wait…" : isSignup ? "Create account" : "Log in"}</button>
        </form>
        <p className="muted small center-t">{isSignup ? <>Have an account? <Link to="/login">Log in</Link></> : <>New here? <Link to="/signup">Create an account</Link></>}</p>
        {!isSignup && <Alert tone="info"><b>Local demo:</b> run the seed script, then log in as <code>demo01@roomsync.demo</code> / <code>RoomSync-demo-1</code>. Demo students are synthetic.</Alert>}
      </div>
    </div>
  );
}
