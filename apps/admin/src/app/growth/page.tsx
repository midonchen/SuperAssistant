"use client";

import { useEffect, useState } from "react";
import { AdminAuthPanel } from "../../components/admin-auth-panel";
import { AdminNav } from "../../components/admin-nav";
import { getGrowthOverview } from "../../lib/api";
import { useAdminSession } from "../../lib/use-admin-session";
import type { GrowthOverview } from "../../types/admin";

const METRICS: Array<{ key: keyof GrowthOverview["totals"]; label: string }> = [
  { key: "thinking_models", label: "Thinking Models" },
  { key: "value_principles", label: "Value Principles" },
  { key: "journal_entries", label: "Journal Entries" },
  { key: "life_goals", label: "Life Goals" },
  { key: "habits", label: "Habits" },
  { key: "workouts", label: "Workouts" },
  { key: "assets", label: "Assets" },
  { key: "investments", label: "Investments" },
];

export default function GrowthPage() {
  const { token, updateToken } = useAdminSession();
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<GrowthOverview | null>(null);

  async function load() {
    if (!token) {
      setData(null);
      return;
    }
    setLoading(true);
    setError("");
    try {
      setData(await getGrowthOverview(token));
    } catch (err) {
      setError(err instanceof Error ? err.message : "load failed");
      setData(null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, [token]);

  return (
    <main className="page">
      <h1>Growth</h1>
      <AdminNav />
      <AdminAuthPanel token={token} onTokenChange={updateToken} onError={setError} />
      <section className="card">
        <div className="row-between">
          <h3>Overview</h3>
          <button onClick={() => void load()} disabled={!token || loading}>
            {loading ? "Refreshing..." : "Refresh"}
          </button>
        </div>
        {error ? <p className="error">{error}</p> : null}
        {data ? (
          <div className="grid">
            {METRICS.map((m) => (
              <div className="card" key={m.key}>
                <div className="metric">
                  <h4>{m.label}</h4>
                  <p>{data.totals[m.key]}</p>
                </div>
              </div>
            ))}
          </div>
        ) : null}
      </section>
    </main>
  );
}
