import prisma from '@/lib/prisma/prisma'
import { NextRequest, NextResponse } from 'next/server'

/**
 * GET /api/video/gallery/examples
 * Fetch featured/best example videos (public, no auth required).
 */
export async function GET(req: NextRequest) {
    try {
        const examples = await prisma.exampleVideo.findMany({
            where: {
                featured: true,
            },
            orderBy: {
                createdAt: 'desc'
            }
        })

        return NextResponse.json({
            success: true,
            data: examples.map(v => ({
                id: v.id,
                title: v.title,
                description: v.description,
                subject: v.subject,
                videoUrl: v.videoUrl,
                thumbnailUrl: v.thumbnailUrl,
                createdAt: v.createdAt,
            }))
        })
    } catch (err: any) {
        console.error("[video/gallery/examples] Error:", err)
        return NextResponse.json(
            { success: false, error: "Failed to fetch example videos" },
            { status: 500 }
        )
    }
}
