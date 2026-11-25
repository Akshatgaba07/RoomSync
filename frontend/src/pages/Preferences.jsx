import { useState } from "react";
import { api } from "../api";
import { useAuth } from "../auth.jsx";
import { PrefEditor } from "../components/Questionnaire.jsx";
import { Alert, Spinner } from "../components/Bits.jsx";

export default function Preferences() {
  const { user, spec, refresh } = useAuth();
  const [db, setDb] = useState(user?.dealbreakers || []); const [pr, setPr] = useState(user?.priorities || []);
  const [msg, setMsg] = useState(""); const [err, setErr] = useState("");
  if (!user || !spec) return <Spinner />;
  const save = async () => {
    setErr(""); setMsg("");
    try { await api("/api/profile", { method: "PUT", body: { answers: user.answers, dealbreakers: db, priorities: pr } }); await refresh(); setMsg("Saved. Your recommendations were recalculated."); }
    catch (e) { setErr(e.message); }
  };
  return (
    <div className="container narrow section">
      <div className="page-head"><h1 className="h2">Matching preferences</h1><p className="muted">Tune your dealbreakers and priorities any time.</p></div>
      <div className="card"><PrefEditor spec={spec} dealbreakers={db} priorities={pr} setDealbreakers={setDb} setPriorities={setPr} />
        {err && <Alert tone="error">{err}</Alert>}{msg && <Alert tone="info">{msg}</Alert>}
        <div className="q-actions"><span /><button className="btn primary" disabled={pr.length === 0} onClick={save}>Save preferences</button></div></div>
    </div>
  );
}
