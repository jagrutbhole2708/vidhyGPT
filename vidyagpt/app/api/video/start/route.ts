import { authOptions } from '@/lib/auth/auth'
import prisma from '@/lib/prisma/prisma'
import { NextRequest, NextResponse } from 'next/server'
import { getServerSession } from 'next-auth'

const PYTHON_SERVICE_URL = process.env.PYTHON_SERVICE_URL || "http://localhost:8000"

export async function POST(req: NextRequest) {
    const session = await getServerSession(authOptions)

    if (!session?.user) {
        return NextResponse.json(
            { success: false, error: "Unauthorized" },
            { status: 401 }
        )
    }

    let { question, answer, subject, classLevel, messageId } = await req.json()

    // Normalize "PhysicsGPT" -> "Physics"
    if (subject && subject.endsWith('GPT')) {
        subject = subject.replace('GPT', '');
    }

    if (!question || !answer) {
        return NextResponse.json(
            { success: false, error: "Missing question or answer" },
            { status: 400 }
        )
    }

    try {
        // Create VideoJob in DB (linked to the assistant message)
        const videoJob = await prisma.videoJob.create({
            data: {
                messageId: messageId,
                status: "pending",
            }
        })

        // Call Python service to start video generation
        const res = await fetch(`${PYTHON_SERVICE_URL}/video/create`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                job_id: videoJob.id,
                topic: question,
                answer_context: answer,
                subject: subject || "Science",
                class_level: classLevel || "10",
                board: "CBSE",
            })
        })

        if (!res.ok) {
            // Update job status to failed
            await prisma.videoJob.update({
                where: { id: videoJob.id },
                data: { status: "failed", errorLog: `Python service error: ${res.status}` }
            })
            throw new Error(`Python service returned ${res.status}`)
        }

        const pythonRes = await res.json()

        return NextResponse.json({
            success: true,
            data: {
                jobId: videoJob.id,
                status: "pending",
            }
        })

    } catch (err: any) {
        console.error("[video/start] Error:", err)
        return NextResponse.json(
            { success: false, error: err.message || "Failed to start video generation" },
            { status: 500 }
        )
    }
}
