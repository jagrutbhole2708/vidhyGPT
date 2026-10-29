"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
import { ChatView } from "@/components/landing/chat-view";
import { TopNav } from "@/components/landing/top-nav";
import { Sidebar } from "@/components/landing/sidebar";
import { Message } from "@/components/landing/types";
import { getPendingPrompt, clearPendingPrompt } from "@/lib/pending-prompt";

type ChatPageProps = {
    sessionId: string;
};

type SessionMeta = {
    id: string;
    title: string | null;
    board: string;
    classLevel: string;
    subject: string;
};

export function ChatPage({ sessionId }: ChatPageProps) {
    const router = useRouter();
    const { data: session } = useSession();

    const [isSidebarOpen, setIsSidebarOpen] = useState(true);
    const [isDarkMode, setIsDarkMode] = useState(true);

    const [messages, setMessages] = useState<Message[]>([]);
    const [inputValue, setInputValue] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const [sessionMeta, setSessionMeta] = useState<SessionMeta | null>(null);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    // Keep a ref to the latest messages so sendMessage always sees current state
    const messagesRef = useRef<Message[]>(messages);
    useEffect(() => {
        messagesRef.current = messages;
    }, [messages]);

    // Dark mode
    useEffect(() => {
        if (isDarkMode) {
            document.documentElement.classList.add("dark");
        } else {
            document.documentElement.classList.remove("dark");
        }
    }, [isDarkMode]);

    // Auto-scroll
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

    // Refs for pending prompt flow
    const hasSentPending = useRef(false);
    const sendMessageRef = useRef<((prompt: string) => Promise<void>) | null>(null);

    // ── Single init effect: load messages THEN handle pending prompt ──
    // This prevents the race condition where loadMessages would overwrite
    // the pending prompt's "Thinking..." message with an empty array.
    useEffect(() => {
        let cancelled = false;

        async function init() {
            // Step 1: Load existing messages from DB
            let loadedMessages: Message[] = [];
            try {
                const res = await fetch(`/api/chat/${sessionId}/messages`);
                if (res.ok) {
                    const json = await res.json();
                    if (json.success && !cancelled) {
                        setSessionMeta(json.data.session);
                        loadedMessages = json.data.messages.map(
                            (m: any) => ({
                                id: m.id,
                                role: m.role === "assistant" ? "ai" : "user",
                                content: m.content,
                                isTyping: false,
                                showActions: m.role === "assistant",
                                messageId: m.id,
                                videoJobId: m.videoJob?.id || undefined,
                                videoUrl: m.videoJob?.videoUrl || undefined,
                                videoStatus: m.videoJob ? (m.videoJob.status as Message["videoStatus"]) : undefined,
                            })
                        );
                    }
                }
            } catch (err) {
                console.error("Failed to load messages:", err);
            }

            if (cancelled) return;

            // Step 2: Check for pending prompt from landing page redirect
            const pending = getPendingPrompt();
            if (pending && !hasSentPending.current) {
                hasSentPending.current = true;
                clearPendingPrompt();

                const userMsg: Message = {
                    id: `pending-user-${sessionId}`,
                    role: "user",
                    content: pending,
                };
                const thinkingMsg: Message = {
                    id: `pending-thinking-${sessionId}`,
                    role: "ai",
                    content: "Thinking...",
                    isTyping: true,
                };

                // Set loaded + pending messages atomically — no race condition
                setMessages([...loadedMessages, userMsg, thinkingMsg]);

                // Wait for sendMessage ref to be populated, then fire the API call
                const tryCall = (attempt: number) => {
                    if (sendMessageRef.current) {
                        sendMessageRef.current(pending);
                    } else if (attempt < 30) {
                        setTimeout(() => tryCall(attempt + 1), 200);
                    }
                };
                setTimeout(() => tryCall(0), 100);
            } else {
                // No pending prompt — just show loaded messages
                setMessages(loadedMessages);
            }
        }

        init();

        return () => { cancelled = true; };
    }, [sessionId]);

    const handleTypingComplete = useCallback((messageId: string) => {
        setMessages((prev) =>
            prev.map((m) =>
                m.id === messageId ? { ...m, isTyping: false, showActions: true } : m
            )
        );
    }, []);

    // ── Core send logic (reusable) ──
    // Uses messagesRef instead of messages in closure to avoid stale closure bug
    const sendMessage = useCallback(async (prompt: string) => {
        if (!prompt.trim()) return;

        if (!session) {
            router.push("/login?callbackUrl=/chat/" + sessionId);
            return;
        }

        setInputValue("");
        setIsLoading(true);

        // Use the ref to get current messages (avoids stale closure)
        const currentMessages = messagesRef.current;

        // Check if a "Thinking..." message already exists (from pending prompt flow)
        const existingThinking = currentMessages.find(
            (m) => m.role === "ai" && m.content === "Thinking..."
        );
        let thinkingId: string;

        if (existingThinking) {
            // Pending prompt flow already added user message + thinking
            thinkingId = existingThinking.id;
        } else {
            // Normal flow — add user message + thinking indicator
            const userMessage: Message = {
                id: Date.now().toString(),
                role: "user",
                content: prompt,
            };
            thinkingId = (Date.now() + 1).toString();

            setMessages((prev) => [
                ...prev,
                userMessage,
                { id: thinkingId, role: "ai", content: "Thinking...", isTyping: true },
            ]);
        }

        try {
            const res = await fetch("/api/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    question: prompt,
                    sessionId,
                    board: sessionMeta?.board || "CBSE",
                    classLevel: sessionMeta?.classLevel || "10",
                    subject: "auto",
                }),
            });

            const json = await res.json();
            console.log("Chat API response:", json);

            if (!res.ok || !json.success) {
                throw new Error(json?.error || `API returned ${res.status}`);
            }

            const answerText = json.data.answer || "I found relevant content but couldn't generate a detailed answer. Please try rephrasing your question.";

            // Replace the thinking message with the actual answer
            setMessages((prev) =>
                prev.map((m) =>
                    m.id === thinkingId
                        ? {
                              ...m,
                              content: answerText,
                              isTyping: false,
                              showActions: true,
                              messageId: json.data.messageId,
                          }
                        : m
                )
            );

            // Update session meta title locally if server generated one
            if (json.data.generatedTitle) {
                setSessionMeta((prev) =>
                    prev ? { ...prev, title: json.data.generatedTitle } : prev
                );
            }
        } catch (err: any) {
            console.error("Chat send error:", err);
            setMessages((prev) =>
                prev.map((m) =>
                    m.id === thinkingId
                        ? {
                              ...m,
                              content: `Sorry, I encountered an error: ${err.message}. Please try again.`,
                              isTyping: false,
                              showActions: false,
                          }
                        : m
                )
            );
        } finally {
            setIsLoading(false);
        }
    }, [session, sessionId, sessionMeta, router]);

    // Keep the ref in sync so the pending-prompt useEffect can call the latest version
    useEffect(() => {
        sendMessageRef.current = sendMessage;
    }, [sendMessage]);

    // ── Wrapper for the input box ──
    const handleSend = async () => {
        const prompt = inputValue.trim();
        if (!prompt || isLoading) return;
        await sendMessage(prompt);
    };

    // ── Video handlers ──
    const handleCreateVideo = useCallback(
        async (messageId: string) => {
            const currentMessages = messagesRef.current;
            const msg = currentMessages.find((m) => m.id === messageId);
            if (!msg || msg.videoJobId) return;

            const idx = currentMessages.findIndex((m) => m.id === messageId);
            const userMsg = idx > 0 ? currentMessages[idx - 1] : null;
            const question = userMsg?.role === "user" ? userMsg.content : "Explain this topic";

            try {
                const res = await fetch("/api/video/start", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        question,
                        answer: msg.content,
                        subject: sessionMeta?.subject || "Science",
                        classLevel: sessionMeta?.classLevel || "10",
                        messageId: msg.messageId,
                    }),
                });

                if (!res.ok) throw new Error(`Video start failed: ${res.status}`);
                const json = await res.json();
                if (!json.success) throw new Error(json.error || "Failed to start video");

                setMessages((prev) =>
                    prev.map((m) =>
                        m.id === messageId
                            ? { ...m, videoJobId: json.data.jobId, videoStatus: "pending" }
                            : m
                    )
                );
            } catch (err: any) {
                console.error("Video start error:", err);
            }
        },
        [sessionMeta]
    );

    const handleVideoComplete = useCallback((messageId: string, videoUrl: string) => {
        setMessages((prev) =>
            prev.map((m) => (m.id === messageId ? { ...m, videoUrl, videoStatus: "done" } : m))
        );
    }, []);

    const handleVideoFailed = useCallback((messageId: string, _error: string) => {
        setMessages((prev) =>
            prev.map((m) => (m.id === messageId ? { ...m, videoStatus: "failed" } : m))
        );
    }, []);

    // ── Video Polling ──
    useEffect(() => {
        const pendingVideos = messages.filter(m => m.videoJobId && m.videoStatus === "pending");
        if (pendingVideos.length === 0) return;

        const interval = setInterval(async () => {
            for (const msg of pendingVideos) {
                try {
                    const res = await fetch(`/api/video/status?jobId=${msg.videoJobId}`);
                    if (!res.ok) continue;
                    const json = await res.json();
                    if (!json.success) continue;

                    const status = json.data.status;
                    if (status === "done" && json.data.videoUrl) {
                        handleVideoComplete(msg.id, json.data.videoUrl);
                    } else if (status === "failed") {
                        handleVideoFailed(msg.id, json.data.errorLog || "Video generation failed");
                    }
                } catch (err) {
                    console.error("Polling error for job", msg.videoJobId, err);
                }
            }
        }, 5000);

        return () => clearInterval(interval);
    }, [messages, handleVideoComplete, handleVideoFailed]);

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

                    <ChatView
                        messages={messages}
                        inputValue={inputValue}
                        setInputValue={setInputValue}
                        handleSend={handleSend}
                        handleTypingComplete={handleTypingComplete}
                        handleCreateVideo={handleCreateVideo}
                        handleVideoComplete={handleVideoComplete}
                        handleVideoFailed={handleVideoFailed}
                        messagesEndRef={messagesEndRef}
                    />
                </div>
            </main>
        </div>
    );
}
