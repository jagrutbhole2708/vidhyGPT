interface RateLimitEntry {
    count: number;
    resetTime: number;
}

class RateLimiter {
    private requests: Map<string, RateLimitEntry> = new Map();
    private readonly maxAttempts: number;
    private readonly windowMs: number;

    constructor(maxAttempts: number = 5, windowMinutes: number = 15) {
        this.maxAttempts = maxAttempts;
        this.windowMs = windowMinutes * 60 * 1000;

        setInterval(() => this.cleanup(), 5 * 60 * 1000);
    }

    check(identifier: string): {
        allowed: boolean;
        remaining: number;
        resetTime: number;
    } {
        const now = Date.now();
        const entry = this.requests.get(identifier);

        // No previous attempts or window expired
        if (!entry || now > entry.resetTime) {
            this.requests.set(identifier, {
                count: 1,
                resetTime: now + this.windowMs,
            });
            return {
                allowed: true,
                remaining: this.maxAttempts - 1,
                resetTime: now + this.windowMs,
            };
        }

        // Increment attempt count
        entry.count++;

        return {
            allowed: entry.count <= this.maxAttempts,
            remaining: Math.max(0, this.maxAttempts - entry.count),
            resetTime: entry.resetTime,
        };
    }

    /**
     * Reset rate limit for an identifier (use after successful login)
     */
    reset(identifier: string): void {
        this.requests.delete(identifier);
    }

    /**
     * Clean up expired entries
     */
    private cleanup(): void {
        const now = Date.now();
        for (const [key, entry] of this.requests.entries()) {
            if (now > entry.resetTime) {
                this.requests.delete(key);
            }
        }
    }
}

// Singleton instance: 5 attempts per 15 minutes
export const loginRateLimiter = new RateLimiter(5, 15);
