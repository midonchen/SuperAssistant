"use client";

import { useEffect, useState } from "react";
import { AdminAuthPanel } from "../../components/admin-auth-panel";
import { AdminNav } from "../../components/admin-nav";
import { getUsers, requestRevokeUserSessions } from "../../lib/api";
import { useAdminSession } from "../../lib/use-admin-session";
import type { UserRow } from "../../types/admin";

export default function UsersPage() {
  const { token, updateToken } = useAdminSession();
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [phone, setPhone] = useState("");
  const [userId, setUserId] = useState("");
  const [rows, setRows] = useState<UserRow[]>([]);
  const [total, setTotal] = useState(0);

  async function load() {
    if (!token) {
      setRows([]);
      setTotal(0);
      return;
    }
    setLoading(true);
    setError("");
    try {
      const data = await getUsers(token, phone || undefined, userId || undefined);
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

  async function handleRevoke(targetUserId: string) {
    if (!token) {
      return;
    }
    setError("");
    try {
      const result = await requestRevokeUserSessions(token, targetUserId, "high-risk operation requires review");
      await load();
      const approvalId = result.approval_request.approval_id;
      setError(`approval created: ${approvalId} (pending reviewer decision)`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "revoke failed");
    }
  }

  useEffect(() => {
    void load();
  }, [token]);

  return (
    <main className="page">
      <h1>Users</h1>
      <AdminNav />
      <AdminAuthPanel token={token} onTokenChange={updateToken} onError={setError} />
      <section className="card">
        <div className="row-between">
          <h3>Query Users</h3>
          <button onClick={() => void load()} disabled={!token || loading}>{loading ? "Refreshing..." : "Search"}</button>
        </div>
        <div className="form-row">
          <label>
            Phone
            <input value={phone} onChange={(event) => setPhone(event.target.value)} placeholder="138" />
          </label>
          <label>
            User ID
            <input value={userId} onChange={(event) => setUserId(event.target.value)} placeholder="UUID" />
          </label>
        </div>
        {error ? <p className="error">{error}</p> : null}
        <p>Total: {total}</p>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>User ID</th>
                <th>Phone</th>
                <th>Timezone</th>
                <th>Role</th>
                <th>Onboarded</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.user_id}>
                  <td>{row.user_id}</td>
                  <td>{row.phone_masked}</td>
                  <td>{row.timezone}</td>
                  <td>{row.role}</td>
                  <td>{row.onboarded ? "Yes" : "No"}</td>
                  <td>
                    <button onClick={() => void handleRevoke(row.user_id)}>Request Revoke</button>
                  </td>
                </tr>
              ))}
              {rows.length === 0 ? (
                <tr>
                  <td colSpan={6}>No data</td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}
