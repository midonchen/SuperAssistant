"use client";

import { useState } from "react";
import { loginBySms } from "../lib/api";

type Props = {
  token: string;
  onTokenChange: (token: string) => void;
  onError: (message: string) => void;
};

export function AdminAuthPanel({ token, onTokenChange, onError }: Props) {
  const [phone, setPhone] = useState("13800138000");
  const [code, setCode] = useState("123456");
  const [deviceId, setDeviceId] = useState("web-admin-device-001");
  const [pending, setPending] = useState(false);

  async function handleLogin() {
    setPending(true);
    onError("");
    try {
      const data = await loginBySms(phone, code, deviceId);
      onTokenChange(data.access_token);
    } catch (error) {
      onError(error instanceof Error ? error.message : "login failed");
    } finally {
      setPending(false);
    }
  }

  return (
    <section className="card auth-panel">
      <h3>Admin Session</h3>
      <div className="auth-grid">
        <label>
          Phone
          <input value={phone} onChange={(event) => setPhone(event.target.value)} placeholder="13800138000" />
        </label>
        <label>
          Code
          <input value={code} onChange={(event) => setCode(event.target.value)} placeholder="123456" />
        </label>
        <label>
          Device ID
          <input value={deviceId} onChange={(event) => setDeviceId(event.target.value)} placeholder="web-admin-device" />
        </label>
      </div>
      <div className="auth-actions">
        <button onClick={handleLogin} disabled={pending}>{pending ? "Logging in..." : "Login by SMS"}</button>
        <button
          onClick={() => onTokenChange("")}
          disabled={!token}
          className="secondary"
        >
          Clear Token
        </button>
      </div>
      <p className="token-preview">{token ? `Token loaded (${token.slice(0, 20)}...)` : "No token"}</p>
    </section>
  );
}
