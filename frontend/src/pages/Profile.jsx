import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth.jsx";
import Questionnaire from "../components/Questionnaire.jsx";
import { Alert, Badge, Spinner } from "../components/Bits.jsx";

export default function Profile() {
  const { user, spec, refresh } = useAuth(); const nav = useNavigate();
  const [editing, setEditing] = useState(false); const [name, setName] = useState(user?.name || ""); const [msg, setMsg] = useState("");
  if (!user || !spec) return <Spinner />;
  const labels = Object.fromEntries(spec.questions.map((q) => [q.key, q]));
  const saveName = async () => { await api("/api/me", { method: "PATCH", body: { name } }); await refresh(); setMsg("Name updated."); };
  if (editing) return (
    <div className="container narrow section"><h1 className="h2">Edit your questionnaire</h1>
      <p className="muted">Saving recalculates your recommendations immediately.</p>
      <Questionnaire spec={spec} initial={user} finishLabel="Save changes" onSave={async (p) => { await api("/api/profile", { method: "PUT", body: p }); }}
        onDone={async () => { await refresh(); setEditing(false); nav("/matches"); }} /></div>);
  return (
    <div className="container narrow section">
      <h1 className="h2">Your profile</h1>
      <div className="card stack">
        <label>Display name<input value={name} onChange={(e) => setName(e.target.value)} /></label>
        <div className="row wrap"><button className="btn primary sm" disabled={!name.trim() || name === user.name} onClick={saveName}>Save name</button>
          <span className="muted small">{user.email}</span>{user.is_demo && <Badge tone="demo">Synthetic demo account</Badge>}</div>
        {msg && <Alert tone="info">{msg}</Alert>}
      </div>
      <div className="card mt"><div className="row between"><h3>Questionnaire</h3><button className="btn primary sm" onClick={() => setEditing(true)}>{user.profile_complete ? "Edit answers" : "Continue"}</button></div>
        <div className="progress"><div style={{ width: `${user.completeness * 100}%` }} /></div>
        <p className="muted small">{Math.round(user.completeness * 100)}% complete{user.missing.length > 0 && ` · missing: ${user.missing.join(", ")}`}</p>
        <div className="table-wrap"><table><tbody>{Object.entries(user.answers).map(([k, v]) => <tr key={k}><td>{labels[k]?.label || k}</td><td>{String(v)}</td></tr>)}</tbody></table></div></div>
    </div>
  );
}
