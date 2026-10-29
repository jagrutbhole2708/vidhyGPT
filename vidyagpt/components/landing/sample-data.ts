import { Question } from "@/components/landing/types";

export const SUBJECT_TABS = ["MathGPT", "PhysicsGPT", "ChemGPT"];

export const SAMPLE_AI_RESPONSE =
    "Newton's First Law of Motion: The Law of Inertia\n\nNewton's First Law of Motion is often called the Law of Inertia. Think of it like this: things like to keep doing whatever they are already doing!\n\nUnderstanding Inertia\nInertia is the special word for this tendency of an object to resist changes in its motion.\n- If a soccer ball is sitting on the grass, it has inertia, and it will sit there forever unless a player kicks it (a force) or the wind pushes it (a force).\n- If you are riding a skateboard and it suddenly hits a rock, your body keeps trying to move forward even though the skateboard stopped. That forward push you feel is your inertia!";

export const SAMPLE_QUESTIONS: Question[] = [
    {
        id: 1,
        text: "According to Newton's First Law, what happens to an object in motion if no external force acts upon it?",
        options: [
            {
                id: "a",
                text: "It will eventually slow down and stop.",
                isCorrect: false,
                explanation:
                    "Friction is an external force that causes things to slow down on Earth.",
            },
            {
                id: "b",
                text: "It will continue in motion with the same speed and in the same direction.",
                isCorrect: true,
                explanation: "Correct! This is the definition of inertia.",
            },
            {
                id: "c",
                text: "It will change its direction but keep the same speed.",
                isCorrect: false,
                explanation: "A change in direction requires an external force.",
            },
            {
                id: "d",
                text: "Its mass will increase.",
                isCorrect: false,
                explanation:
                    "Mass is constant and does not change based on motion in classical mechanics.",
            },
        ],
    },
    {
        id: 2,
        text: "Which of the following is the best everyday example of inertia?",
        options: [
            {
                id: "a",
                text: "A rocket taking off from a launch pad.",
                isCorrect: false,
            },
            {
                id: "b",
                text: "Your body lurching forward when a car suddenly slams on the brakes.",
                isCorrect: true,
                explanation:
                    "Your body wants to keep moving forward at the speed the car was going.",
            },
            { id: "c", text: "A magnet picking up a paperclip.", isCorrect: false },
            { id: "d", text: "An apple falling from a tree.", isCorrect: false },
        ],
    },
];
