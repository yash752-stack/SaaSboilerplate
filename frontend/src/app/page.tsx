import Link from "next/link";
import { MetricCard } from "../components/MetricCard";

export default function HomePage() {
  return (
    <main className="page">
      <section className="card" style={{ marginBottom: 24 }}>
        <p style={{ opacity: 0.7 }}>SaaS Boilerplate</p>
        <h1 style={{ fontSize: 48, marginTop: 8 }}>Launch a production-style FastAPI SaaS faster</h1>
        <p style={{ maxWidth: 720, lineHeight: 1.6 }}>
          Auth, billing, organizations, API keys, uploads, notifications, analytics, webhooks, and realtime updates
          are already wired into the backend.
        </p>
        <div style={{ display: "flex", gap: 12, marginTop: 20 }}>
          <Link href="/login" className="card">Login</Link>
          <Link href="/register" className="card">Register</Link>
          <Link href="/dashboard" className="card">Dashboard</Link>
        </div>
      </section>

      <section className="grid">
        <MetricCard title="Security" value="JWT + 2FA + API keys" subtitle="Built for real product flows" />
        <MetricCard title="Growth" value="Billing + Usage" subtitle="Stripe-ready and analytics-friendly" />
        <MetricCard title="Scale" value="WebSockets + Queues" subtitle="Realtime and async notifications" />
      </section>
    </main>
  );
}
