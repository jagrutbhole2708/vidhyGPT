"use client";

import { FormEvent, useEffect, useMemo, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { signIn, useSession } from "next-auth/react";
import { AuthShell } from "@/components/auth/auth-shell";

function LoginContent() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const { data: session, status } = useSession();

    const callbackUrl = useMemo(
        () => searchParams.get("callbackUrl") || "/",
        [searchParams]
    );

    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");

    useEffect(() => {
        if (status === "authenticated" && session) {
            router.replace(callbackUrl);
        }
    }, [status, session, callbackUrl, router]);

    const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        setError("");
        setLoading(true);

        const result = await signIn("credentials", {
            email,
            password,
            redirect: false,
            callbackUrl,
        });

        setLoading(false);

        if (!result || result.error) {
            setError(result?.error || "Unable to sign in. Please try again.");
            return;
        }

        router.push(result.url || callbackUrl);
    };

    return (
        <AuthShell
            title="Welcome back"
            subtitle="Sign in to continue learning with VidhyaGPT"
            footerText="Don't have an account?"
            footerLinkText="Sign up"
            footerLinkHref={`/register?callbackUrl=${encodeURIComponent(callbackUrl)}`}
        >
            <form className="space-y-4" onSubmit={onSubmit}>
                <div>
                    <label className="mb-1 block text-sm text-[#cfe0c9]" htmlFor="email">
                        Email
                    </label>
                    <input
                        id="email"
                        type="email"
                        value={email}
                        onChange={(event) => setEmail(event.target.value)}
                        required
                        className="w-full rounded-xl border border-[#86a77d]/35 bg-[#0f1b14] px-4 py-3 text-white outline-none transition-colors placeholder:text-[#7f9678] focus:border-[#a3c299]"
                        placeholder="you@example.com"
                    />
                </div>

                <div>
                    <label className="mb-1 block text-sm text-[#cfe0c9]" htmlFor="password">
                        Password
                    </label>
                    <input
                        id="password"
                        type="password"
                        value={password}
                        onChange={(event) => setPassword(event.target.value)}
                        required
                        className="w-full rounded-xl border border-[#86a77d]/35 bg-[#0f1b14] px-4 py-3 text-white outline-none transition-colors placeholder:text-[#7f9678] focus:border-[#a3c299]"
                        placeholder="Enter your password"
                    />
                </div>

                {error ? <p className="text-sm text-red-300">{error}</p> : null}

                <button
                    type="submit"
                    disabled={loading}
                    className="w-full rounded-xl bg-[#5B7B52] px-4 py-3 font-semibold text-white transition-colors hover:bg-[#4d6846] disabled:cursor-not-allowed disabled:opacity-60"
                >
                    {loading ? "Signing in..." : "Sign in"}
                </button>
            </form>
        </AuthShell>
    );
}

export default function LoginPage() {
    return (
        <Suspense fallback={null}>
            <LoginContent />
        </Suspense>
    );
}

