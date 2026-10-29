import { ChatPage } from "@/components/chat/chat-page";

type Props = {
    params: Promise<{ sessionId: string }>;
};

export default async function ChatSessionPage({ params }: Props) {
    const { sessionId } = await params;
    return <ChatPage sessionId={sessionId} />;
}
