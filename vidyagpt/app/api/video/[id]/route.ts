import { authOptions } from '@/lib/auth/auth'
import prisma from '@/lib/prisma/prisma'
import { NextRequest, NextResponse } from 'next/server'
import { getServerSession } from 'next-auth'

const PYTHON_SERVICE_URL = process.env.PYTHON_SERVICE_URL || "http://localhost:8000"

export async function GET(
    req: NextRequest,
    { params }: { params: Promise<{ id: string }> }
) {
    const session = await getServerSession(authOptions)

    if (!session?.user) {
        return NextResponse.json(
            { success: false, error: "Unauthorized" },
            { status: 401 }
        )
    }

    const { id: jobId } = await params

    try {
        // First check Python service for live progress updates
        const pythonRes = await fetch(`${PYTHON_SERVICE_URL}/video/status/${jobId}`)

        if (pythonRes.ok) {
            const pythonJob = await pythonRes.json()

            // If Python says it's done, update our DB
            if (pythonJob.status === "done" && pythonJob.video_url) {
                await prisma.videoJob.update({
                    where: { id: jobId },
                    data: {
                        status: "done",
                        videoUrl: pythonJob.video_url,
                        completedAt: new Date(),
                    }
                })

                return NextResponse.json({
                    success: true,
                    data: {
                        jobId,
                        status: "done",
                        progress: 100,
                        videoUrl: pythonJob.video_url,
                    }
                })
            }

            if (pythonJob.status === "failed") {
                await prisma.videoJob.update({
                    where: { id: jobId },
                    data: {
                        status: "failed",
                        errorLog: pythonJob.error || "Unknown error",
                    }
                })

                return NextResponse.json({
                    success: true,
                    data: {
                        jobId,
                        status: "failed",
                        progress: pythonJob.progress || 0,
                        error: pythonJob.error,
                    }
                })
            }

            // Still processing — return progress
            return NextResponse.json({
                success: true,
                data: {
                    jobId,
                    status: pythonJob.status || "processing",
                    progress: pythonJob.progress || 0,
                }
            })
        }

        // Python service doesn't know about this job — check DB
        const dbJob = await prisma.videoJob.findUnique({
            where: { id: jobId }
        })

        if (!dbJob) {
            return NextResponse.json(
                { success: false, error: "Job not found" },
                { status: 404 }
            )
        }

        return NextResponse.json({
            success: true,
            data: {
                jobId: dbJob.id,
                status: dbJob.status,
                progress: dbJob.status === "done" ? 100 : 0,
                videoUrl: dbJob.videoUrl,
                error: dbJob.errorLog,
            }
        })

    } catch (err: any) {
        console.error("[video/poll] Error:", err)
        return NextResponse.json(
            { success: false, error: "Failed to check job status" },
            { status: 500 }
        )
    }
}
