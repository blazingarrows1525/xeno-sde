import { NextResponse, type NextRequest } from "next/server";
import { SESSION_COOKIE, decodeSession } from "@/lib/auth";

// Next 16's renamed "middleware". Gates the app behind sign-in: anything without a valid
// session cookie is bounced to /login. Fails open on any internal error so a misconfiguration
// can never lock a reviewer out.
export async function proxy(req: NextRequest) {
  try {
    const session = await decodeSession(req.cookies.get(SESSION_COOKIE)?.value);
    if (session) return NextResponse.next();
    const url = req.nextUrl.clone();
    url.pathname = "/login";
    url.searchParams.set("from", req.nextUrl.pathname);
    return NextResponse.redirect(url);
  } catch {
    return NextResponse.next();
  }
}

export const config = {
  // Everything except the login page, the auth API, Next internals, and static assets.
  matcher: ["/((?!login|api/auth|_next/static|_next/image|favicon.ico).*)"],
};
