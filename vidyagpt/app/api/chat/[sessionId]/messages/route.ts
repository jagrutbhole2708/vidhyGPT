import { authOptions } from '@/lib/auth/auth'
import prisma from '@/lib/prisma/prisma'
import { NextRequest, NextResponse } from 'next/server'
import { getServerSession } from 'next-auth'

/**
 * GET /api/chat/[sessionId]/messages
 * Fetch all messages for a given chat session.
 */
export async function GET(
    req: NextRequest,
    { params }: { params: Promise<{ sessionId: string }> }
) {
    const session = await getServerSession(authOptions)

    if (!session?.user) {
        return NextResponse.json(
            { success: false, error: "Unauthorized" },
            { status: 401 }
        )
    }

    const { sessionId } = await params

    // Verify session belongs to user
    const chatSession = await prisma.chatSession.findFirst({
        where: {
            id: sessionId,
            userId: session.user.id
        },
        include: {
            messages: {
                orderBy: { createdAt: 'asc' },
                include: {
                    videoJob: true
                }
            }
        }
    })

    if (!chatSession) {
        return NextResponse.json(
            { success: false, error: "Session not found" },
            { status: 404 }
        )
    }

    return NextResponse.json({
        success: true,
        data: {
            session: {
                id: chatSession.id,
                title: chatSession.title,
                board: chatSession.board,
                classLevel: chatSession.classLevel,
                subject: chatSession.subject,
            },
            messages: chatSession.messages.map(m => ({
                id: m.id,
                role: m.role,
                content: m.content,
                citations: m.citations,
                createdAt: m.createdAt,
                videoJob: m.videoJob ? {
                    id: m.videoJob.id,
                    status: m.videoJob.status,
                    videoUrl: m.videoJob.videoUrl,
                } : null,
            }))
        }
    })
}
