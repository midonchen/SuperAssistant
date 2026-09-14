const TOKEN_KEY = "sa_admin_access_token";

export function readToken(): string {
  if (typeof window === "undefined") {
    return "";
  }
  return window.localStorage.getItem(TOKEN_KEY) ?? "";
}

export function writeToken(token: string): void {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.removeItem(TOKEN_KEY);
}
