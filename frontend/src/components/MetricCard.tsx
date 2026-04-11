export function MetricCard({ title, value, subtitle }: { title: string; value: string; subtitle: string }) {
  return (
    <div className="card">
      <p style={{ margin: 0, opacity: 0.7 }}>{title}</p>
      <h3 style={{ marginBottom: 8 }}>{value}</h3>
      <p style={{ margin: 0, opacity: 0.75 }}>{subtitle}</p>
    </div>
  );
}
