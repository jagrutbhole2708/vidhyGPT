import { useEffect, useRef, useState } from "react";
import { AssistantMessage } from "@/components/chat/AssistantMessage";

type TypingEffectProps = {
    content: string;
    speed?: number;
    onComplete?: () => void;
};

export function TypingEffect({ content, speed = 10, onComplete }: TypingEffectProps) {
    const [displayed, setDisplayed] = useState("");
    // Store onComplete in a ref to avoid re-triggering the effect on every render
    const onCompleteRef = useRef(onComplete);
    onCompleteRef.current = onComplete;

    useEffect(() => {
        setDisplayed("");
        let i = 0;
        const timer = setInterval(() => {
            setDisplayed(content.slice(0, i + 1));
            i += 1;

            if (i >= content.length) {
                clearInterval(timer);
                onCompleteRef.current?.();
            }
        }, speed);

        return () => clearInterval(timer);
    }, [content, speed]);

    // Render markdown during typing so LaTeX, headings, bold etc. look correct
    return <AssistantMessage content={displayed} />;
}
