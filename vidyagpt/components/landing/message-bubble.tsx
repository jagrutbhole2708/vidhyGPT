"use client";

import { useState } from "react";
import {
    FiCopy,
    FiCheck,
    FiPlayCircle,
    FiThumbsDown,
    FiThumbsUp,
} from "react-icons/fi";
import { TbSquareRoot } from "react-icons/tb";
import { TypingEffect } from "@/components/landing/typing-effect";
import { Message } from "@/components/landing/types";
import { VideoJobPoller } from "@/components/video/VideoJobPoller";
import { AssistantMessage } from "@/components/chat/AssistantMessage";

type MessageBubbleProps = {
    message: Message;
    isLatestAssistant?: boolean;
    onTypingComplete?: () => void;
    onCreateVideo?: () => void;
    onVideoComplete?: (videoUrl: string) => void;
    onVideoFailed?: (error: string) => void;
};

export function MessageBubble({
    message,
    isLatestAssistant = false,
    onTypingComplete,
    onCreateVideo,
    onVideoComplete,
    onVideoFailed,
}: MessageBubbleProps) {
    const isUser = message.role === "user";
    const [copied, setCopied] = useState(false);
    const [liked, setLiked] = useState(false);
    const [disliked, setDisliked] = useState(false);

    const handleCopy = async () => {
        try {
            await navigator.clipboard.writeText(message.content);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        } catch (err) {
            console.error("Failed to copy:", err);
        }
    };

    const handleLike = () => {
        setLiked(!liked);
        if (disliked) setDisliked(false);
    };

    const handleDislike = () => {
        setDisliked(!disliked);
        if (liked) setLiked(false);
    };

    // Determine if generate video button should be disabled
    const hasVideo = !!message.videoUrl || !!message.videoJobId;
    const isVideoGenerateDisabled = hasVideo || !isLatestAssistant;

    return (
        <div className={`flex w-full ${isUser ? "justify-end" : "justify-start"}`}>
            {isUser ? (
                <div className="max-w-[80%] rounded-3xl bg-gray-100 px-5 py-3 text-[15px] text-black dark:bg-[#333333] dark:text-white">
                    {message.content}
                </div>
            ) : (
                <div className="flex w-full gap-4">
                    <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[#5B7B52] p-1.5 text-white">
                        <TbSquareRoot size={20} />
                    </div>
                    <div className="flex-1 pt-1 text-[15px] text-black dark:text-white">
                        {message.content === "Thinking..." ? (
                            /* ── Animated thinking indicator ── */
                            <div className="space-y-3">
                                <div className="flex items-center gap-2">
                                    <div className="flex gap-1">
                                        <span className="inline-block h-2 w-2 animate-bounce rounded-full bg-[#5B7B52]" style={{ animationDelay: "0ms" }} />
                                        <span className="inline-block h-2 w-2 animate-bounce rounded-full bg-[#5B7B52]" style={{ animationDelay: "150ms" }} />
                                        <span className="inline-block h-2 w-2 animate-bounce rounded-full bg-[#5B7B52]" style={{ animationDelay: "300ms" }} />
                                    </div>
                                    <span className="text-sm text-gray-400 dark:text-gray-500">
                                        Thinking...
                                    </span>
                                </div>
                                {/* Shimmer skeleton lines */}
                                <div className="space-y-2.5 opacity-40">
                                    <div className="h-3 w-3/4 animate-pulse rounded bg-gray-200 dark:bg-white/10" />
                                    <div className="h-3 w-full animate-pulse rounded bg-gray-200 dark:bg-white/10" style={{ animationDelay: "75ms" }} />
                                    <div className="h-3 w-5/6 animate-pulse rounded bg-gray-200 dark:bg-white/10" style={{ animationDelay: "150ms" }} />
                                    <div className="h-3 w-2/3 animate-pulse rounded bg-gray-200 dark:bg-white/10" style={{ animationDelay: "225ms" }} />
                                </div>
                            </div>
                        ) : message.isTyping ? (
                            /* ── Typing animation for short messages ── */
                            <TypingEffect
                                content={message.content}
                                speed={10}
                                onComplete={onTypingComplete}
                            />
                        ) : (
                            /* ── Full markdown render for completed AI messages ── */
                            <AssistantMessage content={message.content} />
                        )}

                        {/* Video poller — shown when a video job is active and not yet done */}
                        {message.videoJobId && message.videoStatus !== "done" && (
                            <VideoJobPoller
                                jobId={message.videoJobId}
                                onComplete={(url) => onVideoComplete?.(url)}
                                onFailed={(err) => onVideoFailed?.(err)}
                            />
                        )}

                        {/* Completed video player — persists across page reloads */}
                        {message.videoUrl && (message.videoStatus === "done" || !message.videoStatus) && (
                            <div className="mt-4 overflow-hidden rounded-xl border border-gray-200 dark:border-white/10">
                                <div className="relative aspect-video w-full bg-black">
                                    <video
                                        src={message.videoUrl}
                                        controls
                                        className="h-full w-full"
                                    >
                                        Your browser does not support the video tag.
                                    </video>
                                </div>
                                {/* Video footer — only like/dislike, no copy */}
                                <div className="flex items-center justify-between border-t border-gray-200 bg-gray-50 px-4 py-2 dark:border-white/10 dark:bg-[#2A2A2A]">
                                    <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
                                        <FiPlayCircle size={14} className="text-[#5B7B52]" />
                                        <span>VidhyaGPT Video</span>
                                    </div>
                                    <div className="flex items-center gap-3 text-gray-400 dark:text-gray-500">
                                        <button
                                            onClick={handleLike}
                                            className="transition-colors hover:text-gray-600 dark:hover:text-gray-300"
                                            type="button"
                                            title="Like"
                                        >
                                            <FiThumbsUp
                                                size={16}
                                                className={liked ? "text-green-500" : ""}
                                                style={liked ? { strokeWidth: 3 } : undefined}
                                            />
                                        </button>
                                        <button
                                            onClick={handleDislike}
                                            className="transition-colors hover:text-gray-600 dark:hover:text-gray-300"
                                            type="button"
                                            title="Dislike"
                                        >
                                            <FiThumbsDown
                                                size={16}
                                                className={disliked ? "text-red-500" : ""}
                                                style={disliked ? { strokeWidth: 3 } : undefined}
                                            />
                                        </button>
                                    </div>
                                </div>
                            </div>
                        )}

                        {message.showActions && !message.isTyping ? (
                            <div className="mt-6 flex w-full items-center justify-between">
                                <div className="flex flex-wrap gap-2">
                                    <button
                                        onClick={onCreateVideo}
                                        disabled={isVideoGenerateDisabled}
                                        className="flex items-center gap-2 cursor-pointer rounded-full border border-[#5B7B52]/40 bg-[#5B7B52]/5 px-3 py-1.5 text-sm text-[#5B7B52] transition-colors hover:bg-[#5B7B52]/10 disabled:cursor-not-allowed disabled:opacity-50 dark:border-[#5B7B52]/40 dark:text-[#7BA370] dark:hover:bg-[#5B7B52]/10"
                                        type="button"
                                    >
                                        <FiPlayCircle />
                                        {message.videoUrl
                                            ? "Video Generated ✓"
                                            : message.videoJobId
                                                ? "Video Generating..."
                                                : "▶ Generate Video"}
                                    </button>
                                </div>
                                <div className="flex items-center gap-3 text-gray-400 dark:text-gray-500">
                                    <button
                                        onClick={handleCopy}
                                        className="transition-colors hover:text-gray-600 dark:hover:text-gray-300"
                                        type="button"
                                        title={copied ? "Copied!" : "Copy to clipboard"}
                                    >
                                        {copied ? (
                                            <FiCheck size={16} className="text-[#5B7B52]" />
                                        ) : (
                                            <FiCopy size={16} />
                                        )}
                                    </button>
                                    <button
                                        onClick={handleLike}
                                        className="transition-colors hover:text-gray-600 dark:hover:text-gray-300"
                                        type="button"
                                        title="Like"
                                    >
                                        <FiThumbsUp
                                            size={16}
                                            className={liked ? "text-green-500" : ""}
                                            style={liked ? { strokeWidth: 3 } : undefined}
                                        />
                                    </button>
                                    <button
                                        onClick={handleDislike}
                                        className="transition-colors hover:text-gray-600 dark:hover:text-gray-300"
                                        type="button"
                                        title="Dislike"
                                    >
                                        <FiThumbsDown
                                            size={16}
                                            className={disliked ? "text-red-500" : ""}
                                            style={disliked ? { strokeWidth: 3 } : undefined}
                                        />
                                    </button>
                                </div>
                            </div>
                        ) : null}
                    </div>
                </div>
            )}
        </div>
    );
}
