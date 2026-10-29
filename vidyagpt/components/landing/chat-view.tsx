import { RefObject } from "react";
import { ChatInput } from "@/components/landing/chat-input";
import { MessageBubble } from "@/components/landing/message-bubble";
import { Message } from "@/components/landing/types";

type ChatViewProps = {
    messages: Message[];
    inputValue: string;
    setInputValue: (value: string) => void;
    handleSend: () => void;
    handleTypingComplete: (id: string) => void;
    handleCreateVideo: (messageId: string) => void;
    handleVideoComplete: (messageId: string, videoUrl: string) => void;
    handleVideoFailed: (messageId: string, error: string) => void;
    messagesEndRef: RefObject<HTMLDivElement | null>;
};

export function ChatView({
    messages,
    inputValue,
    setInputValue,
    handleSend,
    handleTypingComplete,
    handleCreateVideo,
    handleVideoComplete,
    handleVideoFailed,
    messagesEndRef,
}: ChatViewProps) {
    // Find the last assistant message ID to only enable generate video on it
    const lastAssistantId = [...messages].reverse().find(m => m.role === "ai" && m.content !== "Thinking...")?.id;

    return (
        <div className="relative flex h-full w-full flex-1 flex-col pt-16">
            <div className="w-full flex-1 overflow-y-auto scroll-smooth pb-40">
                <div className="mx-auto w-full max-w-4xl space-y-8 p-4">
                    {messages.map((message) => (
                        <MessageBubble
                            key={message.id}
                            message={message}
                            isLatestAssistant={message.id === lastAssistantId}
                            onTypingComplete={() => handleTypingComplete(message.id)}
                            onCreateVideo={() => handleCreateVideo(message.id)}
                            onVideoComplete={(url) => handleVideoComplete(message.id, url)}
                            onVideoFailed={(err) => handleVideoFailed(message.id, err)}
                        />
                    ))}

                    <div ref={messagesEndRef} />
                </div>
            </div>

            <div className="pointer-events-none absolute right-0 bottom-0 left-0 bg-gradient-to-t from-white via-white to-transparent p-4 pt-10 dark:from-[#212121] dark:via-[#212121]">
                <div className="pointer-events-auto mx-auto flex max-w-3xl flex-col items-center">
                    <ChatInput value={inputValue} onChange={setInputValue} onSend={handleSend} />
                    <p className="mt-3 text-xs text-gray-400 dark:text-gray-500">
                        VidhyaGPT can make mistakes. Check important info.
                    </p>
                </div>
            </div>
        </div>
    );
}
