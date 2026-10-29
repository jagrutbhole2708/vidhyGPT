import { ReactNode } from "react";

type NavItemProps = {
    icon: ReactNode;
    label: string;
    isOpen: boolean;
    onClick?: () => void;
};

export function NavItem({ icon, label, isOpen, onClick }: NavItemProps) {
    return (
        <button
            onClick={onClick}
            className={`flex w-full items-center rounded-lg p-2.5 text-gray-700 transition-colors hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-white/5 ${isOpen ? "justify-start" : "justify-center"}`}
            type="button"
        >
            <span className="shrink-0">{icon}</span>
            <span
                className={`overflow-hidden whitespace-nowrap text-sm font-medium transition-all duration-300 ${isOpen ? "ml-3 max-w-[200px] opacity-100" : "ml-0 max-w-0 opacity-0"}`}
            >
                {label}
            </span>
        </button>
    );
}
