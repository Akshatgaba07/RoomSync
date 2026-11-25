import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { Alert, Badge, ScoreRing, Spinner } from "../components/Bits.jsx";

export default function Matches() {
  const [strict, setStrict] = useState(true); const [demo, setDemo] = useState(true); const [k, setK] = useState(10);
  const [data, setData] = useState(null); const [err, setErr] = useState("");
  useEffect(() => {
    setData(null);
    api(`/api/matches?k=${k}&strict=${strict}&include_demo=${demo}`).then(setData).catch((e) => setErr(e.message));
  }, [strict, demo, k]);
  return (
    <div className="container section">
      <div className="page-head"><h1 className="h2">Recommended roommates</h1>
        <p className="muted">Ranked by estimated compatibility. Only students in your hostel type are considered.</p></div>
      <div className="card filters">
        <label className="check"><input type="checkbox" checked={strict} onChange={(e) => setStrict(e.target.checked)} /> Hide dealbreaker conflicts</label>
        <label className="check"><input type="checkbox" checked={demo} onChange={(e) => setDemo(e.target.checked)} /> Include synthetic demo students</label>
        <label className="check">Show <select value={k} onChange={(e) => setK(+e.target.value)}>{[5, 10, 20, 50].map((n) => <option key={n}>{n}</option>)}</select></label>
      </div>
      {err && <Alert tone="error">{err}</Alert>}
      {!data && !err && <Spinner text="Scoring every eligible pair…" />}
      {data && <>
        <p className="muted small">{data.returned} shown · {data.pool_size} students in the pool{strict && ` · ${data.excluded_by_dealbreakers} hidden by dealbreakers`}</p>
        {data.matches.length === 0 && <Alert tone="info">No matches with the current filters.</Alert>}
        <div className="stack">{data.matches.map((x) => (
          <Link to={`/matches/${x.id}`} key={x.id} className="card match-row">
            <div className="rank">#{x.rank}</div>
            <ScoreRing score={x.score} />
            <div className="grow">
              <div className="row wrap"><b>{x.name}</b>{x.is_demo && <Badge tone="demo">Synthetic demo</Badge>}
                <Badge tone={x.blocked ? "bad" : x.score >= 65 ? "good" : "neutral"}>{x.label}</Badge></div>
              <div className="muted small">{x.year} year · {x.hostel} · confidence {Math.round(x.confidence * 100)}%</div>
              {x.top_strengths.map((s) => <div className="small good-t" key={s}>✓ {s.split(":")[0]}</div>)}
              {x.top_mismatches.map((s) => <div className="small warn" key={s}>! {s.split(":")[0]}</div>)}
              {x.blocked && <div className="small bad-t">⛔ {x.dealbreaker_count} dealbreaker conflict(s)</div>}
            </div>
            <span className="link">Why? →</span>
          </Link>))}</div>
        <p className="muted small mt">{data.disclaimer}</p>
      </>}
    </div>
  );
}
