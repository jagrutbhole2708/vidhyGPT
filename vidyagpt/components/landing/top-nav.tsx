import Link from "next/link";
import { Session } from "next-auth";
import { AuthenticatedNav } from "@/components/landing/authenticated-nav";

type TopNavProps = {
    isDarkMode: boolean;
    setIsDarkMode: (value: boolean) => void;
    session: Session | null;
};

export function TopNav({ isDarkMode, setIsDarkMode, session }: TopNavProps) {
    return (
        <header className="pointer-events-none absolute top-0 right-0 z-10 flex w-full items-center justify-end gap-3 bg-transparent p-4">
            <div className="pointer-events-auto flex items-center gap-3">

                {session ? (
                    <AuthenticatedNav email={session.user?.email} />
                ) : (
                    <div className="flex items-center gap-2">
                        <Link
                            href="/login"
                            className="rounded-full border border-gray-200 px-4 py-1.5 text-sm font-semibold text-gray-700 transition-colors hover:bg-gray-100 dark:border-white/10 dark:text-gray-300 dark:hover:bg-white/5"
                        >
                            Sign in
                        </Link>
                        <Link
                            href="/register"
                            className="rounded-full bg-[#5B7B52] px-4 py-1.5 text-sm font-semibold text-white transition-colors hover:bg-[#4D6846]"
                        >
                            Sign up
                        </Link>
                    </div>
                )}
            </div>
        </header>
    );
}
