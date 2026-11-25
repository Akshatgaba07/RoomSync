import { Link } from "react-router-dom";
import { useAuth } from "../auth.jsx";

const DIMS = ["Sleep schedule", "Noise & study", "Cleanliness", "Food habits", "Night-time AC / fan", "Gaming & audio",
  "Guests & visitors", "Weekend lifestyle", "Privacy & space", "Sharing habits", "Conflict style", "Desired relationship"];

export default function Landing() {
  const { user } = useAuth();
  return (
    <>
      <section className="hero"><div className="container hero-grid">
        <div>
          <span className="eyebrow">Built for Bennett University hostels</span>
          <h1>Find a roommate you can actually <em>live</em> with.</h1>
          <p className="lead">RoomSync compares your habits — sleep, noise, cleanliness, food, guests — with other students and explains exactly where you fit and where you'll clash.</p>
          <div className="row">
            <Link className="btn primary lg" to={user ? "/dashboard" : "/signup"}>{user ? "Go to dashboard" : "Create your profile"}</Link>
            {!user && <Link className="btn ghost lg" to="/login">Log in</Link>}
          </div>
          <p className="muted small">~5 minutes · dealbreakers respected · estimates, not guarantees</p>
        </div>
        <div className="card hero-card" aria-hidden="true">
          <div className="hc-top"><div><b>Aarav &amp; Rohan</b><div className="muted small">Example pair (illustration)</div></div><div className="hc-score">82</div></div>
          {[["Sleep schedule", 92, "teal"], ["Noise & study", 78, "teal"], ["Cleanliness", 64, "indigo"], ["Guests", 38, "amber"]].map(([l, v, t]) => (
            <div key={l} className="bar-row"><span>{l}</span><div className="bar"><div className={t} style={{ width: v + "%" }} /></div></div>
          ))}
          <div className="alert info small">Possible friction: different guest comfort levels.</div>
        </div>
      </div></section>

      <section className="container section">
        <h2 className="center-t">How it works</h2>
        <div className="grid3">
          {[["1", "Tell us how you live", "A short, multi-step questionnaire covering 12 lifestyle areas, your dealbreakers and your top priorities."],
            ["2", "We score every pair", "Rule-based scoring plus an unsupervised model compare you with each eligible student. Dealbreakers are hard filters, never averaged away."],
            ["3", "See the why", "Every recommendation shows strengths, mismatches and conflicts in plain language, so you can talk it through before you decide."]].map(([n, t, d]) => (
            <div className="card" key={n}><div className="step-n">{n}</div><h3>{t}</h3><p className="muted">{d}</p></div>
          ))}
        </div>
      </section>

      <section className="container section">
        <div className="card band">
          <h2>What we compare</h2>
          <div className="chips">{DIMS.map((d) => <span className="chip static" key={d}>{d}</span>)}</div>
          <p className="muted">Your top three priorities count extra. A critical clash in something you care about lowers the score even if everything else lines up.</p>
        </div>
      </section>

      <section className="container section">
        <div className="card honest">
          <h3>An honest note on the AI</h3>
          <p>There is no public dataset of real roommate outcomes, so RoomSync does not pretend to predict them. Scores come from documented compatibility rules combined with an unsupervised lifestyle model. When students report how their real roommate arrangement went, the app can learn from that data — until then, treat scores as a conversation starter.</p>
        </div>
      </section>
    </>
  );
}
