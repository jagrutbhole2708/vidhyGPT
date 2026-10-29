import prisma from '@/lib/prisma/prisma';
import { NextRequest, NextResponse } from 'next/server';

export async function GET(req: NextRequest) {
    try {
        const url = new URL(req.url);
        const jobId = url.searchParams.get("jobId");

        if (!jobId) {
            return NextResponse.json(
                { success: false, error: "Missing jobId parameter" },
                { status: 400 }
            );
        }

        const videoJob = await prisma.videoJob.findUnique({
            where: { id: jobId }
        });

        if (!videoJob) {
            return NextResponse.json(
                { success: false, error: "Job not found" },
                { status: 404 }
            );
        }

        return NextResponse.json({
            success: true,
            data: {
                id: videoJob.id,
                status: videoJob.status,
                videoUrl: videoJob.videoUrl,
                errorLog: videoJob.errorLog,
            }
        });

    } catch (err: any) {
        console.error("[video/status] Error:", err);
        return NextResponse.json(
            { success: false, error: "Failed to get video status" },
            { status: 500 }
        );
    }
}
