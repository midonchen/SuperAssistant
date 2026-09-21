"use client";

import { useEffect, useState } from "react";
import { AdminAuthPanel } from "../../components/admin-auth-panel";
import { AdminNav } from "../../components/admin-nav";
import { getHouseholds } from "../../lib/api";
import { useAdminSession } from "../../lib/use-admin-session";
import type { HouseholdRow } from "../../types/admin";

export default function HouseholdsPage() {
  const { token, updateToken } = useAdminSession();
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [rows, setRows] = useState<HouseholdRow[]>([]);
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
      const data = await getHouseholds(token);
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
      <h1>Households</h1>
      <AdminNav />
      <AdminAuthPanel token={token} onTokenChange={updateToken} onError={setError} />
      <section className="card">
        <div className="row-between">
          <h3>Household Roster</h3>
          <button onClick={() => void load()} disabled={!token || loading}>
            {loading ? "Refreshing..." : "Refresh"}
          </button>
        </div>
        {error ? <p className="error">{error}</p> : null}
        <p>Total: {total}</p>
        {rows.map((row) => (
          <details key={row.household_id} className="card" style={{ marginBottom: 12 }}>
            <summary>
              {row.name} — {row.member_count} member{row.member_count === 1 ? "" : "s"}
            </summary>
            <p style={{ color: "#666" }}>ID: {row.household_id}</p>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>User ID</th>
                    <th>Phone</th>
                    <th>Role</th>
                  </tr>
                </thead>
                <tbody>
                  {row.members.map((member) => (
                    <tr key={member.user_id}>
                      <td>{member.user_id}</td>
                      <td>{member.phone_masked}</td>
                      <td>{member.role}</td>
                    </tr>
                  ))}
                  {row.members.length === 0 ? (
                    <tr>
                      <td colSpan={3}>No members</td>
                    </tr>
                  ) : null}
                </tbody>
              </table>
            </div>
          </details>
        ))}
        {rows.length === 0 ? <p>No data</p> : null}
      </section>
    </main>
  );
}
