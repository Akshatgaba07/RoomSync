import { useMemo, useState } from "react";
import { Alert } from "./Bits.jsx";

const SECTION_ORDER = ["About you", "Sleep & climate", "Cleanliness", "Study & noise", "Social life", "Food", "Living together", "Extras"];

export function PrefEditor({ spec, dealbreakers, priorities, setDealbreakers, setPriorities }) {
  const toggle = (list, set, v, max) => {
    if (list.includes(v)) set(list.filter((x) => x !== v));
    else if (!max || list.length < max) set([...list, v]);
  };
  return (
    <div className="stack">
      <fieldset className="field">
        <legend>Hard dealbreakers <span className="muted">— you would NOT want a roommate who…</span></legend>
        <div className="chips">
          <button type="button" className={"chip " + (dealbreakers.length === 0 ? "on" : "")} onClick={() => setDealbreakers([])}>None of these</button>
          {spec.dealbreakers.map((d) => (
            <button type="button" key={d} className={"chip danger " + (dealbreakers.includes(d) ? "on" : "")}
              aria-pressed={dealbreakers.includes(d)} onClick={() => toggle(dealbreakers, setDealbreakers, d)}>{d}</button>
          ))}
        </div>
        <p className="hint">Dealbreakers are hard filters: students who trigger one are excluded from your recommendations.</p>
      </fieldset>
      <fieldset className="field">
        <legend>What matters most? <span className="muted">— pick up to {spec.max_priorities} ({priorities.length}/{spec.max_priorities})</span></legend>
        <div className="chips">
          {spec.priorities.map((p) => {
            const on = priorities.includes(p);
            return <button type="button" key={p} className={"chip " + (on ? "on" : "")} aria-pressed={on}
              disabled={!on && priorities.length >= spec.max_priorities} onClick={() => toggle(priorities, setPriorities, p, spec.max_priorities)}>{p}</button>;
          })}
        </div>
        <p className="hint">Your top priorities get extra weight when we score compatibility.</p>
      </fieldset>
    </div>
  );
}

function Question({ q, value, onChange }) {
  return (
    <fieldset className="field">
      <legend>{q.label}{q.optional && <span className="muted"> (optional)</span>}</legend>
      {q.type === "scale" ? (
        <div>
          <div className="scale" role="radiogroup" aria-label={q.label}>
            {Array.from({ length: q.max - q.min + 1 }, (_, i) => q.min + i).map((n) => (
              <button type="button" key={n} role="radio" aria-checked={value === n} className={"scale-btn " + (value === n ? "on" : "")} onClick={() => onChange(n)}>{n}</button>
            ))}
          </div>
          {q.scale_hint && <div className="scale-hint"><span>{q.scale_hint[0]}</span><span>{q.scale_hint[1]}</span></div>}
        </div>
      ) : (
        <div className="options" role="radiogroup" aria-label={q.label}>
          {q.options.map((o) => (
            <button type="button" key={o} role="radio" aria-checked={value === o} className={"option " + (value === o ? "on" : "")} onClick={() => onChange(o)}>{o}</button>
          ))}
        </div>
      )}
    </fieldset>
  );
}

/** Multi-step questionnaire. onSave(payload) is called on every step (drafts persist) and at the end. */
export default function Questionnaire({ spec, initial, onSave, onDone, finishLabel = "Save & find roommates" }) {
  const [answers, setAnswers] = useState(initial.answers || {});
  const [dealbreakers, setDealbreakers] = useState(initial.dealbreakers || []);
  const [priorities, setPriorities] = useState(initial.priorities || []);
  const [step, setStep] = useState(0);
  const [err, setErr] = useState("");
  const [saving, setSaving] = useState(false);

  const steps = useMemo(() => {
    const by = {};
    spec.questions.forEach((q) => (by[q.section] ||= []).push(q));
    return [...SECTION_ORDER.filter((s) => by[s]).map((s) => ({ title: s, questions: by[s] })), { title: "Preferences", prefs: true }];
  }, [spec]);
  const cur = steps[step];
  const missing = cur.prefs ? (priorities.length === 0 ? ["priorities"] : []) : cur.questions.filter((q) => !q.optional && answers[q.key] == null);
  const payload = () => ({ answers, dealbreakers, priorities });

  const next = async () => {
    if (missing.length) { setErr(cur.prefs ? "Pick at least one priority." : "Please answer every question in this step."); return; }
    setErr(""); setSaving(true);
    try {
      await onSave(payload());
      if (step === steps.length - 1) onDone?.(); else { setStep(step + 1); window.scrollTo({ top: 0, behavior: "smooth" }); }
    } catch (e) { setErr(e.message); } finally { setSaving(false); }
  };

  return (
    <div className="card q-card">
      <div className="progress" aria-label={`Step ${step + 1} of ${steps.length}`}><div style={{ width: `${((step + 1) / steps.length) * 100}%` }} /></div>
      <div className="q-head"><span className="eyebrow">Step {step + 1} of {steps.length}</span><h2>{cur.title}</h2></div>
      {cur.prefs ? <PrefEditor spec={spec} {...{ dealbreakers, priorities, setDealbreakers, setPriorities }} />
        : <div className="stack">{cur.questions.map((q) => <Question key={q.key} q={q} value={answers[q.key]} onChange={(v) => setAnswers({ ...answers, [q.key]: v })} />)}</div>}
      {err && <Alert tone="error">{err}</Alert>}
      <div className="q-actions">
        <button className="btn ghost" disabled={step === 0 || saving} onClick={() => setStep(step - 1)}>Back</button>
        <button className="btn primary" disabled={saving} onClick={next}>{saving ? "Saving…" : step === steps.length - 1 ? finishLabel : "Continue"}</button>
      </div>
    </div>
  );
}
