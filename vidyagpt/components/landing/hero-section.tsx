import { MdQrCodeScanner } from "react-icons/md";
import { TbSquareRoot } from "react-icons/tb";
import { ChatInput } from "@/components/landing/chat-input";

type HeroSectionProps = {
    activeTab: string;
    setActiveTab: (tab: string) => void;
    inputValue: string;
    setInputValue: (value: string) => void;
    onSend: () => void;
    tabs: string[];
};

export function HeroSection({
    activeTab,
    setActiveTab,
    inputValue,
    setInputValue,
    onSend,
    tabs,
}: HeroSectionProps) {
    return (
        <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col items-center justify-center p-4">
            <div className="mb-3 flex items-center gap-3">
                <div className="rounded-full bg-[#5B7B52] p-1.5 text-white">
                    <TbSquareRoot size={28} />
                </div>
                <h1 className="text-3xl font-medium tracking-tight">
                    VidhyaGPT - Your Personal Tutor
                </h1>
            </div>

            <p className="mb-8 text-[15px] text-gray-500 dark:text-gray-400">
                Get instant homework help from your on-demand AI Tutor
            </p>

            <div className="mb-8 flex gap-2">
                {tabs.map((tab) => (
                    <button
                        key={tab}
                        onClick={() => setActiveTab(tab)}
                        className={`rounded-lg px-5 py-2.5 text-sm font-medium transition-all duration-200 border ${activeTab === tab ? "border-[#5B7B52] bg-[#5B7B52]/10 text-[#5B7B52] shadow-sm dark:border-[#7BA370] dark:bg-[#5B7B52]/15 dark:text-[#7BA370]" : "border-gray-200 bg-white text-gray-600 hover:border-[#5B7B52]/40 hover:bg-[#5B7B52]/5 dark:border-white/10 dark:bg-white/5 dark:text-gray-400 dark:hover:border-[#5B7B52]/40"}`}
                        type="button"
                    >
                        {tab}
                    </button>
                ))}
            </div>

            <ChatInput value={inputValue} onChange={setInputValue} onSend={onSend} />

            {/* <div className="mt-6 flex items-center gap-2 rounded-md border border-gray-200/50 bg-gray-50 px-3 py-1.5 text-xs text-gray-500 dark:border-white/5 dark:bg-white/5 dark:text-gray-400">
                <MdQrCodeScanner size={16} />
                <span>
                    <a href="#" className="font-medium text-[#5B7B52] hover:underline">
                        Download
                    </a>{" "}
                    the VidhyaGPT mobile app to get help on the go!
                </span>
            </div> */}
        </div>
    );
}
