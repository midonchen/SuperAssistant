"use client";

import { useEffect, useState } from "react";
import { AdminAuthPanel } from "../../components/admin-auth-panel";
import { AdminNav } from "../../components/admin-nav";
import { getSecurityEvents } from "../../lib/api";
import { useAdminSession } from "../../lib/use-admin-session";
import type { SecurityEventRow } from "../../types/admin";

function normalizeLimit(input: string): number {
  const value = Number(input);
  if (!Number.isFinite(value)) {
    return 50;
  }
  return Math.max(1, Math.min(200, Math.trunc(value)));
}

export default function SecurityPage() {
  const { token, updateToken } = useAdminSession();
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [rows, setRows] = useState<SecurityEventRow[]>([]);
  const [total, setTotal] = useState(0);
  const [userId, setUserId] = useState("");
  const [eventType, setEventType] = useState("");
  const [limitInput, setLimitInput] = useState("50");

  async function load() {
    if (!token) {
      setRows([]);
      setTotal(0);
      return;
    }
    setLoading(true);
    setError("");
    try {
      const limit = normalizeLimit(limitInput);
      const data = await getSecurityEvents(token, userId || undefined, eventType || undefined, limit);
      setRows(data.list);
      setTotal(data.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : "load failed");
      setRows([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, [token]);

  return (
    <main className="page">
      <h1>Security Events</h1>
      <AdminNav />
      <AdminAuthPanel token={token} onTokenChange={updateToken} onError={setError} />
      <section className="card">
        <div className="row-between">
          <h3>Security Audit Log</h3>
          <button onClick={() => void load()} disabled={!token || loading}>{loading ? "Refreshing..." : "Query"}</button>
        </div>
        <div className="form-row">
          <label>
            User ID
            <input value={userId} onChange={(event) => setUserId(event.target.value)} placeholder="UUID" />
          </label>
          <label>
            Event Type
            <input value={eventType} onChange={(event) => setEventType(event.target.value)} placeholder="ADMIN_AUDIT_REVIEW" />
          </label>
          <label>
            Limit
            <input value={limitInput} onChange={(event) => setLimitInput(event.target.value)} placeholder="50" />
          </label>
        </div>
        {error ? <p className="error">{error}</p> : null}
        <p>Total: {total}</p>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>User ID</th>
                <th>Event Type</th>
                <th>Details</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.event_id}>
                  <td>{row.event_id}</td>
                  <td>{row.user_id}</td>
                  <td>{row.event_type}</td>
                  <td><code>{JSON.stringify(row.details)}</code></td>
                  <td>{new Date(row.created_at).toLocaleString()}</td>
                </tr>
              ))}
              {rows.length === 0 ? (
                <tr>
                  <td colSpan={5}>No events</td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}
