import { authOptions } from '@/lib/auth/auth'
import prisma from '@/lib/prisma/prisma'
import { NextRequest, NextResponse } from 'next/server'
import { getServerSession } from 'next-auth'

const PYTHON_SERVICE_URL = process.env.PYTHON_SERVICE_URL || "http://localhost:8000"

/**
 * Generate a short, descriptive title from a user's question.
 * e.g. "explain me swartz reaction" → "Explanation of Swartz Reaction"
 */
function generateTitle(question: string): string {
    const q = question.trim();

    // Remove common question prefixes
    const prefixes = [
        /^(can you |could you |please |pls |hey |hi |hello |yo )/i,
        /^(explain|tell|describe|what is|what are|how does|how do|how to|define|give me|show me|help me with|help me understand|write about|teach me|elaborate on)\s+(me\s+)?(about\s+)?(the\s+)?/i,
    ];

    let cleaned = q;
    for (const prefix of prefixes) {
        cleaned = cleaned.replace(prefix, '');
    }

    // Remove trailing punctuation
    cleaned = cleaned.replace(/[?.!]+$/, '').trim();

    // If too short after cleaning, use original
    if (cleaned.length < 3) {
        cleaned = q.replace(/[?.!]+$/, '').trim();
    }

    // Capitalize first letter of each major word
    const titleCased = cleaned
        .split(' ')
        .map((word, idx) => {
            const lower = word.toLowerCase();
            // Don't capitalize small words unless first
            if (idx > 0 && ['a', 'an', 'the', 'of', 'in', 'on', 'at', 'to', 'for', 'and', 'or', 'but', 'is', 'are', 'was', 'were', 'me', 'my', 'ki'].includes(lower)) {
                return lower;
            }
            return word.charAt(0).toUpperCase() + word.slice(1).toLowerCase();
        })
        .join(' ');

    // Truncate to reasonable length
    const maxLen = 50;
    if (titleCased.length > maxLen) {
        return titleCased.slice(0, maxLen).replace(/\s+\S*$/, '...');
    }

    return titleCased;
}

export async function POST(req: NextRequest) {
    const session = await getServerSession(authOptions)

    if (!session?.user) {
        return NextResponse.json(
            {
                success: false,
                error: "Unauthorized Request"
            },
            {
                status: 401
            }
        )
    }

    const body = await req.json();
    const { question, sessionId, board, classLevel } = body;
    let { subject } = body;

    // Normalize "PhysicsGPT" -> "Physics", etc.
    if (subject && subject.endsWith('GPT')) {
        subject = subject.replace('GPT', '');
    }

    console.log("Chat Request:", { question, sessionId, board, classLevel, subject });

    if (!question || !sessionId) {
        return NextResponse.json(
            {
                success: false,
                error: "Missing question or sessionId"
            },
            {
                status: 400
            }
        )
    }

    // Verify session belongs to user
    const chatSession = await prisma.chatSession.findFirst({
        where: {
            id: sessionId,
            userId: session.user.id
        }
    });

    if (!chatSession) {
        return NextResponse.json(
            {
                success: false,
                error: "Session not found"
            },
            {
                status: 404
            }
        )
    }

    // Save user message
    await prisma.message.create({
        data: {
            sessionId,
            role: "user",
            content: question
        }
    })

    let pythonResponse;

    try {
        const res = await fetch(`${PYTHON_SERVICE_URL}/generate`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                question,
                board: board || chatSession.board,
                class_level: classLevel || chatSession.classLevel,
                subject: subject || chatSession.subject,
                top_k: 3
            })
        });

        if (!res.ok) {
            const errData = await res.json().catch(() => null);
            const details = errData?.detail || res.statusText;
            throw new Error(`Python service error (${res.status}): ${details}`);
        }

        pythonResponse = await res.json();
        console.log("Python Response (parsed):", JSON.stringify(pythonResponse).slice(0, 500));

    } catch (err: any) {
        console.error("API error during /generate:", err.message || err);
        return NextResponse.json(
            {
                success: false,
                error: err.message || "Failed to generate answer"
            },
            {
                status: 500
            }
        )
    }

    // Save assistant message with citations
    const assistantMessage = await prisma.message.create({
        data: {
            sessionId,
            role: "assistant",
            content: pythonResponse.answer,
            citations: pythonResponse.citations || [],
        }
    })

    // Update session title from first message if not set (or still default "New Chat")
    let generatedTitle: string | null = null;
    if (!chatSession.title || chatSession.title === "New Chat") {
        generatedTitle = generateTitle(question);
        await prisma.chatSession.update({
            where: {
                id: sessionId
            },
            data: {
                title: generatedTitle
            }
        })
    }

    return NextResponse.json({
        success: true,
        message: "Answer generated successfully",
        data: {
            messageId: assistantMessage.id,
            answer: pythonResponse.answer,
            citations: pythonResponse.citations,
            detectedSubject: pythonResponse.detected_subject || "general",
            hasFormula: pythonResponse.has_formula || false,
            hasDiagramNeed: pythonResponse.has_diagram_need || false,
            suggestedDiagramType: pythonResponse.suggested_diagram_type || null,
            hasVideo: true,
            generatedTitle,  // Send the generated title back to the client
        }
    })
}
