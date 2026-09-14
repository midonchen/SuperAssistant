"use client";

import { useEffect, useState } from "react";
import { AdminAuthPanel } from "../../components/admin-auth-panel";
import { AdminNav } from "../../components/admin-nav";
import { getAuditTasks, reviewAuditTask } from "../../lib/api";
import { useAdminSession } from "../../lib/use-admin-session";
import type { AuditTask } from "../../types/admin";

export default function AuditPage() {
  const { token, updateToken } = useAdminSession();
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [tasks, setTasks] = useState<AuditTask[]>([]);

  async function load() {
    if (!token) {
      setTasks([]);
      return;
    }
    setLoading(true);
    setError("");
    try {
      const data = await getAuditTasks(token);
      setTasks(data.list);
    } catch (err) {
      setError(err instanceof Error ? err.message : "load failed");
      setTasks([]);
    } finally {
      setLoading(false);
    }
  }

  async function handleReview(taskId: string, action: "APPROVE" | "REJECT" | "CORRECT") {
    if (!token) {
      return;
    }
    setError("");
    try {
      await reviewAuditTask(token, taskId, action);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "review failed");
    }
  }

  useEffect(() => {
    void load();
  }, [token]);

  return (
    <main className="page">
      <h1>Audit</h1>
      <AdminNav />
      <AdminAuthPanel token={token} onTokenChange={updateToken} onError={setError} />
      <section className="card">
        <div className="row-between">
          <h3>Audit Queue</h3>
          <button onClick={() => void load()} disabled={!token || loading}>{loading ? "Refreshing..." : "Refresh"}</button>
        </div>
        {error ? <p className="error">{error}</p> : null}
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Task ID</th>
                <th>Parse Session</th>
                <th>Status</th>
                <th>Entities</th>
                <th>Created</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {tasks.map((task) => (
                <tr key={task.task_id}>
                  <td>{task.task_id}</td>
                  <td>{task.parse_session_id}</td>
                  <td>{task.status}</td>
                  <td>{task.entities.length}</td>
                  <td>{new Date(task.created_at).toLocaleString()}</td>
                  <td>
                    <div className="inline-actions">
                      <button onClick={() => void handleReview(task.task_id, "APPROVE")}>Approve</button>
                      <button className="secondary" onClick={() => void handleReview(task.task_id, "REJECT")}>Reject</button>
                    </div>
                  </td>
                </tr>
              ))}
              {tasks.length === 0 ? (
                <tr>
                  <td colSpan={6}>No tasks</td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}
