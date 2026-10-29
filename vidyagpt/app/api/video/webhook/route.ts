import prisma from '@/lib/prisma/prisma';
import { NextRequest, NextResponse } from 'next/server';

export async function POST(req: NextRequest) {
    try {
        const body = await req.json();
        const { jobId, status, videoUrl, error } = body;

        if (!jobId || !status) {
            return NextResponse.json(
                { success: false, error: "Missing jobId or status" },
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

        await prisma.videoJob.update({
            where: { id: jobId },
            data: {
                status: status,
                videoUrl: videoUrl || null,
                errorLog: error || null,
                completedAt: status === "done" || status === "failed" ? new Date() : null,
            }
        });

        return NextResponse.json({ success: true, message: "Webhook processed" });

    } catch (err: any) {
        console.error("[video/webhook] Error:", err);
        return NextResponse.json(
            { success: false, error: "Failed to process webhook" },
            { status: 500 }
        );
    }
}
