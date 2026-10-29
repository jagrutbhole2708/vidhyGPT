"use client";

import ReactMarkdown from "react-markdown";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import "katex/dist/katex.min.css";

type AssistantMessageProps = {
    content: string;
};

export function AssistantMessage({ content }: AssistantMessageProps) {
    return (
        <div
            className="
                prose prose-sm dark:prose-invert max-w-none
                prose-headings:font-semibold
                prose-h2:text-xl prose-h2:mt-6 prose-h2:mb-2 prose-h2:text-black dark:prose-h2:text-white
                prose-h3:text-base prose-h3:mt-4 prose-h3:mb-1 prose-h3:text-black dark:prose-h3:text-white
                prose-p:leading-relaxed prose-p:my-2 prose-p:text-black dark:prose-p:text-white
                prose-li:my-0.5 prose-ul:my-2 prose-ol:my-2
                prose-strong:font-semibold prose-strong:text-black dark:prose-strong:text-white
                prose-blockquote:border-l-[#5B7B52] prose-blockquote:bg-gray-50 dark:prose-blockquote:bg-white/5
                prose-blockquote:px-4 prose-blockquote:py-1 prose-blockquote:rounded-r-lg
                prose-code:bg-gray-100 dark:prose-code:bg-white/10 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded
                prose-code:text-sm prose-code:font-mono
            "
        >
            <ReactMarkdown
                remarkPlugins={[remarkMath]}
                rehypePlugins={[rehypeKatex]}
            >
                {content}
            </ReactMarkdown>
        </div>
    );
}
