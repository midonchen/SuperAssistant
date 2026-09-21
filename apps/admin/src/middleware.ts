import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function middleware(request: NextRequest) {
  const password = process.env.ADMIN_PASSWORD;
  if (!password) {
    return NextResponse.next();
  }
  const auth = request.headers.get("authorization") ?? "";
  const expected = "Basic " + Buffer.from(`admin:${password}`).toString("base64");
  if (auth !== expected) {
    return new NextResponse("Unauthorized", {
      status: 401,
      headers: { "WWW-Authenticate": 'Basic realm="SuperAssistant Admin"' },
    });
  }
  return NextResponse.next();
}

export const config = {
  runtime: "nodejs",
  matcher: ["/:path*"],
};
