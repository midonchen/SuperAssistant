"use client";

import { useEffect, useState } from "react";
import { AdminAuthPanel } from "../../components/admin-auth-panel";
import { AdminNav } from "../../components/admin-nav";
import { getAnalytics } from "../../lib/api";
import { useAdminSession } from "../../lib/use-admin-session";
import type { AnalyticsSnapshot } from "../../types/admin";

export default function AnalyticsPage() {
  const { token, updateToken } = useAdminSession();
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<AnalyticsSnapshot | null>(null);

  async function load() {
    if (!token) {
      setData(null);
      return;
    }
    setLoading(true);
    setError("");
    try {
      setData(await getAnalytics(token));
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
      <h1>Analytics</h1>
      <AdminNav />
      <AdminAuthPanel token={token} onTokenChange={updateToken} onError={setError} />
      <section className="card">
        <div className="row-between">
          <h3>Event Summary</h3>
          <button onClick={() => void load()} disabled={!token || loading}>
            {loading ? "Refreshing..." : "Refresh"}
          </button>
        </div>
        {error ? <p className="error">{error}</p> : null}
        {data ? (
          <>
            <div className="grid">
              {Object.entries(data.summary).map(([type, count]) => (
                <div key={type} className="card">
                  <div className="metric">
                    <h4>{type}</h4>
                    <p>{count}</p>
                  </div>
                </div>
              ))}
              {Object.keys(data.summary).length === 0 ? <p>No events yet</p> : null}
            </div>
            <p>Recent events: {data.total}</p>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Event</th>
                    <th>User</th>
                    <th>Household</th>
                    <th>Payload</th>
                    <th>Time</th>
                  </tr>
                </thead>
                <tbody>
                  {data.list.map((row) => (
                    <tr key={row.event_id}>
                      <td>{row.event_id}</td>
                      <td>{row.event_type}</td>
                      <td>{row.user_id ?? "-"}</td>
                      <td>{row.household_id ?? "-"}</td>
                      <td>{JSON.stringify(row.payload)}</td>
                      <td>{row.created_at}</td>
                    </tr>
                  ))}
                  {data.list.length === 0 ? (
                    <tr>
                      <td colSpan={6}>No data</td>
                    </tr>
                  ) : null}
                </tbody>
              </table>
            </div>
          </>
        ) : null}
      </section>
    </main>
  );
}
