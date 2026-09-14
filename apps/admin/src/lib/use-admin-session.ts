"use client";

import { useEffect, useState } from "react";
import { readToken, writeToken, clearToken } from "./token-store";

export function useAdminSession() {
  const [token, setToken] = useState("");

  useEffect(() => {
    setToken(readToken());
  }, []);

  function updateToken(next: string) {
    setToken(next);
    if (next) {
      writeToken(next);
      return;
    }
    clearToken();
  }

  return { token, updateToken };
}
