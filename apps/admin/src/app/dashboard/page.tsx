"use client";

import { useEffect, useState } from "react";
import { AdminAuthPanel } from "../../components/admin-auth-panel";
import { AdminNav } from "../../components/admin-nav";
import { getDashboardSummary } from "../../lib/api";
import { useAdminSession } from "../../lib/use-admin-session";
import type { DashboardSummary } from "../../types/admin";

export default function DashboardPage() {
  const { token, updateToken } = useAdminSession();
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [summary, setSummary] = useState<DashboardSummary | null>(null);

  async function load() {
    if (!token) {
      setSummary(null);
      return;
    }
    setLoading(true);
    setError("");
    try {
      const data = await getDashboardSummary(token);
      setSummary(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "load failed");
      setSummary(null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, [token]);

  return (
    <main className="page">
      <h1>Dashboard</h1>
      <AdminNav />
      <AdminAuthPanel token={token} onTokenChange={updateToken} onError={setError} />
      <section className="card">
        <div className="row-between">
          <h3>KPI</h3>
          <button onClick={() => void load()} disabled={!token || loading}>{loading ? "Refreshing..." : "Refresh"}</button>
        </div>
        {error ? <p className="error">{error}</p> : null}
        {!token ? <p>Please login first.</p> : null}
        {summary ? (
          <div className="grid">
            <section className="card metric"><h4>Total Users</h4><p>{summary.kpi.total_users}</p></section>
            <section className="card metric"><h4>Total Audit Tasks</h4><p>{summary.kpi.total_audit_tasks}</p></section>
            <section className="card metric"><h4>Pending Audit Tasks</h4><p>{summary.kpi.pending_audit_tasks}</p></section>
            <section className="card metric"><h4>Push Sent</h4><p>{summary.kpi.push_sent ?? 0}</p></section>
            <section className="card metric"><h4>Push Failed</h4><p>{summary.kpi.push_failed ?? 0}</p></section>
          </div>
        ) : null}
      </section>
      <section className="card">
        <h3>Alerts</h3>
        <ul>
          {(summary?.alerts ?? []).map((alert, index) => (
            <li key={`${alert.level}-${index}`}>{alert.level}: {alert.message}</li>
          ))}
        </ul>
      </section>
      {summary?.ai_runtime ? (
        <section className="card">
          <h3>AI Runtime</h3>
          <pre>{JSON.stringify(summary.ai_runtime, null, 2)}</pre>
        </section>
      ) : null}
    </main>
  );
}
