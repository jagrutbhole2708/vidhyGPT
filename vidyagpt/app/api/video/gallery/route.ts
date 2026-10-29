import { authOptions } from '@/lib/auth/auth'
import prisma from '@/lib/prisma/prisma'
import { NextRequest, NextResponse } from 'next/server'
import { getServerSession } from 'next-auth'

/**
 * GET /api/video/gallery
 * Fetch all completed videos for the authenticated user.
 */
export async function GET(req: NextRequest) {
    const session = await getServerSession(authOptions)

    if (!session?.user) {
        return NextResponse.json(
            { success: false, error: "Unauthorized" },
            { status: 401 }
        )
    }

    try {
        const videos = await prisma.videoJob.findMany({
            where: {
                status: "done",
                message: {
                    session: {
                        userId: session.user.id
                    }
                }
            },
            include: {
                message: {
                    include: {
                        session: {
                            select: {
                                title: true,
                                subject: true,
                            }
                        }
                    }
                }
            },
            orderBy: {
                createdAt: 'desc'
            }
        })

        const formatted = videos.map(v => {
            // Find the user message that preceded the assistant message
            const sessionTitle = v.message.session?.title || "Untitled";
            return {
                id: v.id,
                title: sessionTitle,
                subject: v.message.session?.subject || "General",
                videoUrl: v.videoUrl,
                createdAt: v.createdAt,
            };
        });

        return NextResponse.json({
            success: true,
            data: formatted
        })
    } catch (err: any) {
        console.error("[video/gallery] Error:", err)
        return NextResponse.json(
            { success: false, error: "Failed to fetch videos" },
            { status: 500 }
        )
    }
}
