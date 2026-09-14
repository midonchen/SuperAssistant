import Link from "next/link";

export default function Home() {
  return (
    <main className="page">
      <h1>SuperAssistant Admin</h1>
      <div className="nav">
        <Link href="/dashboard">Dashboard</Link>
        <Link href="/users">Users</Link>
        <Link href="/approvals">Approvals</Link>
        <Link href="/audit">Audit</Link>
        <Link href="/security">Security</Link>
      </div>
      <p>Core admin pages are scaffolded for MVP: Dashboard / Users / Approvals / Audit / Security.</p>
    </main>
  );
}
