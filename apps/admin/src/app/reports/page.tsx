"use client";

import { useEffect, useState } from "react";
import { AdminAuthPanel } from "../../components/admin-auth-panel";
import { AdminNav } from "../../components/admin-nav";
import { getReportOverview } from "../../lib/api";
import { useAdminSession } from "../../lib/use-admin-session";
import type { ReportOverviewRow } from "../../types/admin";

export default function ReportsPage() {
  const { token, updateToken } = useAdminSession();
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [rows, setRows] = useState<ReportOverviewRow[]>([]);
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
      const data = await getReportOverview(token);
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
      <h1>Reports</h1>
      <AdminNav />
      <AdminAuthPanel token={token} onTokenChange={updateToken} onError={setError} />
      <section className="card">
        <div className="row-between">
          <h3>Household Consumption Overview</h3>
          <button onClick={() => void load()} disabled={!token || loading}>
            {loading ? "Refreshing..." : "Refresh"}
          </button>
        </div>
        {error ? <p className="error">{error}</p> : null}
        <p>Total: {total}</p>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Household</th>
                <th>Members</th>
                <th>Reports</th>
                <th>Latest Month</th>
                <th>Total Consumed</th>
                <th>Total Wasted</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.household_id}>
                  <td>{row.name}</td>
                  <td>{row.member_count}</td>
                  <td>{row.report_count}</td>
                  <td>{row.latest_month ?? "-"}</td>
                  <td>{row.total_consumed_qty}</td>
                  <td>{row.total_wasted_qty}</td>
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
