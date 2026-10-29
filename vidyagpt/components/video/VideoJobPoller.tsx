"use client";

import { useEffect, useRef, useState } from "react";
import { FiAlertCircle, FiDownload, FiLoader, FiPlay } from "react-icons/fi";
import { VideoJobData } from "@/components/landing/types";

type VideoJobPollerProps = {
    jobId: string;
    onComplete: (videoUrl: string) => void;
    onFailed: (error: string) => void;
};

const POLL_INTERVAL = 3000; // 3 seconds

const STEP_LABELS: Record<string, string> = {
    "5": "Starting up...",
    "15": "Writing script...",
    "35": "Generating narration audio...",
    "55": "Creating animations...",
    "80": "Rendering scenes...",
    "85": "Merging audio & video...",
    "90": "Final assembly...",
    "95": "Uploading to cloud...",
    "100": "Complete!",
};

function getStepLabel(progress: number): string {
    const thresholds = [5, 15, 35, 55, 80, 85, 90, 95, 100];
    for (const t of thresholds) {
        if (progress <= t) return STEP_LABELS[String(t)];
    }
    return "Processing...";
}

export function VideoJobPoller({ jobId, onComplete, onFailed }: VideoJobPollerProps) {
    const [progress, setProgress] = useState(0);
    const [status, setStatus] = useState<string>("pending");
    const [error, setError] = useState<string | null>(null);
    const [videoUrl, setVideoUrl] = useState<string | null>(null);
    const intervalRef = useRef<NodeJS.Timeout | null>(null);
    const completedRef = useRef(false);

    useEffect(() => {
        if (!jobId) return;

        const poll = async () => {
            try {
                const res = await fetch(`/api/video/${jobId}`);
                if (!res.ok) return;

                const json = await res.json();
                if (!json.success) return;

                const data: VideoJobData = json.data;
                setProgress(data.progress);
                setStatus(data.status);

                if (data.status === "done" && data.videoUrl && !completedRef.current) {
                    completedRef.current = true;
                    setVideoUrl(data.videoUrl);
                    onComplete(data.videoUrl);
                    if (intervalRef.current) clearInterval(intervalRef.current);
                }

                if (data.status === "failed" && !completedRef.current) {
                    completedRef.current = true;
                    setError(data.error || "Video generation failed");
                    onFailed(data.error || "Video generation failed");
                    if (intervalRef.current) clearInterval(intervalRef.current);
                }
            } catch {
                // Silently retry on network errors
            }
        };

        // Poll immediately, then every 3s
        poll();
        intervalRef.current = setInterval(poll, POLL_INTERVAL);

        return () => {
            if (intervalRef.current) clearInterval(intervalRef.current);
        };
    }, [jobId, onComplete, onFailed]);

    // ── Failed state ──
    if (error) {
        return (
            <div className="mt-4 flex items-center gap-3 rounded-xl border border-red-200 bg-red-50 p-4 dark:border-red-800/30 dark:bg-red-950/20">
                <FiAlertCircle className="shrink-0 text-red-500" size={20} />
                <div className="flex-1">
                    <p className="text-sm font-medium text-red-700 dark:text-red-400">
                        Video generation failed
                    </p>
                    <p className="mt-0.5 text-xs text-red-500 dark:text-red-500/70">
                        {error}
                    </p>
                </div>
            </div>
        );
    }

    // ── Completed state ──
    if (videoUrl) {
        return (
            <div className="mt-4 overflow-hidden rounded-xl border border-gray-200 dark:border-white/10">
                <div className="relative aspect-video w-full bg-black">
                    <video
                        src={videoUrl}
                        controls
                        className="h-full w-full"
                        poster=""
                    >
                        Your browser does not support the video tag.
                    </video>
                </div>
                <div className="flex items-center justify-between border-t border-gray-200 bg-gray-50 px-4 py-2 dark:border-white/10 dark:bg-[#2A2A2A]">
                    <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
                        <FiPlay size={14} className="text-[#5B7B52]" />
                        <span>VidhyaGPT Video</span>
                    </div>
                    <a
                        href={videoUrl}
                        download
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm text-gray-600 transition-colors hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-white/5"
                    >
                        <FiDownload size={14} />
                        Download
                    </a>
                </div>
            </div>
        );
    }

    // ── Processing state — animated progress bar ──
    return (
        <div className="mt-4 rounded-xl border border-gray-200 bg-gray-50 p-4 dark:border-white/10 dark:bg-[#2A2A2A]">
            <div className="flex items-center gap-3">
                <div className="relative">
                    <FiLoader
                        className="animate-spin text-[#5B7B52]"
                        size={20}
                    />
                </div>
                <div className="flex-1">
                    <div className="flex items-center justify-between">
                        <p className="text-sm font-medium text-black dark:text-white">
                            Generating your video...
                        </p>
                        <span className="text-xs font-mono text-gray-500 dark:text-gray-400">
                            {progress}%
                        </span>
                    </div>
                    <p className="mt-0.5 text-xs text-gray-500 dark:text-gray-400">
                        {getStepLabel(progress)}
                    </p>
                </div>
            </div>

            {/* Progress bar */}
            <div className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-gray-200 dark:bg-white/10">
                <div
                    className="h-full rounded-full bg-gradient-to-r from-[#5B7B52] to-[#7BA370] transition-all duration-700 ease-out"
                    style={{ width: `${progress}%` }}
                />
            </div>

            <p className="mt-2 text-center text-[11px] text-gray-400 dark:text-gray-500">
                This usually takes 2–5 minutes. You can keep chatting while it generates.
            </p>
        </div>
    );
}
