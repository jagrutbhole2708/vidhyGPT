"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
import { HeroSection } from "@/components/landing/hero-section";
import { SUBJECT_TABS } from "@/components/landing/sample-data";
import { TopNav } from "@/components/landing/top-nav";
import { savePendingPrompt, getPendingPrompt, clearPendingPrompt } from "@/lib/pending-prompt";
import { TbSquareRoot } from "react-icons/tb";
import { FiBookOpen, FiVideo, FiMessageSquare, FiZap, FiSearch, FiPlay } from "react-icons/fi";

type MainContentProps = {
    isDarkMode: boolean;
    setIsDarkMode: (value: boolean) => void;
    isAuthenticated: boolean;
};

export function MainContent({ isDarkMode, setIsDarkMode, isAuthenticated }: MainContentProps) {
    const router = useRouter();
    const { data: session } = useSession();

    const [activeTab, setActiveTab] = useState(SUBJECT_TABS[0]);
    const [inputValue, setInputValue] = useState("");
    const [isLoading, setIsLoading] = useState(false);

    useEffect(() => {
        const pending = getPendingPrompt();
        if (pending) {
            setInputValue(pending);
            clearPendingPrompt();
        }
    }, []);

    useEffect(() => {
        if (isDarkMode) {
            document.documentElement.classList.add("dark");
        } else {
            document.documentElement.classList.remove("dark");
        }
    }, [isDarkMode]);

    // ── Send first message: create session → redirect to /chat/:id ──
    const handleSend = async () => {
        const prompt = inputValue.trim();
        if (!prompt || isLoading) return;

        // Not logged in → save prompt and go to login
        if (!session) {
            savePendingPrompt(prompt);
            router.push("/login?callbackUrl=/");
            return;
        }

        setIsLoading(true);

        try {
            // 1. Create a new chat session
            const sessionRes = await fetch("/api/chat/session", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    board: "CBSE",
                    classLevel: "10",
                    subject: activeTab,
                }),
            });

            if (!sessionRes.ok) throw new Error("Failed to create session");
            const sessionJson = await sessionRes.json();
            if (!sessionJson.success) throw new Error("Session creation failed");

            const newSessionId = sessionJson.data.sessionId;

            // 2. Save the prompt so the chat page can pick it up
            savePendingPrompt(prompt);

            // 3. Navigate to /chat/:sessionId (like ChatGPT)
            router.push(`/chat/${newSessionId}`);
        } catch (err: any) {
            console.error("Session creation error:", err);
            setIsLoading(false);
        }
    };

    // ── Authenticated view: just the input box (like ChatGPT home) ──
    if (isAuthenticated) {
        return (
            <main className="relative flex h-full flex-1 overflow-hidden">
                <div className="relative flex h-full w-full flex-1 flex-col">
                    <TopNav
                        isDarkMode={isDarkMode}
                        setIsDarkMode={setIsDarkMode}
                        session={session ?? null}
                    />

                    <HeroSection
                        activeTab={activeTab}
                        setActiveTab={setActiveTab}
                        inputValue={inputValue}
                        setInputValue={setInputValue}
                        onSend={handleSend}
                        tabs={SUBJECT_TABS}
                    />
                </div>
            </main>
        );
    }

    // ── Unauthenticated view: full landing page with features, how it works, footer ──
    return (
        <main className="relative flex h-full flex-1 flex-col overflow-y-auto scroll-smooth">
            {/* Hero Section (min-h-screen) */}
            <div className="flex min-h-screen flex-col">
                <TopNav
                    isDarkMode={isDarkMode}
                    setIsDarkMode={setIsDarkMode}
                    session={session ?? null}
                />
                <HeroSection
                    activeTab={activeTab}
                    setActiveTab={setActiveTab}
                    inputValue={inputValue}
                    setInputValue={setInputValue}
                    onSend={handleSend}
                    tabs={SUBJECT_TABS}
                />
            </div>

            {/* Bento Grid Section (min-h-screen) */}
            <section className="flex min-h-screen w-full flex-col items-center justify-center border-t border-gray-200 bg-gray-50 py-20 dark:border-white/5 dark:bg-[#1A1A1A]">
                <div className="mx-auto w-full max-w-5xl px-6">
                    <h2 className="mb-4 text-center text-4xl font-bold text-black dark:text-white">
                        How It Works
                    </h2>
                    <p className="mb-14 text-center text-lg text-gray-500 dark:text-gray-400">
                        From question to deep understanding in three simple steps
                    </p>

                    <div className="grid grid-cols-1 gap-6 md:grid-cols-3 lg:grid-rows-2">
                        {/* Tile 1: Ask Your Question - Span 2 cols */}
                        <div className="group relative flex flex-col justify-between overflow-hidden rounded-3xl border border-gray-200 bg-white p-8 dark:border-white/10 dark:bg-[#2A2A2A] md:col-span-2">
                            <div className="absolute -right-10 -top-10 h-40 w-40 rounded-full bg-[#5B7B52]/10 blur-3xl transition-all group-hover:bg-[#5B7B52]/20"></div>
                            <div className="relative z-10">
                                <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[#5B7B52]/10 text-[#5B7B52]">
                                    <FiSearch size={24} />
                                </div>
                            </div>
                            <div className="relative z-10 mt-16">
                                <div className="mb-2 text-xs font-bold uppercase tracking-widest text-[#5B7B52]">Step 1</div>
                                <h3 className="mb-2 text-3xl font-bold text-black dark:text-white">Ask Your Question</h3>
                                <p className="text-gray-500 dark:text-gray-400">
                                    Type any question from Maths, Physics, or Chemistry. Our AI understands natural language and parses complex formulas instantly.
                                </p>
                            </div>
                        </div>

                        {/* Tile 2: NCERT Aligned - Span 1 col, 1 row */}
                        <div className="group relative flex flex-col justify-between overflow-hidden rounded-3xl border border-gray-200 bg-[#5B7B52] p-8 text-white md:col-span-1">
                            <div className="absolute right-0 top-0 h-full w-full bg-gradient-to-br from-white/10 to-transparent"></div>
                            <div className="relative z-10">
                                <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-white/20 text-white backdrop-blur-md">
                                    <FiBookOpen size={24} />
                                </div>
                            </div>
                            <div className="relative z-10 mt-16">
                                <h3 className="mb-2 text-2xl font-bold">NCERT Aligned</h3>
                                <p className="text-white/80">All answers strictly follow the CBSE curriculum.</p>
                            </div>
                        </div>

                        {/* Tile 3: Get Detailed Answers - Span 1 col, 1 row */}
                        <div className="group relative flex flex-col justify-between overflow-hidden rounded-3xl border border-gray-200 bg-white p-8 dark:border-white/10 dark:bg-[#2A2A2A] md:col-span-1">
                            <div className="absolute -bottom-10 -right-10 h-32 w-32 rounded-full bg-[#5B7B52]/10 blur-3xl transition-all group-hover:bg-[#5B7B52]/20"></div>
                            <div className="relative z-10">
                                <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[#5B7B52]/10 text-[#5B7B52]">
                                    <FiZap size={24} />
                                </div>
                            </div>
                            <div className="relative z-10 mt-16">
                                <div className="mb-2 text-xs font-bold uppercase tracking-widest text-[#5B7B52]">Step 2</div>
                                <h3 className="mb-2 text-2xl font-bold text-black dark:text-white">Get Detailed Answers</h3>
                                <p className="text-gray-500 dark:text-gray-400">Step-by-step explanations with formulas and diagrams.</p>
                            </div>
                        </div>

                        {/* Tile 4: Watch AI Videos - Span 2 cols */}
                        <div className="group relative flex flex-col justify-between overflow-hidden rounded-3xl border border-gray-200 bg-white p-8 dark:border-white/10 dark:bg-[#2A2A2A] md:col-span-2">
                            <div className="absolute inset-0 bg-gradient-to-br from-[#5B7B52]/5 to-transparent"></div>
                            <div className="relative z-10 flex items-center justify-between">
                                <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[#5B7B52]/10 text-[#5B7B52]">
                                    <FiPlay size={24} />
                                </div>
                                <div className="rounded-full bg-[#5B7B52]/10 px-3 py-1 text-xs font-semibold text-[#5B7B52]">Visual Learning</div>
                            </div>
                            <div className="relative z-10 mt-16">
                                <div className="mb-2 text-xs font-bold uppercase tracking-widest text-[#5B7B52]">Step 3</div>
                                <h3 className="mb-2 text-3xl font-bold text-black dark:text-white">Watch Explainer Videos</h3>
                                <p className="text-gray-500 dark:text-gray-400">
                                    Turn any complex math or physics answer into an engaging animated video with AI voice narration. Visual learning made simple.
                                </p>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            {/* Footer */}
            <footer className="w-full border-t border-gray-200 bg-white py-10 dark:border-white/5 dark:bg-[#212121]">
                <div className="mx-auto max-w-5xl px-6">
                    <div className="flex flex-col items-center justify-between gap-6 md:flex-row">
                        <div className="flex items-center gap-2">
                            <div className="rounded-full bg-[#5B7B52] p-1.5 text-white">
                                <TbSquareRoot size={20} />
                            </div>
                            <span className="text-lg font-semibold text-black dark:text-white">
                                VidhyaGPT
                            </span>
                        </div>

                        <div className="flex items-center gap-6 text-sm text-gray-500 dark:text-gray-400">
                            <a href="#" className="transition-colors hover:text-[#5B7B52]">About</a>
                            <a href="#" className="transition-colors hover:text-[#5B7B52]">Privacy</a>
                            <a href="#" className="transition-colors hover:text-[#5B7B52]">Terms</a>
                            <a href="#" className="transition-colors hover:text-[#5B7B52]">Contact</a>
                        </div>

                        <p className="text-xs text-gray-400 dark:text-gray-500">
                            © 2026 VidhyaGPT. All rights reserved.
                        </p>
                    </div>
                </div>
            </footer>
        </main>
    );
}
