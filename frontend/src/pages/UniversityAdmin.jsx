import { useState } from "react";

function downloadCsv(filename, rows) {
  if (!rows.length) return;
  const keys = Object.keys(rows[0]);
  const quote = (value) => `"${String(value ?? "").replaceAll('"', '""')}"`;
  const csv = [keys.map(quote).join(","), ...rows.map((row) => keys.map((key) => quote(row[key])).join(","))].join("\r\n");
  const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
  const a = document.createElement("a");
  a.href = url; a.download = filename; a.click();
  URL.revokeObjectURL(url);
}

export default function UniversityAdmin() {
  const [adminKey, setAdminKey] = useState("");
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);

  async function runMatching(e) {
    e.preventDefault();
    setError(""); setResult(null);
    if (!file) { setError("Please choose a CSV file."); return; }
    if (!adminKey.trim()) { setError("Enter the university admin key configured by the backend administrator."); return; }
    setBusy(true);
    try {
      const csv_text = await file.text();
      const response = await fetch("/api/university/matches", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-University-Admin-Key": adminKey.trim() },
        body: JSON.stringify({ csv_text, mode: "both" }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        const detail = data.detail;
        if (detail && typeof detail === "object") {
          const lines = detail.errors || [];
          throw new Error([detail.message, ...lines].filter(Boolean).join("\n"));
        }
        throw new Error(typeof detail === "string" ? detail : "Could not process this CSV.");
      }
      setResult(data);
    } catch (err) {
      setError(err.message || "Upload failed. Check the backend connection.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="container section narrow">
      <div className="page-head">
        <span className="eyebrow">RoomSync Campus Match</span>
        <h1 className="h2">University CSV matching</h1>
        <p className="muted">Upload a university questionnaire export to generate individual top-2 suggestions and exclusive roommate pairs.</p>
      </div>

      <form className="card stack" onSubmit={runMatching}>
        <label>University admin key
          <input type="password" value={adminKey} onChange={(e) => setAdminKey(e.target.value)} placeholder="Enter admin key" autoComplete="off" />
        </label>
        <label>Student questionnaire CSV
          <input type="file" accept=".csv,text/csv" onChange={(e) => { setFile(e.target.files?.[0] || null); setResult(null); }} />
        </label>
        <p className="hint">Use the same Google Forms column headings as the RoomSync questionnaire. Required questions and priorities must be answered for every student. Maximum 500 rows; file is processed in memory and is not saved by the server.</p>
        <button className="btn primary" disabled={busy || !file}>{busy ? "Calculating matches…" : "Generate both matching reports"}</button>
        {error && <div className="alert error" style={{ whiteSpace: "pre-wrap" }}>{error}</div>}
      </form>

      {result && (
        <div className="stack mt">
          <div className="grid3">
            <div className="card stat"><div className="muted small">Students processed</div><div className="stat-n">{result.students_processed}</div></div>
            <div className="card stat"><div className="muted small">Exclusive pairs</div><div className="stat-n">{result.exclusive_pairs.length}</div></div>
            <div className="card stat"><div className="muted small">Unmatched</div><div className="stat-n">{result.unmatched_students.length}</div></div>
          </div>

          <section className="card stack">
            <div className="row between wrap"><h2 className="h3">Individual top 2 matches</h2>
              <button className="btn ghost sm" onClick={() => downloadCsv("roomsync-individual-top2.csv", result.individual_top2.flatMap((s) => s.matches.map((m, i) => ({ student_id: s.student_id, student_name: s.student_name, match_rank: i + 1, match_id: m.student_id, match_name: m.student_name, compatibility_score: m.score, compatibility_label: m.label }))))}>Download CSV</button>
            </div>
            <div className="table-wrap"><table><thead><tr><th>Student</th><th>Match 1</th><th>Score</th><th>Match 2</th><th>Score</th></tr></thead>
              <tbody>{result.individual_top2.map((s) => <tr key={s.student_id}><td>{s.student_name}<div className="muted small">{s.student_id}</div></td>
                <td>{s.matches[0]?.student_name || "—"}</td><td>{s.matches[0] ? `${s.matches[0].score}%` : "—"}</td>
                <td>{s.matches[1]?.student_name || "—"}</td><td>{s.matches[1] ? `${s.matches[1].score}%` : "—"}</td></tr>)}</tbody></table></div>
          </section>

          <section className="card stack">
            <div className="row between wrap"><h2 className="h3">Exclusive roommate allocation</h2>
              <button className="btn ghost sm" onClick={() => downloadCsv("roomsync-exclusive-pairs.csv", result.exclusive_pairs)}>Download CSV</button>
            </div>
            <div className="table-wrap"><table><thead><tr><th>Pair</th><th>Student 1</th><th>Student 2</th><th>Compatibility</th></tr></thead>
              <tbody>{result.exclusive_pairs.map((p) => <tr key={p.pair_number}><td>{p.pair_number}</td><td>{p.student_1_name}<div className="muted small">{p.student_1_id}</div></td><td>{p.student_2_name}<div className="muted small">{p.student_2_id}</div></td><td><b>{p.score}%</b><div className="muted small">{p.label}</div></td></tr>)}</tbody></table></div>
            <p className="hint">{result.allocation_method}</p>
          </section>

          <section className="card stack">
            <div className="row between wrap"><h2 className="h3">Unmatched students</h2>
              <button className="btn ghost sm" onClick={() => downloadCsv("roomsync-unmatched-students.csv", result.unmatched_students)}>Download CSV</button>
            </div>
            {result.unmatched_students.length ? <ul>{result.unmatched_students.map((s) => <li key={s.student_id}>{s.student_name} <span className="muted small">({s.student_id})</span></li>)}</ul> : <p className="muted">Every student was allocated to a pair.</p>}
          </section>
          <p className="muted small">{result.disclaimer}</p>
        </div>
      )}
    </div>
  );
}
