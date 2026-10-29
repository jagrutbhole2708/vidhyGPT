const PENDING_PROMPT_KEY = "VidhyaGPT:pendingPrompt";

export function savePendingPrompt(prompt: string) {
    if (typeof window === "undefined") return;
    window.localStorage.setItem(PENDING_PROMPT_KEY, prompt);
}

export function getPendingPrompt() {
    if (typeof window === "undefined") return "";
    return window.localStorage.getItem(PENDING_PROMPT_KEY) ?? "";
}

export function clearPendingPrompt() {
    if (typeof window === "undefined") return;
    window.localStorage.removeItem(PENDING_PROMPT_KEY);
}
