import { getAuthSession } from '@/helper/authHelper'
import prisma from "@/lib/prisma/prisma";
import { NextRequest, NextResponse } from 'next/server'

export async function POST(req: NextRequest) {
    const session = await getAuthSession()

    if (!session?.user) {
        return NextResponse.json(
            {
                success: false,
                message: "Unauthorized"
            },
            {
                status: 401
            }
        )
    }

    const { board, classLevel, subject } = await req.json()

    if (!board || !classLevel || !subject) {
        return NextResponse.json(
            {
                success: false,
                message: "Missing board, classLevel, or subject"
            },
            {
                status: 400
            }
        )
    }

    const chatSession = await prisma.chatSession.create({
        data: {
            userId: session.user.id,
            board,
            classLevel,
            subject,
        }
    })

    return NextResponse.json({
        success: true,
        message: "Session created successfully",
        data: {
            sessionId: chatSession.id
        }
    })
}

export async function GET(req: NextRequest) {
    const session = await getAuthSession();

    if (!session?.user) {
        return NextResponse.json(
            {
                success: false,
                message: "Unauthorized"
            },
            {
                status: 401
            }
        )
    }

    const sessions = await prisma.chatSession.findMany({
        where: {
            userId: session.user.id
        },
        select: {
            id: true,
            title: true,
            board: true,
            classLevel: true,
            subject: true,
            updatedAt: true
        }
    })

    return NextResponse.json({
        success: true,
        message: "Sessions fetched successfully",
        data: sessions
    })
}