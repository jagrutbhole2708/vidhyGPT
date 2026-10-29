import { signOut } from "next-auth/react";

type AuthenticatedNavProps = {
    email?: string | null;
};

export function AuthenticatedNav({ email }: AuthenticatedNavProps) {
    return (
        <div className="flex items-center gap-3 rounded-full border border-gray-200 bg-white px-3 py-1.5 dark:border-white/10 dark:bg-[#2A2A2A]">
            <span className="max-w-40 truncate text-sm text-gray-700 dark:text-gray-300">
                {email ?? "Signed in"}
            </span>
            <button
                onClick={() => signOut({ callbackUrl: "/" })}
                className="rounded-full bg-[#5B7B52] px-3 py-1 text-sm font-semibold text-white transition-colors hover:bg-[#4D6846]"
                type="button"
            >
                Sign out
            </button>
        </div>
    );
}
