/**
 * Security event logger
 * In production, send these to a logging service (e.g., Datadog, Sentry, CloudWatch)
 */

export enum SecurityEventType {
    LOGIN_SUCCESS = "LOGIN_SUCCESS",
    LOGIN_FAILED = "LOGIN_FAILED",
    LOGIN_RATE_LIMITED = "LOGIN_RATE_LIMITED",
    ACCOUNT_LOCKED = "ACCOUNT_LOCKED",
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS",
    SESSION_CREATED = "SESSION_CREATED",
    SESSION_EXPIRED = "SESSION_EXPIRED",
}

interface SecurityEvent {
    type: SecurityEventType;
    username?: string;
    userId?: string;
    ip?: string;
    userAgent?: string;
    timestamp: string;
    metadata?: Record<string, any>;
}

class SecurityLogger {
    /**
     * Log security events
     * Replace console.log with your logging service in production
     */
    log(event: SecurityEvent): void {
        const logEntry = {
            ...event,
            timestamp: event.timestamp || new Date().toISOString(),
            environment: process.env.NODE_ENV,
        };

        // Development: console logging
        if (process.env.NODE_ENV === "development") {
            console.log("[SECURITY]", JSON.stringify(logEntry, null, 2));
        }

        // Production: Send to logging service
        // Example integrations:
        // - Sentry: Sentry.captureMessage(JSON.stringify(logEntry))
        // - Datadog: logger.info(logEntry)
        // - CloudWatch: cloudwatch.putLogEvents(...)
        // - File: fs.appendFileSync('security.log', JSON.stringify(logEntry))

        if (process.env.NODE_ENV === "production") {
            // TODO: Integrate with your logging service
            console.error("[SECURITY]", JSON.stringify(logEntry));
        }
    }

    logLoginSuccess(username: string, userId: string, ip?: string): void {
        this.log({
            type: SecurityEventType.LOGIN_SUCCESS,
            username,
            userId,
            ip,
            timestamp: new Date().toISOString(),
        });
    }

    logLoginFailed(username: string, reason: string, ip?: string): void {
        this.log({
            type: SecurityEventType.LOGIN_FAILED,
            username,
            ip,
            timestamp: new Date().toISOString(),
            metadata: { reason },
        });
    }

    logRateLimited(identifier: string, ip?: string): void {
        this.log({
            type: SecurityEventType.LOGIN_RATE_LIMITED,
            username: identifier,
            ip,
            timestamp: new Date().toISOString(),
        });
    }

    logAccountLocked(username: string, ip?: string): void {
        this.log({
            type: SecurityEventType.ACCOUNT_LOCKED,
            username,
            ip,
            timestamp: new Date().toISOString(),
        });
    }
}

export const securityLogger = new SecurityLogger();
