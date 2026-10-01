"use client";

import { useEffect, useState } from "react";
import { AdminAuthPanel } from "../../components/admin-auth-panel";
import { AdminNav } from "../../components/admin-nav";
import { getWorkOverview } from "../../lib/api";
import { useAdminSession } from "../../lib/use-admin-session";
import type { WorkOverview } from "../../types/admin";

export default function WorkPage() {
  const { token, updateToken } = useAdminSession();
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<WorkOverview | null>(null);

  async function load() {
    if (!token) {
      setData(null);
      return;
    }
    setLoading(true);
    setError("");
    try {
      setData(await getWorkOverview(token));
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
      <h1>Work &amp; Schedule</h1>
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
          <>
            <div className="grid">
              <div className="card">
                <div className="metric">
                  <h4>Tasks</h4>
                  <p>{data.totals.tasks}</p>
                </div>
              </div>
              <div className="card">
                <div className="metric">
                  <h4>Meetings</h4>
                  <p>{data.totals.meetings}</p>
                </div>
              </div>
              <div className="card">
                <div className="metric">
                  <h4>Weekly Reports</h4>
                  <p>{data.totals.weekly_reports}</p>
                </div>
              </div>
            </div>
            <h3>Recent Tasks</h3>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Title</th>
                    <th>Priority</th>
                    <th>Status</th>
                    <th>Due</th>
                  </tr>
                </thead>
                <tbody>
                  {data.recent_tasks.map((t) => (
                    <tr key={t.task_id}>
                      <td>{t.title}</td>
                      <td>P{t.priority}</td>
                      <td>{t.status}</td>
                      <td>{t.due_at ?? "-"}</td>
                    </tr>
                  ))}
                  {data.recent_tasks.length === 0 ? (
                    <tr>
                      <td colSpan={4}>No data</td>
                    </tr>
                  ) : null}
                </tbody>
              </table>
            </div>
            <h3>Recent Meetings</h3>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Title</th>
                    <th>Summary</th>
                    <th>Started</th>
                  </tr>
                </thead>
                <tbody>
                  {data.recent_meetings.map((m) => (
                    <tr key={m.meeting_id}>
                      <td>{m.title}</td>
                      <td>{m.summary}</td>
                      <td>{m.started_at ?? "-"}</td>
                    </tr>
                  ))}
                  {data.recent_meetings.length === 0 ? (
                    <tr>
                      <td colSpan={3}>No data</td>
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
