export function ScoreRing({ score, size = 76, label }) {
  const r = size / 2 - 6, c = 2 * Math.PI * r, pct = Math.max(0, Math.min(100, score)) / 100;
  const color = score >= 75 ? "#0d9488" : score >= 55 ? "#4f46e5" : score >= 40 ? "#d97706" : "#dc2626";
  return (
    <div className="ring" style={{ width: size, height: size }} role="img" aria-label={`Compatibility ${Math.round(score)} out of 100`}>
      <svg width={size} height={size}>
        <circle cx={size / 2} cy={size / 2} r={r} stroke="#e6e9f2" strokeWidth="6" fill="none" />
        <circle cx={size / 2} cy={size / 2} r={r} stroke={color} strokeWidth="6" fill="none" strokeLinecap="round"
          strokeDasharray={`${c * pct} ${c}`} transform={`rotate(-90 ${size / 2} ${size / 2})`} />
      </svg>
      <div className="ring-num" style={{ fontSize: size * 0.3 }}>{Math.round(score)}{label && <small>{label}</small>}</div>
    </div>
  );
}

export const Badge = ({ children, tone = "neutral" }) => <span className={`badge ${tone}`}>{children}</span>;
export const Alert = ({ tone = "info", children }) => <div className={`alert ${tone}`} role={tone === "error" ? "alert" : "status"}>{children}</div>;
export const Spinner = ({ text = "Loading…" }) => <div className="center muted">{text}</div>;
