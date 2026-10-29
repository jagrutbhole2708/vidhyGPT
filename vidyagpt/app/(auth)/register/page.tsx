"use client";

import { FormEvent, useMemo, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { signIn } from "next-auth/react";
import { AuthShell } from "@/components/auth/auth-shell";

function RegisterContent() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const callbackUrl = useMemo(
        () => searchParams.get("callbackUrl") || "/",
        [searchParams]
    );

    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");

    const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        setError("");
        setLoading(true);

        const derivedName = email.split("@")[0] || "User";

        const registerResponse = await fetch("/api/auth/register", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                name: derivedName,
                email,
                password,
            }),
        });

        const registerResult = (await registerResponse.json()) as {
            success: boolean;
            message: string;
        };

        if (!registerResponse.ok || !registerResult.success) {
            setLoading(false);
            setError(registerResult.message || "Unable to create account.");
            return;
        }

        const loginResult = await signIn("credentials", {
            email,
            password,
            redirect: false,
            callbackUrl,
        });

        setLoading(false);

        if (!loginResult || loginResult.error) {
            setError(loginResult?.error || "Registered, but sign in failed. Please log in.");
            router.push(`/login?callbackUrl=${encodeURIComponent(callbackUrl)}`);
            return;
        }

        router.push(loginResult.url || callbackUrl);
    };

    return (
        <AuthShell
            title="Create account"
            subtitle="Start solving faster with VidhyaGPT"
            footerText="Already have an account?"
            footerLinkText="Sign in"
            footerLinkHref={`/login?callbackUrl=${encodeURIComponent(callbackUrl)}`}
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
                        minLength={6}
                        className="w-full rounded-xl border border-[#86a77d]/35 bg-[#0f1b14] px-4 py-3 text-white outline-none transition-colors placeholder:text-[#7f9678] focus:border-[#a3c299]"
                        placeholder="At least 6 characters"
                    />
                </div>

                {error ? <p className="text-sm text-red-300">{error}</p> : null}

                <button
                    type="submit"
                    disabled={loading}
                    className="w-full rounded-xl bg-[#5B7B52] px-4 py-3 font-semibold text-white transition-colors hover:bg-[#4d6846] disabled:cursor-not-allowed disabled:opacity-60"
                >
                    {loading ? "Creating account..." : "Sign up"}
                </button>
            </form>
        </AuthShell>
    );
}

export default function RegisterPage() {
    return (
        <Suspense fallback={null}>
            <RegisterContent />
        </Suspense>
    );
}

