import { NextResponse, type NextRequest } from "next/server";
import {
  SESSION_COOKIE,
  encodeSession,
  providers,
  type SessionUser,
} from "@/lib/auth";

// OAuth (Google / GitHub) + a one-tap demo session, with no external auth dependency.
//   GET  /api/auth/start/<provider>     → redirect to the provider's consent screen
//   GET  /api/auth/callback/<provider>  → exchange code, set session, land on the app
//   POST /api/auth/demo                 → instant demo session (always available)
//   POST /api/auth/logout               → clear the session

function baseUrl(req: NextRequest): string {
  return process.env.NEXT_PUBLIC_BASE_URL || req.nextUrl.origin;
}

function cookieOpts() {
  return {
    httpOnly: true,
    sameSite: "lax" as const,
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 60 * 60 * 24 * 7,
  };
}

async function sessionRedirect(user: SessionUser, to: string, req: NextRequest) {
  const res = NextResponse.redirect(new URL(to, baseUrl(req)));
  res.cookies.set(SESSION_COOKIE, await encodeSession(user), cookieOpts());
  return res;
}

async function googleUser(code: string, redirectUri: string): Promise<SessionUser> {
  const token = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      code,
      client_id: process.env.GOOGLE_CLIENT_ID!,
      client_secret: process.env.GOOGLE_CLIENT_SECRET!,
      redirect_uri: redirectUri,
      grant_type: "authorization_code",
    }),
  }).then((r) => r.json());
  const p = await fetch("https://www.googleapis.com/oauth2/v2/userinfo", {
    headers: { Authorization: `Bearer ${token.access_token}` },
  }).then((r) => r.json());
  return { name: p.name || p.email, email: p.email, avatar: p.picture, provider: "google" };
}

async function githubUser(code: string): Promise<SessionUser> {
  const token = await fetch("https://github.com/login/oauth/access_token", {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({
      code,
      client_id: process.env.GITHUB_CLIENT_ID!,
      client_secret: process.env.GITHUB_CLIENT_SECRET!,
    }),
  }).then((r) => r.json());
  const headers = {
    Authorization: `Bearer ${token.access_token}`,
    "User-Agent": "kairos",
    Accept: "application/vnd.github+json",
  };
  const p = await fetch("https://api.github.com/user", { headers }).then((r) => r.json());
  let email: string | undefined = p.email;
  if (!email) {
    const emails: { email: string; primary: boolean }[] = await fetch(
      "https://api.github.com/user/emails",
      { headers },
    ).then((r) => r.json());
    email = Array.isArray(emails) ? emails.find((e) => e.primary)?.email : undefined;
  }
  return { name: p.name || p.login, email, avatar: p.avatar_url, provider: "github" };
}

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ slug: string[] }> },
) {
  const { slug } = await params;
  const [action, provider] = slug;

  if (action === "start") {
    const redirectUri = `${baseUrl(req)}/api/auth/callback/${provider}`;
    if (provider === "google" && providers.google) {
      const u = new URL("https://accounts.google.com/o/oauth2/v2/auth");
      u.searchParams.set("client_id", process.env.GOOGLE_CLIENT_ID!);
      u.searchParams.set("redirect_uri", redirectUri);
      u.searchParams.set("response_type", "code");
      u.searchParams.set("scope", "openid email profile");
      u.searchParams.set("prompt", "select_account");
      return NextResponse.redirect(u);
    }
    if (provider === "github" && providers.github) {
      const u = new URL("https://github.com/login/oauth/authorize");
      u.searchParams.set("client_id", process.env.GITHUB_CLIENT_ID!);
      u.searchParams.set("redirect_uri", redirectUri);
      u.searchParams.set("scope", "read:user user:email");
      return NextResponse.redirect(u);
    }
    return NextResponse.redirect(new URL(`/login?e=${provider}_unconfigured`, baseUrl(req)));
  }

  if (action === "callback") {
    const code = req.nextUrl.searchParams.get("code");
    if (!code) return NextResponse.redirect(new URL("/login?e=cancelled", baseUrl(req)));
    try {
      const user =
        provider === "google"
          ? await googleUser(code, `${baseUrl(req)}/api/auth/callback/google`)
          : await githubUser(code);
      if (!user?.name) throw new Error("no profile");
      return await sessionRedirect(user, "/", req);
    } catch {
      return NextResponse.redirect(new URL(`/login?e=${provider}_failed`, baseUrl(req)));
    }
  }

  return NextResponse.json({ error: "not found" }, { status: 404 });
}

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ slug: string[] }> },
) {
  const { slug } = await params;
  const [action] = slug;

  if (action === "demo") {
    return sessionRedirect(
      { name: "Demo Operator", email: "demo@kairos.app", provider: "demo" },
      "/",
      req,
    );
  }

  if (action === "logout") {
    const res = NextResponse.redirect(new URL("/login", baseUrl(req)));
    res.cookies.delete(SESSION_COOKIE);
    return res;
  }

  return NextResponse.json({ error: "not found" }, { status: 404 });
}
