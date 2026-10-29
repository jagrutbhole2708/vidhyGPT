import { getToken } from "next-auth/jwt";
import { NextRequest, NextResponse } from "next/server";

export async function proxy(req: NextRequest) {
    try {
        const token = await getToken({
            req,
            secret: process.env.NEXTAUTH_SECRET,
        });

        const { pathname } = req.nextUrl;

        const guestOnlyRoutes = ["/login", "/register", "/logout"];

        const isGuestOnlyRoute =
            guestOnlyRoutes.includes(pathname) ||
            pathname.startsWith("/login") ||
            pathname.startsWith("/register") ||
            pathname.startsWith("/logout");

        const protectedRoutes = ["/dashboard", "/profile"];

        const isProtectedRoute = protectedRoutes.some((route) => pathname.startsWith(route));

        if (token && isGuestOnlyRoute) {
            return NextResponse.redirect(new URL("/", req.url));
        }

        if (!token && isProtectedRoute) {
            const loginUrl = new URL("/login", req.url);
            loginUrl.searchParams.set("callbackUrl", pathname);
            return NextResponse.redirect(loginUrl);
        }

        return NextResponse.next();
    } catch (error) {
        console.error("Error in proxy middleware:", error);
        return NextResponse.next();
    }
}

export const config = {
    matcher: ["/", "/login", "/register", "/logout", "/dashboard/:path*", "/profile"],
};
