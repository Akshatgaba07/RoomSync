import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth.jsx";
import Questionnaire from "../components/Questionnaire.jsx";
import { Spinner } from "../components/Bits.jsx";

export default function Onboarding() {
  const { user, spec, refresh } = useAuth();
  const nav = useNavigate();
  if (!spec || !user) return <Spinner />;
  const save = async (payload) => { await api("/api/profile", { method: "PUT", body: payload }); };
  return (
    <div className="container narrow section">
      <div className="page-head"><span className="eyebrow">Welcome, {user.name.split(" ")[0]}</span>
        <h1 className="h2">Tell us how you live</h1>
        <p className="muted">Answer honestly — the best match is the one who fits who you really are, not who you'd like to be. Your progress saves at each step.</p></div>
      <Questionnaire spec={spec} initial={user} onSave={save} onDone={async () => { const me = await refresh(); nav(me?.profile_complete ? "/dashboard" : "/profile"); }} />
    </div>
  );
}
