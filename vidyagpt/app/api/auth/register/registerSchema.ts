import { z } from "zod";

export const registerSchemaRequest = z.object({
    name: z.string().min(1, "Name is required"),
    email: z
        .string()
        .regex(
            /^[a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*@(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$/,
            "Invalid email address"
        ),
    password: z.string().min(6, "Password must be at least 6 characters long"),
});