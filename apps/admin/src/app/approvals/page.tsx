"use client";

import { useEffect, useState } from "react";
import { AdminAuthPanel } from "../../components/admin-auth-panel";
import { AdminNav } from "../../components/admin-nav";
import { getApprovalRequests, reviewApprovalRequest } from "../../lib/api";
import { useAdminSession } from "../../lib/use-admin-session";
import type { ApprovalRequest } from "../../types/admin";

export default function ApprovalsPage() {
  const { token, updateToken } = useAdminSession();
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [rows, setRows] = useState<ApprovalRequest[]>([]);

  async function load() {
    if (!token) {
      setRows([]);
      return;
    }
    setLoading(true);
    setError("");
    try {
      const data = await getApprovalRequests(token);
      setRows(data.list);
    } catch (err) {
      setError(err instanceof Error ? err.message : "load failed");
      setRows([]);
    } finally {
      setLoading(false);
    }
  }

  async function handleReview(approvalId: string, decision: "APPROVE" | "REJECT") {
    if (!token) {
      return;
    }
    setError("");
    try {
      await reviewApprovalRequest(token, approvalId, decision);
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
      <h1>Approvals</h1>
      <AdminNav />
      <AdminAuthPanel token={token} onTokenChange={updateToken} onError={setError} />
      <section className="card">
        <div className="row-between">
          <h3>Pending / History</h3>
          <button onClick={() => void load()} disabled={!token || loading}>{loading ? "Refreshing..." : "Refresh"}</button>
        </div>
        {error ? <p className="error">{error}</p> : null}
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Approval ID</th>
                <th>Action</th>
                <th>Status</th>
                <th>Target User</th>
                <th>Requested By</th>
                <th>Created</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.approval_id}>
                  <td>{row.approval_id}</td>
                  <td>{row.action_type}</td>
                  <td>{row.status}</td>
                  <td>{row.target_user_id}</td>
                  <td>{row.requested_by}</td>
                  <td>{new Date(row.created_at).toLocaleString()}</td>
                  <td>
                    {row.status === "PENDING" ? (
                      <div className="inline-actions">
                        <button onClick={() => void handleReview(row.approval_id, "APPROVE")}>Approve</button>
                        <button className="secondary" onClick={() => void handleReview(row.approval_id, "REJECT")}>Reject</button>
                      </div>
                    ) : (
                      "Done"
                    )}
                  </td>
                </tr>
              ))}
              {rows.length === 0 ? (
                <tr>
                  <td colSpan={7}>No approvals</td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}
