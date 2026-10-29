import { FiCheck, FiCheckSquare, FiRefreshCw, FiX } from "react-icons/fi";
import { PracticeTestState, Question } from "@/components/landing/types";

type PracticeTestPanelProps = {
    testState: PracticeTestState;
    testTitle?: string;
    sampleQuestions: Question[];
    currentQuestionIndex: number;
    selectedAnswers: Record<number, string>;
    showExplanation: Record<number, boolean>;
    setTestState: (state: PracticeTestState) => void;
    onAnswerSelect: (questionId: number, optionId: string) => void;
    onNextQuestion: () => void;
    onRetake: () => void;
};

export function PracticeTestPanel({
    testState,
    testTitle,
    sampleQuestions,
    currentQuestionIndex,
    selectedAnswers,
    showExplanation,
    setTestState,
    onAnswerSelect,
    onNextQuestion,
    onRetake,
}: PracticeTestPanelProps) {
    if (testState === "idle") return null;

    const displayTitle = testTitle || "Practice Test";

    const calculateScore = () => {
        let correct = 0;
        Object.entries(selectedAnswers).forEach(([questionId, optionId]) => {
            const question = sampleQuestions.find((item) => item.id === Number(questionId));
            if (question?.options.find((option) => option.id === optionId)?.isCorrect) {
                correct += 1;
            }
        });

        return {
            correct,
            total: sampleQuestions.length,
        };
    };

    const score = calculateScore();
    const question = sampleQuestions[currentQuestionIndex];

    return (
        <div className="flex h-full w-1/2 flex-col bg-gray-50 transition-all duration-300 dark:bg-[#1A1A1A]">
            <div className="flex items-start justify-between border-b border-gray-200 p-6 dark:border-white/10">
                <div>
                    <h2 className="mb-2 text-xl font-semibold">{displayTitle}</h2>
                    {testState === "loading" ? (
                        <p className="text-sm text-gray-500">Generating questions...</p>
                    ) : null}
                    {testState === "active" ? (
                        <p className="text-sm text-gray-500">Let&apos;s start!</p>
                    ) : null}
                    {testState === "completed" ? (
                        <p className="text-sm text-gray-500">Test completed</p>
                    ) : null}

                    {testState === "active" || testState === "completed" ? (
                        <div className="mt-4">
                            <div className="mb-2 flex gap-2">
                                {sampleQuestions.map((_, index) => (
                                    <div
                                        key={index}
                                        className={`h-1 flex-1 rounded-full ${index <= currentQuestionIndex ? "bg-[#5B7B52]" : "bg-gray-200 dark:bg-white/10"}`}
                                    />
                                ))}
                            </div>

                            {testState === "completed" ? (
                                <div className="mt-4">
                                    <p className="text-sm">
                                        You got{" "}
                                        <span className="font-bold text-[#5B7B52]">{score.correct}</span>{" "}
                                        answers correct and{" "}
                                        <span className="font-bold text-red-500">
                                            {score.total - score.correct}
                                        </span>{" "}
                                        wrong
                                    </p>
                                    <p className="mt-1 text-sm">
                                        Test Score:{" "}
                                        <span className="font-bold text-[#5B7B52]">
                                            {score.total > 0 ? Math.round((score.correct / score.total) * 100) : 0}%
                                        </span>
                                    </p>
                                </div>
                            ) : null}
                        </div>
                    ) : null}
                </div>

                <button
                    onClick={() => setTestState("idle")}
                    className="text-gray-400 transition-colors hover:text-gray-600 dark:hover:text-white"
                    type="button"
                >
                    <FiX size={24} />
                </button>
            </div>

            <div className="flex-1 overflow-y-auto p-6">
                {testState === "loading" ? (
                    <div className="flex h-full items-center justify-center">
                        <div className="h-12 w-12 animate-spin rounded-full border-b-2 border-[#5B7B52]"></div>
                    </div>
                ) : null}

                {testState === "active" && question ? (
                    <div className="mx-auto max-w-xl">
                        <div className="mb-6 flex justify-between text-sm text-gray-500">
                            <span>
                                Question {currentQuestionIndex + 1} of {sampleQuestions.length}
                            </span>
                        </div>

                        <h3 className="mb-8 text-lg">{question.text}</h3>

                        <div className="space-y-3">
                            {question.options.map((option) => {
                                const isSelected = selectedAnswers[question.id] === option.id;
                                const showResult = showExplanation[question.id];

                                let optionClass =
                                    "border-gray-200 hover:bg-gray-100 dark:border-white/10 dark:hover:bg-white/5";
                                let icon = null;

                                if (showResult) {
                                    if (option.isCorrect) {
                                        optionClass =
                                            "border-[#5B7B52] bg-[#5B7B52]/10 dark:bg-[#5B7B52]/20";
                                        icon = <FiCheck className="text-[#5B7B52]" />;
                                    } else if (isSelected) {
                                        optionClass = "border-red-500 bg-red-500/10 dark:bg-red-500/20";
                                        icon = <FiX className="text-red-500" />;
                                    } else {
                                        optionClass = "border-gray-200 opacity-50 dark:border-white/10";
                                    }
                                } else if (isSelected) {
                                    optionClass = "border-[#5B7B52] bg-[#5B7B52]/5";
                                }

                                return (
                                    <button
                                        key={option.id}
                                        onClick={() => onAnswerSelect(question.id, option.id)}
                                        disabled={showResult}
                                        className={`flex w-full items-start gap-4 rounded-xl border p-4 text-left transition-all ${optionClass}`}
                                        type="button"
                                    >
                                        <div
                                            className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border ${showResult && (option.isCorrect || isSelected) ? "border-transparent" : "border-gray-400 dark:border-gray-500"}`}
                                        >
                                            {icon}
                                        </div>
                                        <div>
                                            <p>{option.text}</p>
                                            {showResult &&
                                            (option.isCorrect || isSelected) &&
                                            option.explanation ? (
                                                <p
                                                    className={`mt-2 text-sm ${option.isCorrect ? "text-[#5B7B52]" : "text-red-500"}`}
                                                >
                                                    {option.explanation}
                                                </p>
                                            ) : null}
                                        </div>
                                    </button>
                                );
                            })}
                        </div>

                        {showExplanation[question.id] ? (
                            <div className="mt-8">
                                <button
                                    onClick={onNextQuestion}
                                    className="rounded-lg bg-[#5B7B52] px-6 py-2.5 font-medium text-white transition-colors hover:bg-opacity-90"
                                    type="button"
                                >
                                    {currentQuestionIndex < sampleQuestions.length - 1
                                        ? "Next Question"
                                        : "Finish Test"}
                                </button>
                            </div>
                        ) : null}
                    </div>
                ) : null}

                {testState === "completed" ? (
                    <div className="flex h-full flex-col items-center justify-center text-center">
                        <div className="mb-6 rounded-full bg-[#5B7B52] p-4 text-white">
                            <FiCheckSquare size={48} />
                        </div>
                        <h3 className="mb-2 text-2xl font-bold">Test Completed!</h3>
                        <p className="mb-8 text-gray-500 dark:text-gray-400">
                            You&apos;ve finished the practice test.
                        </p>
                        <button
                            onClick={onRetake}
                            className="flex items-center gap-2 rounded-lg border border-gray-300 bg-transparent px-6 py-2.5 font-medium transition-colors hover:bg-gray-100 dark:border-gray-600 dark:hover:bg-white/5"
                            type="button"
                        >
                            <FiRefreshCw />
                            Retake Test
                        </button>
                    </div>
                ) : null}
            </div>
        </div>
    );
}
