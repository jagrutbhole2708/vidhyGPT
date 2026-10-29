import Link from "next/link";
import { ReactNode } from "react";
import { TbSquareRoot } from "react-icons/tb";

type AuthShellProps = {
    title: string;
    subtitle: string;
    children: ReactNode;
    footerText: string;
    footerLinkText: string;
    footerLinkHref: string;
};

export function AuthShell({
    title,
    subtitle,
    children,
    footerText,
    footerLinkText,
    footerLinkHref,
}: AuthShellProps) {
    return (
        <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-[#212121] px-4 py-10">
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_20%,rgba(91,123,82,0.32),transparent_45%),radial-gradient(circle_at_80%_15%,rgba(198,220,173,0.18),transparent_35%),radial-gradient(circle_at_50%_90%,rgba(91,123,82,0.24),transparent_45%)]" />

            <div className="relative w-full max-w-md rounded-3xl border border-[#8aac82]/30 bg-[#132118]/90 p-8 shadow-[0_20px_80px_rgba(0,0,0,0.45)] backdrop-blur">
                <Link
                    href="/"
                    className="mb-7 inline-flex items-center gap-2 rounded-full border border-[#8aac82]/40 bg-[#1a2d21] px-3 py-1.5 text-sm text-[#d8e8d2] transition-colors hover:border-[#8aac82]/70"
                >
                    <span className="rounded-full bg-[#5B7B52] p-1 text-white">
                        <TbSquareRoot size={16} />
                    </span>
                    VidhyaGPT
                </Link>

                <h1 className="text-3xl font-semibold text-white">{title}</h1>
                <p className="mt-2 text-sm text-[#b9cbb3]">{subtitle}</p>

                <div className="mt-8">{children}</div>

                <p className="mt-6 text-center text-sm text-[#b9cbb3]">
                    {footerText}{" "}
                    <Link href={footerLinkHref} className="font-semibold text-[#d9f6ca] hover:underline">
                        {footerLinkText}
                    </Link>
                </p>
            </div>
        </div>
    );
}
