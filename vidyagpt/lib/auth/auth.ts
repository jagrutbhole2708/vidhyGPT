import prisma from "../prisma/prisma";
import bcrypt from "bcryptjs";
import CredentialsProvider from "next-auth/providers/credentials";
import { NextAuthOptions } from "next-auth";

// Login options:
import { loginRateLimiter } from "@/lib/auth/rate-limiter";
import { securityLogger } from "@/lib/auth/security-logger";

if (!process.env.NEXTAUTH_SECRET) {
    throw new Error("NEXTAUTH_SECRET is not defined in environment variables");
}

export const authOptions: NextAuthOptions = {
    secret: process.env.NEXTAUTH_SECRET,
    session: {
        strategy: process.env.NEXTAUTH_STRATEGY as "jwt" | "database",
        maxAge: 30 * 24 * 60 * 60, // 30 days
    },
    debug: process.env.NODE_ENV === "development",
    cookies: {
        sessionToken: {
            name:
                process.env.NODE_ENV === "production"
                    ? "__Secure-next-auth.session-token"
                    : "next-auth.session-token",
            options: {
                httpOnly: true,
                sameSite: "lax",
                path: "/",
                secure: process.env.NODE_ENV === "production",
            },
        },
    },
    providers: [
        CredentialsProvider({
            name: "Credentials",
            type: "credentials",
            id: "credentials",
            credentials: {
                email: {
                    label: "Email",
                    type: "email",
                    placeholder: "Email",
                },
                password: {
                    label: "Password",
                    type: "password",
                    placeholder: "Password",
                },
            },
            async authorize(credentials) {
                if (!credentials?.email || !credentials?.password) {
                    return null;
                }

                // Rate limiting by email
                const rateLimit = loginRateLimiter.check(credentials.email);
                if (!rateLimit.allowed) {
                    securityLogger.logRateLimited(credentials.email);
                    const minutesRemaining = Math.ceil((rateLimit.resetTime - Date.now()) / 60000);
                    throw new Error(
                        `Too many login attempts. Try again in ${minutesRemaining} minutes.`
                    );
                }
                const user = await prisma.user.findUnique({
                    where: {
                        email: credentials.email,
                    },
                    select: {
                        id: true,
                        email: true,
                        password: true,
                        createdAt: true,
                    },
                });

                if (!user) {
                    securityLogger.logLoginFailed(credentials.email, "User not found");
                    throw new Error("Invalid username or password");
                }

                // // Check if account is locked
                // const isLocked = await AccountLockout.isLocked(user.id);
                // if (isLocked) {
                //     const remainingMinutes = await AccountLockout.getRemainingLockoutTime(user.id);
                //     securityLogger.logAccountLocked(credentials.email);
                //     throw new Error(`Account is locked. Try again in ${remainingMinutes} minutes.`);
                // }

                if (!user.password) {
                    securityLogger.logLoginFailed(credentials.email, "Password not found");
                    throw new Error("Invalid username or password");
                }

                const isPasswordValid = await bcrypt.compare(credentials.password, user.password);

                if (!isPasswordValid) {
                    // Record failed attempt
                    // const nowLocked = await AccountLockout.recordFailedAttempt(user.id);

                    // if (nowLocked) {
                    //     securityLogger.logAccountLocked(credentials.email);
                    //     throw new Error(
                    //         `Account locked due to multiple failed login attempts. Try again in 15 minutes.`
                    //     );
                    // }

                    securityLogger.logLoginFailed(credentials.email, "Invalid password");
                    throw new Error("Invalid username or password");
                }

                // // Successful login: reset failed attempts and rate limit
                // await AccountLockout.resetFailedAttempts(user.id);
                loginRateLimiter.reset(credentials.email);
                securityLogger.logLoginSuccess(user.email!, user.id);

                return {
                    id: user.id,
                    email: user.email,
                    createdAt: user.createdAt.toISOString(),
                };
            },
        }),
    ],
    callbacks: {
        jwt: async ({ token, user }) => {
            if (user) {
                token.id = user.id;
            }
            return token;
        },

        session: async ({ session, token }) => {
            if (token) {
                session.user.id = token.id;
            }

            return session;
        },
    },
    pages: {
        signIn: "/login",
        error: "/error",
    },
};
