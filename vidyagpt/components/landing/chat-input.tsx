import { KeyboardEvent } from "react";
import { FiArrowUp } from "react-icons/fi";

type ChatInputProps = {
    value: string;
    onChange: (value: string) => void;
    onSend: () => void;
};

export function ChatInput({ value, onChange, onSend }: ChatInputProps) {
    const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
        if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            onSend();
        }
    };

    return (
        <div className="w-full max-w-3xl items-end gap-2 rounded-2xl border border-gray-200 bg-white p-2 shadow-sm transition-all focus-within:border-[#5B7B52] focus-within:ring-1 focus-within:ring-[#5B7B52] dark:border-white/10 dark:bg-[#2A2A2A]">
            <textarea
                value={value}
                onChange={(event) => onChange(event.target.value)}
                onKeyDown={onKeyDown}
                placeholder="Type your question here..."
                className="min-h-[56px] max-h-32 w-full resize-none border-none bg-transparent p-3 text-[15px] text-black placeholder-gray-400 outline-none focus:ring-0 dark:text-white dark:placeholder-gray-500"
                rows={1}
            />
            <div className="flex justify-end">
                <button
                    onClick={onSend}
                    disabled={!value.trim()}
                    className="mb-1 mr-1 shrink-0 rounded-full bg-[#5B7B52] p-2 text-white transition-colors hover:bg-opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
                    type="button"
                >
                    <FiArrowUp size={20} />
                </button>
            </div>
        </div>
    );
}
