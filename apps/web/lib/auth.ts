// Tiny, dependency-free session layer: an HMAC-signed cookie (Web Crypto, so it runs in
// both the Edge middleware and Node route handlers). Real Google/GitHub OAuth is wired in
// app/api/auth/[...slug]/route.ts; a one-tap demo session keeps the deployment reviewable
// even when no OAuth credentials are configured.

export const SESSION_COOKIE = "kairos_session";

const SECRET = process.env.AUTH_SECRET || "kairos-dev-secret-change-me-in-prod";

export interface SessionUser {
  name: string;
  email?: string;
  avatar?: string;
  provider: "google" | "github" | "demo";
}

// Which OAuth providers are usable (creds present in the environment).
export const providers = {
  google: Boolean(process.env.GOOGLE_CLIENT_ID && process.env.GOOGLE_CLIENT_SECRET),
  github: Boolean(process.env.GITHUB_CLIENT_ID && process.env.GITHUB_CLIENT_SECRET),
};

function b64urlEncode(bytes: Uint8Array): string {
  let s = "";
  for (const b of bytes) s += String.fromCharCode(b);
  return btoa(s).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function b64urlToBytes(str: string): Uint8Array {
  let s = str.replace(/-/g, "+").replace(/_/g, "/");
  while (s.length % 4) s += "=";
  const bin = atob(s);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

async function hmac(data: string): Promise<string> {
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(SECRET),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const sig = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(data));
  return b64urlEncode(new Uint8Array(sig));
}

export async function encodeSession(user: SessionUser): Promise<string> {
  const payload = b64urlEncode(new TextEncoder().encode(JSON.stringify(user)));
  return `${payload}.${await hmac(payload)}`;
}

export async function decodeSession(token?: string | null): Promise<SessionUser | null> {
  if (!token || !token.includes(".")) return null;
  const [payload, sig] = token.split(".");
  if (!payload || !sig) return null;
  if ((await hmac(payload)) !== sig) return null;
  try {
    return JSON.parse(new TextDecoder().decode(b64urlToBytes(payload))) as SessionUser;
  } catch {
    return null;
  }
}
