import type { Metadata } from "next";
import { headers } from "next/headers";
import "./styles.css";

export const metadata: Metadata = {
  title: "SuperAssistant Admin",
  description: "Dashboard / Users / Approvals / Audit / Security",
};

export const dynamic = "force-dynamic";

function basicAuthDenied(): boolean {
  const password = process.env.ADMIN_PASSWORD;
  if (!password) {
    return false; // no password configured → open (local dev)
  }
  const header = headers().get("authorization") ?? "";
  const expected = "Basic " + Buffer.from(`admin:${password}`).toString("base64");
  return header !== expected;
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  if (basicAuthDenied()) {
    return new Response("Unauthorized", {
      status: 401,
      headers: {
        "WWW-Authenticate": 'Basic realm="SuperAssistant Admin"',
        "Content-Type": "text/plain",
      },
    });
  }
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
