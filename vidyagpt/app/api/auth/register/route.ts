import prisma from "@/lib/prisma/prisma";
import bcrypt from "bcryptjs";
import { NextRequest, NextResponse } from "next/server";
import { registerSchemaRequest } from "./registerSchema";

export async function POST(req: NextRequest) {
    try {
        const body = await req.json();

        const validationResult = registerSchemaRequest.safeParse(body);

        if (!validationResult.success) {
            return NextResponse.json(
                {
                    success: false,
                    message: validationResult.error.issues[0]?.message || "Invalid request body",
                },
                {
                    status: 400,
                }
            );
        }

        const { name, email, password } = validationResult.data;

        const existinguser = await prisma.user.findUnique({
            where: {
                email: email,
            },
        });

        if (existinguser) {
            return NextResponse.json(
                {
                    success: false,
                    message: "User already exists",
                },
                {
                    status: 400,
                }
            );
        }

        const hashedPassword = await bcrypt.hash(password, 10);

        const user = await prisma.user.create({
            data: {
                name,
                email,
                password: hashedPassword,
            },
            select: {
                name: true,
            },
        });

        const returnedUser = {
            success: true,
            message: "User registered successfully",
            data: {
                name: user.name,
            },
        };

        return NextResponse.json(
            returnedUser,
            {
                status: 201,
            }
        );
    } catch (error) {
        console.log("Error at /api/auth/register : ", error);
        return NextResponse.json(
            {
                success: false,
                message: "Error occurred while registering user",
            },
            {
                status: 500,
            }
        );
    }
}
