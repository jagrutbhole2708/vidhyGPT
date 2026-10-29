export type Message = {
    id: string;
    role: "user" | "ai";
    content: string;
    isTyping?: boolean;
    showActions?: boolean;
    messageId?: string;        // DB message ID (for linking video jobs)
    videoJobId?: string;       // active video job ID (for polling)
    videoUrl?: string;         // completed video URL
    videoStatus?: "pending" | "processing" | "done" | "failed";
};

export type PracticeTestState = "idle" | "loading" | "active" | "completed";

export type Question = {
    id: number;
    text: string;
    options: { id: string; text: string; isCorrect: boolean; explanation?: string }[];
};

export type VideoJobData = {
    jobId: string;
    status: "pending" | "processing" | "done" | "failed";
    progress: number;
    videoUrl?: string;
    error?: string;
};
