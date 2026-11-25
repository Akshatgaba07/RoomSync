import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth.jsx";
import { Alert, Badge, ScoreRing, Spinner } from "../components/Bits.jsx";

export default function MatchDetail() {
  const { id } = useParams(); const { spec } = useAuth();
  const [d, setD] = useState(null); const [err, setErr] = useState("");
  const [rating, setRating] = useState(0); const [sent, setSent] = useState(false);
  useEffect(() => { setD(null); api(`/api/matches/${id}`).then(setD).catch((e) => setErr(e.message)); }, [id]);
  if (err) return <div className="container section"><Alert tone="error">{err}</Alert><Link to="/matches" className="link">← Back</Link></div>;
  if (!d || !spec) return <Spinner />;
  const { student: s, result: r } = d;
  const labels = Object.fromEntries(spec.questions.map((q) => [q.key, q.label]));
  const rows = d.comparison.filter((c) => labels[c.key] && c.key !== "hostel");
  const sendFeedback = async () => { await api("/api/feedback", { method: "POST", body: { rating, partner_id: id } }); setSent(true); };

  return (
    <div className="container section">
      <Link to="/matches" className="link">← All recommendations</Link>
      <div className="card detail-head">
        <ScoreRing score={r.score} size={112} label="/100" />
        <div className="grow">
          <div className="row wrap"><h1 className="h2">{s.name}</h1>{s.is_demo && <Badge tone="demo">Synthetic demo</Badge>}</div>
          <div className="muted">{s.year} year · {s.hostel}</div>
          <div className="row wrap mt-s"><Badge tone={r.blocked ? "bad" : r.score >= 65 ? "good" : "neutral"}>{r.label}</Badge>
            <span className="muted small">Model confidence {Math.round(r.confidence * 100)}% · rule score {Math.round(r.rule_score * 100)}{r.latent_similarity != null && ` · lifestyle similarity ${Math.round(r.latent_similarity * 100)}`}</span></div>
        </div>
      </div>

      {r.dealbreakers.length > 0 && <Alert tone="error"><b>Dealbreaker conflict</b><ul>{r.dealbreakers.map((x, i) => <li key={i}>{x.message}</li>)}</ul></Alert>}
      {r.unverified.length > 0 && <Alert tone="warn"><b>Could not verify</b><ul>{r.unverified.map((x, i) => <li key={i}>{x.message}</li>)}</ul></Alert>}

      <div className="grid2 mt">
        <div className="card"><h3 className="good-t">Where you fit</h3>
          {r.strengths.length ? <ul className="plain">{r.strengths.map((x) => <li key={x}>✓ {x}</li>)}</ul> : <p className="muted">No standout strengths.</p>}</div>
        <div className="card"><h3 className="warn">Possible friction</h3>
          {r.mismatches.length ? <ul className="plain">{r.mismatches.map((x) => <li key={x}>! {x}</li>)}</ul> : <p className="muted">No major mismatches found.</p>}</div>
      </div>

      <div className="card mt"><h3>Compatibility breakdown</h3>
        <p className="muted small">Bars show how well you two line up in each area. ★ marks something either of you ranked as a top priority (weighted more).</p>
        <div className="stack">{r.dimensions.map((x) => (
          <div key={x.key}>
            <div className="row between"><span><b>{x.label}</b> {x.priority && <span title="Top priority">★</span>}</span><span className="muted small">{x.score == null ? "not enough data" : Math.round(x.score * 100)}</span></div>
            <div className="bar"><div className={x.verdict === "strength" ? "teal" : x.verdict === "mismatch" ? "amber" : "indigo"} style={{ width: `${(x.score ?? 0) * 100}%` }} /></div>
            <div className="muted small">{x.note}</div>
          </div>))}</div></div>

      <div className="card mt"><h3>Side by side</h3>
        <div className="table-wrap"><table><thead><tr><th>Question</th><th>You</th><th>{s.name}</th></tr></thead>
          <tbody>{rows.map((c) => <tr key={c.key}><td>{labels[c.key]}</td><td>{c.you ?? "—"}</td><td>{c.them ?? "—"}</td></tr>)}</tbody></table></div>
        <p className="small muted mt-s">Their dealbreakers: {s.dealbreakers.length ? s.dealbreakers.join(", ") : "none"} · Their priorities: {s.priorities.join(", ") || "—"}</p></div>

      {!s.is_demo && <div className="card mt"><h3>Lived together?</h3>
        <p className="muted small">Rating a real roommate arrangement is the only way RoomSync can ever learn what actually works.</p>
        {sent ? <Alert tone="info">Thanks — feedback saved.</Alert> : <div className="row wrap">{[1, 2, 3, 4, 5].map((n) => <button key={n} className={"scale-btn " + (rating === n ? "on" : "")} onClick={() => setRating(n)}>{n}</button>)}
          <button className="btn primary sm" disabled={!rating} onClick={sendFeedback}>Submit rating</button></div>}</div>}
      <p className="muted small mt">{d.disclaimer}</p>
    </div>
  );
}
