import { MetricCard } from "../../components/MetricCard";

export default function DashboardPage() {
  return (
    <main className="page">
      <h1 style={{ marginTop: 0 }}>Dashboard</h1>
      <div className="grid">
        <MetricCard title="Organization" value="Multi-tenant ready" subtitle="Invite teammates and manage roles" />
        <MetricCard title="Files" value="Presigned uploads" subtitle="S3-compatible upload flow" />
        <MetricCard title="Realtime" value="Live notifications" subtitle="WebSocket channel available at /ws" />
      </div>
    </main>
  );
}
