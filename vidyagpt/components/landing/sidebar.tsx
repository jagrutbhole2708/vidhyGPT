"use client";

import { Dispatch, SetStateAction, useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import {
    FiEdit,
    FiMessageSquare,
    FiSidebar,
    FiVideo,
} from "react-icons/fi";
import { FaDiscord, FaLinkedin, FaTiktok } from "react-icons/fa";
import { NavItem } from "@/components/landing/nav-item";
import { Session } from "next-auth";

type SidebarProps = {
    isSidebarOpen: boolean;
    setIsSidebarOpen: Dispatch<SetStateAction<boolean>>;
    session: Session | null;
};

type ChatHistoryItem = {
    id: string;
    title: string | null;
    subject: string;
    updatedAt: string;
};

export function Sidebar({ isSidebarOpen, setIsSidebarOpen, session }: SidebarProps) {
    const router = useRouter();
    const pathname = usePathname();
    const [recentChats, setRecentChats] = useState<ChatHistoryItem[]>([]);

    // Fetch chat history when user is logged in
    useEffect(() => {
        if (!session) {
            setRecentChats([]);
            return;
        }

        async function fetchChats() {
            try {
                const res = await fetch("/api/chat/session");
                if (!res.ok) return;
                const json = await res.json();
                if (json.success && json.data) {
                    // Sort by most recent first
                    const sorted = json.data.sort(
                        (a: any, b: any) =>
                            new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime()
                    );
                    setRecentChats(sorted.slice(0, 20)); // Show max 20
                }
            } catch {
                // silently fail
            }
        }
        fetchChats();
    }, [session, pathname]); // Re-fetch when navigating

    const handleNewChat = () => {
        router.push("/");
    };

    const handleChatClick = (chatId: string) => {
        router.push(`/chat/${chatId}`);
    };

    const handleVideoGalleryClick = () => {
        router.push("/video-gallery");
    };

    // Check if a chat is currently active
    const activeChatId = pathname?.startsWith("/chat/")
        ? pathname.split("/chat/")[1]
        : null;

    return (
        <>
            <aside
                className={`${isSidebarOpen ? "w-[260px]" : "w-[68px]"} flex shrink-0 flex-col border-r border-gray-200 transition-all duration-300 ease-in-out dark:border-white/10`}
            >
                <div
                    className={`flex items-center px-3 transition-all duration-300 ${isSidebarOpen ? "h-[60px] justify-between" : "h-auto flex-col justify-center gap-4 py-4"}`}
                >
                    <button
                        onClick={() => setIsSidebarOpen((prev) => !prev)}
                        className="rounded-md p-2 text-gray-500 transition-colors hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-white/5"
                        type="button"
                    >
                        <FiSidebar size={20} />
                    </button>
                    <button
                        onClick={handleNewChat}
                        className="rounded-md p-2 text-gray-500 transition-colors hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-white/5"
                        type="button"
                        title="New Chat"
                    >
                        <FiEdit size={20} />
                    </button>
                </div>

                <div className="flex flex-1 flex-col gap-1 overflow-x-hidden overflow-y-auto px-2 py-2">
                    <div onClick={handleVideoGalleryClick}>
                        <NavItem
                            icon={<FiVideo size={20} className="text-[#5B7B52]" />}
                            label="Video Gallery"
                            isOpen={isSidebarOpen}
                        />
                    </div>

                    {/* Recent Chats */}
                    {session && (
                        <div
                            className={`overflow-hidden transition-all duration-300 ${isSidebarOpen ? "mt-6 mb-2 max-h-[calc(100vh-300px)] px-1 opacity-100" : "m-0 max-h-0 p-0 opacity-0"}`}
                        >
                            <h3 className="mb-2 whitespace-nowrap px-2 text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500">
                                Recent Chats
                            </h3>

                            {recentChats.length === 0 ? (
                                <p className="whitespace-nowrap px-2 text-sm text-gray-400 dark:text-gray-600">
                                    No chats yet
                                </p>
                            ) : (
                                <div className="flex flex-col gap-0.5">
                                    {recentChats.map((chat) => (
                                        <button
                                            key={chat.id}
                                            onClick={() => handleChatClick(chat.id)}
                                            className={`group flex w-full items-center gap-2 rounded-lg px-2 py-2 text-left text-sm transition-colors ${
                                                activeChatId === chat.id
                                                    ? "bg-gray-100 font-medium text-black dark:bg-white/10 dark:text-white"
                                                    : "text-gray-600 hover:bg-gray-50 dark:text-gray-400 dark:hover:bg-white/5"
                                            }`}
                                            type="button"
                                        >
                                            <FiMessageSquare
                                                size={14}
                                                className="shrink-0 text-gray-400 dark:text-gray-500"
                                            />
                                            <span className="truncate">
                                                {chat.title || "New Chat"}
                                            </span>
                                        </button>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}

                    {/* Collapsed chat icon */}
                    <div
                        className={`flex justify-center overflow-hidden transition-all duration-300 ${!isSidebarOpen ? "mt-4 max-h-20 opacity-100" : "m-0 max-h-0 opacity-0"}`}
                    >
                        <FiMessageSquare size={20} className="text-gray-500 dark:text-gray-400" />
                    </div>
                </div>

                <div className="flex flex-col gap-2 overflow-hidden p-3">
                    <div
                        className={`mt-3 mb-2 flex items-center text-gray-400 transition-all duration-300 dark:text-gray-500 ${isSidebarOpen ? "flex-row justify-start gap-5 px-3" : "flex-col justify-center gap-5"}`}
                    >
                        <FaDiscord
                            size={18}
                            className="shrink-0 cursor-pointer transition-colors hover:text-[#5B7B52]"
                        />
                        <FaTiktok
                            size={18}
                            className="shrink-0 cursor-pointer transition-colors hover:text-[#5B7B52]"
                        />
                        <FaLinkedin
                            size={18}
                            className="shrink-0 cursor-pointer transition-colors hover:text-[#5B7B52]"
                        />
                    </div>
                </div>
            </aside>
        </>
    );
}
