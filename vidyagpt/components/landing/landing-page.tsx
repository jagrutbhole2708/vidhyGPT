"use client";

import { useState } from "react";
import { MainContent } from "@/components/landing/main-content";
import { Sidebar } from "@/components/landing/sidebar";
import { useSession } from "next-auth/react";

export function LandingPage() {
    const { data: session, status } = useSession();
    const [isSidebarOpen, setIsSidebarOpen] = useState(true);
    const [isDarkMode, setIsDarkMode] = useState(true);

    // If authenticated, show sidebar + input-only view
    if (status === "authenticated" && session) {
        return (
            <div className="flex h-screen w-full overflow-hidden bg-white font-sans text-black transition-colors duration-200 dark:bg-[#212121] dark:text-white">
                <Sidebar isSidebarOpen={isSidebarOpen} setIsSidebarOpen={setIsSidebarOpen} session={session} />
                <MainContent isDarkMode={isDarkMode} setIsDarkMode={setIsDarkMode} isAuthenticated={true} />
            </div>
        );
    }

    // If not authenticated, show full landing page without sidebar
    return (
        <div className="flex h-screen w-full overflow-hidden bg-white font-sans text-black transition-colors duration-200 dark:bg-[#212121] dark:text-white">
            <MainContent isDarkMode={isDarkMode} setIsDarkMode={setIsDarkMode} isAuthenticated={false} />
        </div>
    );
}
