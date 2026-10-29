"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
import {
    FiVideo,
    FiPlay,
    FiDownload,
    FiStar,
    FiLoader,
    FiArrowLeft,
} from "react-icons/fi";
import { Sidebar } from "@/components/landing/sidebar";
import { TopNav } from "@/components/landing/top-nav";

type UserVideo = {
    id: string;
    title: string;
    subject: string;
    videoUrl: string | null;
    createdAt: string;
};

type ExampleVideo = {
    id: string;
    title: string;
    description: string | null;
    subject: string;
    videoUrl: string;
    thumbnailUrl: string | null;
    createdAt: string;
};

export default function VideoGalleryPage() {
    const router = useRouter();
    const { data: session } = useSession();

    const [isSidebarOpen, setIsSidebarOpen] = useState(true);
    const [isDarkMode, setIsDarkMode] = useState(true);
    const [activeTab, setActiveTab] = useState<"my-videos" | "examples">("my-videos");

    const [userVideos, setUserVideos] = useState<UserVideo[]>([]);
    const [exampleVideos, setExampleVideos] = useState<ExampleVideo[]>([]);
    const [userLoading, setUserLoading] = useState(true);
    const [examplesLoading, setExamplesLoading] = useState(true);

    // Dark mode
    useEffect(() => {
        if (isDarkMode) {
            document.documentElement.classList.add("dark");
        } else {
            document.documentElement.classList.remove("dark");
        }
    }, [isDarkMode]);

    // Fetch user's videos
    useEffect(() => {
        if (!session) {
            setUserLoading(false);
            return;
        }

        async function fetchUserVideos() {
            try {
                const res = await fetch("/api/video/gallery");
                if (!res.ok) return;
                const json = await res.json();
                if (json.success && json.data) {
                    setUserVideos(json.data);
                }
            } catch {
                // silently fail
            } finally {
                setUserLoading(false);
            }
        }
        fetchUserVideos();
    }, [session]);

    // Fetch example videos
    useEffect(() => {
        async function fetchExamples() {
            try {
                const res = await fetch("/api/video/gallery/examples");
                if (!res.ok) return;
                const json = await res.json();
                if (json.success && json.data) {
                    setExampleVideos(json.data);
                }
            } catch {
                // silently fail
            } finally {
                setExamplesLoading(false);
            }
        }
        fetchExamples();
    }, []);

    return (
        <div className="flex h-screen w-full overflow-hidden bg-white font-sans text-black transition-colors duration-200 dark:bg-[#212121] dark:text-white">
            <Sidebar
                isSidebarOpen={isSidebarOpen}
                setIsSidebarOpen={setIsSidebarOpen}
                session={session ?? null}
            />
            <main className="relative flex h-full flex-1 overflow-hidden">
                <div className="relative flex h-full flex-1 flex-col w-full">
                    <TopNav
                        isDarkMode={isDarkMode}
                        setIsDarkMode={setIsDarkMode}
                        session={session ?? null}
                    />

                    <div className="flex-1 overflow-y-auto pt-16">
                        <div className="mx-auto w-full max-w-6xl px-6 py-8">
                            {/* Header */}
                            <div className="mb-8 flex items-center gap-4">
                                <button
                                    onClick={() => router.push("/")}
                                    className="flex h-10 w-10 items-center justify-center rounded-xl border border-gray-200 text-gray-500 transition-colors hover:bg-gray-50 dark:border-white/10 dark:text-gray-400 dark:hover:bg-white/5"
                                    type="button"
                                >
                                    <FiArrowLeft size={18} />
                                </button>
                                <div>
                                    <h1 className="text-2xl font-bold text-black dark:text-white">
                                        Video Gallery
                                    </h1>
                                    <p className="text-sm text-gray-500 dark:text-gray-400">
                                        All your AI-generated educational videos in one place
                                    </p>
                                </div>
                            </div>

                            {/* Tabs */}
                            <div className="mb-8 flex gap-2">
                                <button
                                    onClick={() => setActiveTab("my-videos")}
                                    className={`flex items-center gap-2 rounded-lg px-5 py-2.5 text-sm font-medium transition-all duration-200 border ${
                                        activeTab === "my-videos"
                                            ? "border-[#5B7B52] bg-[#5B7B52]/10 text-[#5B7B52] dark:border-[#7BA370] dark:text-[#7BA370]"
                                            : "border-gray-200 bg-white text-gray-600 hover:border-[#5B7B52]/40 dark:border-white/10 dark:bg-white/5 dark:text-gray-400"
                                    }`}
                                    type="button"
                                >
                                    <FiVideo size={16} />
                                    My Videos
                                </button>
                                <button
                                    onClick={() => setActiveTab("examples")}
                                    className={`flex items-center gap-2 rounded-lg px-5 py-2.5 text-sm font-medium transition-all duration-200 border ${
                                        activeTab === "examples"
                                            ? "border-[#5B7B52] bg-[#5B7B52]/10 text-[#5B7B52] dark:border-[#7BA370] dark:text-[#7BA370]"
                                            : "border-gray-200 bg-white text-gray-600 hover:border-[#5B7B52]/40 dark:border-white/10 dark:bg-white/5 dark:text-gray-400"
                                    }`}
                                    type="button"
                                >
                                    <FiStar size={16} />
                                    Example Videos
                                </button>
                            </div>

                            {/* My Videos Tab */}
                            {activeTab === "my-videos" && (
                                <div>
                                    {userLoading ? (
                                        <div className="flex items-center justify-center py-24">
                                            <FiLoader className="h-8 w-8 animate-spin text-[#5B7B52]" />
                                        </div>
                                    ) : userVideos.length === 0 ? (
                                        <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-gray-300 py-24 text-center dark:border-white/10">
                                            <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-[#5B7B52]/10 text-[#5B7B52]">
                                                <FiVideo size={32} />
                                            </div>
                                            <h3 className="mb-2 text-lg font-semibold text-gray-700 dark:text-gray-300">
                                                No videos yet
                                            </h3>
                                            <p className="mb-6 max-w-sm text-sm text-gray-500 dark:text-gray-400">
                                                Start a chat and click &quot;Generate Video&quot; on any AI answer to create your first educational video!
                                            </p>
                                            <button
                                                onClick={() => router.push("/")}
                                                className="rounded-lg bg-[#5B7B52] px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-[#4A6A43]"
                                                type="button"
                                            >
                                                Start a Chat
                                            </button>
                                        </div>
                                    ) : (
                                        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
                                            {userVideos.map((video) => (
                                                <VideoCard
                                                    key={video.id}
                                                    title={video.title}
                                                    subject={video.subject}
                                                    videoUrl={video.videoUrl}
                                                    createdAt={video.createdAt}
                                                />
                                            ))}
                                        </div>
                                    )}
                                </div>
                            )}

                            {/* Examples Tab */}
                            {activeTab === "examples" && (
                                <div>
                                    {examplesLoading ? (
                                        <div className="flex items-center justify-center py-24">
                                            <FiLoader className="h-8 w-8 animate-spin text-[#5B7B52]" />
                                        </div>
                                    ) : exampleVideos.length === 0 ? (
                                        <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-gray-300 py-24 text-center dark:border-white/10">
                                            <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-[#5B7B52]/10 text-[#5B7B52]">
                                                <FiStar size={32} />
                                            </div>
                                            <h3 className="mb-2 text-lg font-semibold text-gray-700 dark:text-gray-300">
                                                Coming soon
                                            </h3>
                                            <p className="max-w-sm text-sm text-gray-500 dark:text-gray-400">
                                                We&apos;re curating the best example videos. Check back soon!
                                            </p>
                                        </div>
                                    ) : (
                                        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
                                            {exampleVideos.map((video) => (
                                                <VideoCard
                                                    key={video.id}
                                                    title={video.title}
                                                    subject={video.subject}
                                                    videoUrl={video.videoUrl}
                                                    description={video.description}
                                                    createdAt={video.createdAt}
                                                    isFeatured
                                                />
                                            ))}
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            </main>
        </div>
    );
}

// ── Video Card Component ──
function VideoCard({
    title,
    subject,
    videoUrl,
    description,
    createdAt,
    isFeatured,
}: {
    title: string;
    subject: string;
    videoUrl: string | null;
    description?: string | null;
    createdAt: string;
    isFeatured?: boolean;
}) {
    return (
        <div className="group overflow-hidden rounded-xl border border-gray-200 bg-white transition-all duration-200 hover:border-[#5B7B52]/30 hover:shadow-lg dark:border-white/10 dark:bg-[#2A2A2A] dark:hover:border-[#5B7B52]/30">
            {videoUrl ? (
                <div className="relative aspect-video w-full bg-black">
                    <video
                        src={videoUrl}
                        controls
                        className="h-full w-full"
                        preload="metadata"
                    >
                        Your browser does not support the video tag.
                    </video>
                </div>
            ) : (
                <div className="flex aspect-video items-center justify-center bg-gray-100 dark:bg-white/5">
                    <FiPlay size={40} className="text-gray-300 dark:text-gray-600" />
                </div>
            )}
            <div className="p-4">
                <div className="flex items-start justify-between gap-2">
                    <h4 className="line-clamp-2 text-sm font-semibold text-black dark:text-white">
                        {title}
                    </h4>
                    {isFeatured && (
                        <FiStar size={14} className="mt-0.5 shrink-0 text-amber-500" />
                    )}
                </div>
                {description && (
                    <p className="mt-1 line-clamp-2 text-xs text-gray-500 dark:text-gray-400">
                        {description}
                    </p>
                )}
                <div className="mt-3 flex items-center justify-between">
                    <span className="rounded-md bg-[#5B7B52]/10 px-2 py-0.5 text-xs font-medium text-[#5B7B52]">
                        {subject}
                    </span>
                    <span className="text-xs text-gray-400 dark:text-gray-500">
                        {new Date(createdAt).toLocaleDateString()}
                    </span>
                </div>
                {videoUrl && (
                    <a
                        href={videoUrl}
                        download
                        target="_blank"
                        rel="noopener noreferrer"
                        className="mt-3 flex w-full items-center justify-center gap-1.5 rounded-lg border border-gray-200 py-2 text-sm text-gray-600 transition-colors hover:bg-gray-50 dark:border-white/10 dark:text-gray-400 dark:hover:bg-white/5"
                    >
                        <FiDownload size={14} />
                        Download
                    </a>
                )}
            </div>
        </div>
    );
}
