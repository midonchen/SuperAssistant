"use client";

import { useEffect, useState } from "react";
import { AdminAuthPanel } from "../../components/admin-auth-panel";
import { AdminNav } from "../../components/admin-nav";
import { getCareerOverview } from "../../lib/api";
import { useAdminSession } from "../../lib/use-admin-session";
import type { CareerOverview } from "../../types/admin";

export default function CareerPage() {
  const { token, updateToken } = useAdminSession();
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<CareerOverview | null>(null);

  async function load() {
    if (!token) {
      setData(null);
      return;
    }
    setLoading(true);
    setError("");
    try {
      setData(await getCareerOverview(token));
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
      <h1>Career</h1>
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
            <div className="card">
              <div className="metric">
                <h4>Goals</h4>
                <p>{data.totals.career_goals}</p>
              </div>
            </div>
            <div className="card">
              <div className="metric">
                <h4>Skills</h4>
                <p>{data.totals.skills}</p>
              </div>
            </div>
            <div className="card">
              <div className="metric">
                <h4>Applications</h4>
                <p>{data.totals.job_applications}</p>
              </div>
            </div>
            <div className="card">
              <div className="metric">
                <h4>Learning Items</h4>
                <p>{data.totals.learning_items}</p>
              </div>
            </div>
          </div>
        ) : null}
      </section>
    </main>
  );
}
