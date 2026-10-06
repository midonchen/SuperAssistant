"use client";

import { useEffect, useState } from "react";
import { AdminAuthPanel } from "../../components/admin-auth-panel";
import { AdminNav } from "../../components/admin-nav";
import { getRelationshipsOverview } from "../../lib/api";
import { useAdminSession } from "../../lib/use-admin-session";
import type { RelationshipsOverview } from "../../types/admin";

export default function RelationshipsPage() {
  const { token, updateToken } = useAdminSession();
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<RelationshipsOverview | null>(null);

  async function load() {
    if (!token) {
      setData(null);
      return;
    }
    setLoading(true);
    setError("");
    try {
      setData(await getRelationshipsOverview(token));
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
      <h1>Relationships</h1>
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
                  <h4>Contacts</h4>
                  <p>{data.totals.contacts}</p>
                </div>
              </div>
              <div className="card">
                <div className="metric">
                  <h4>Occasions</h4>
                  <p>{data.totals.occasions}</p>
                </div>
              </div>
              <div className="card">
                <div className="metric">
                  <h4>Gift Suggestions</h4>
                  <p>{data.totals.gift_suggestions}</p>
                </div>
              </div>
            </div>
            <h3>Recent Contacts</h3>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Relationship</th>
                    <th>Birthday</th>
                  </tr>
                </thead>
                <tbody>
                  {data.recent_contacts.map((c) => (
                    <tr key={c.contact_id}>
                      <td>{c.name}</td>
                      <td>{c.relationship ?? "-"}</td>
                      <td>{c.birthday ?? "-"}</td>
                    </tr>
                  ))}
                  {data.recent_contacts.length === 0 ? (
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
