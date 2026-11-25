import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth.jsx";
import { Alert, Badge, ScoreRing, Spinner } from "../components/Bits.jsx";

export default function Dashboard() {
  const { user } = useAuth();
  const [stats, setStats] = useState(null); const [m, setM] = useState(null); const [err, setErr] = useState("");
  useEffect(() => {
    Promise.all([api("/api/stats"), api("/api/matches?k=3")]).then(([s, mm]) => { setStats(s); setM(mm); }).catch((e) => setErr(e.message));
  }, [user?.updated_at]);
  if (err) return <div className="container section"><Alert tone="error">{err}</Alert></div>;
  if (!stats || !m) return <Spinner />;
  return (
    <div className="container section">
      <div className="page-head"><h1 className="h2">Hi {user.name.split(" ")[0]} 👋</h1>
        <p className="muted">Here is where your roommate search stands right now.</p></div>
      <div className="grid4">
        <Stat label="Eligible roommates" value={stats.eligible_matches ?? 0} sub={`${m.excluded_by_dealbreakers} excluded by dealbreakers`} />
        <Stat label="Best match" value={stats.best_score != null ? Math.round(stats.best_score) : "—"} sub="out of 100" />
        <Stat label="Avg of your top 5" value={stats.avg_top5 != null ? Math.round(stats.avg_top5) : "—"} sub="out of 100" />
        <Stat label="Profiles in the pool" value={stats.profiles_complete} sub={`${stats.real_signups} real sign-ups, rest demo`} />
      </div>
      <div className="row between mt"><h2 className="h3">Your top recommendations</h2><Link to="/matches" className="link">See all →</Link></div>
      {m.matches.length === 0 ? <Alert tone="info">No eligible students yet. Loosen a dealbreaker or check back as more students join.</Alert> : (
        <div className="grid3">{m.matches.map((x) => (
          <Link key={x.id} to={`/matches/${x.id}`} className="card match-mini">
            <div className="row between"><div><b>{x.name}</b><div className="muted small">{x.year} year · {x.hostel}</div></div><ScoreRing score={x.score} size={64} /></div>
            <Badge tone={x.score >= 65 ? "good" : "neutral"}>{x.label}</Badge>
            {x.top_strengths[0] && <p className="small muted">✓ {x.top_strengths[0].split(":")[0]}</p>}
            {x.top_mismatches[0] && <p className="small warn">! {x.top_mismatches[0].split(":")[0]}</p>}
          </Link>))}</div>)}
      <p className="muted small mt">{m.disclaimer}</p>
    </div>
  );
}
const Stat = ({ label, value, sub }) => <div className="card stat"><div className="muted small">{label}</div><div className="stat-n">{value}</div><div className="muted small">{sub}</div></div>;
