export default function StatsBar({ incidents }) {
  if (incidents.length === 0) return null;

  const latencies = incidents.map((i) => i.latency_ms).filter(Boolean).sort((a, b) => a - b);
  const p50 = latencies[Math.floor(latencies.length * 0.5)] ?? 0;
  const p95 = latencies[Math.floor(latencies.length * 0.95)] ?? 0;
  const highDisagreement = incidents.filter((i) => i.resolution?.high_disagreement).length;
  const highConf = incidents.filter((i) => i.resolution?.final_diagnosis?.confidence === "high").length;

  const stats = [
    { label: "Total Incidents", value: incidents.length, icon: "📋" },
    { label: "p50 Latency", value: `${p50}ms`, icon: "⚡" },
    { label: "p95 Latency", value: `${p95}ms`, icon: "📈" },
    { label: "High Confidence", value: `${highConf}`, icon: "✓" },
    { label: "Disagreements", value: `${highDisagreement}`, icon: "⚠" },
  ];

  return (
    <div style={{
      display: "grid",
      gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))",
      gap: 12, marginBottom: 4,
    }}>
      {stats.map((s) => (
        <div key={s.label} className="card" style={{ padding: "16px 18px" }}>
          <div style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 6, fontWeight: 500 }}>
            {s.icon} {s.label}
          </div>
          <div style={{ fontSize: 24, fontWeight: 700, color: "var(--text-primary)", letterSpacing: "-0.02em" }}>
            {s.value}
          </div>
        </div>
      ))}
    </div>
  );
}