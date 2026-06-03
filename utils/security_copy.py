"""
LeadFlow — utils/security_copy.py
Reusable, factual security descriptions for UI pages, email templates,
and anywhere else a human-readable explanation of the auth/security model is needed.

These strings describe the *actual* implementation:
  - Custom session auth with bcrypt password hashing (Flask + PostgreSQL)
  - CSRF protection on all state-changing requests
  - Rate limiting on authentication endpoints
  - Secure, HttpOnly, SameSite=Strict session cookies in production
  - Time-limited, single-use, hashed password reset tokens
"""

AUTH_SYSTEM = (
    "LeadFlow uses a secure session-based authentication system. "
    "Passwords are hashed with bcrypt (cost factor 13) — your plain-text password "
    "is never stored. Sessions are managed via HttpOnly, SameSite=Strict cookies "
    "and automatically expire after 7 days of inactivity."
)

PASSWORD_POLICY = (
    "Passwords must be at least 10 characters and include an uppercase letter, "
    "a lowercase letter, a number, and a special character. "
    "This is enforced on both the client and server."
)

PASSWORD_RESET = (
    "Password resets use a secure, single-use token emailed to your registered address. "
    "The token is valid for 1 hour, stored as a SHA-256 hash (never in plain text), "
    "and invalidated immediately after use. Requesting a reset does not expose whether "
    "an email address is registered."
)

SESSION_HANDLING = (
    "Your session is stored in an encrypted, HttpOnly cookie. "
    "It cannot be read by JavaScript and is bound to the originating domain "
    "(SameSite=Strict). Sessions are cleared on sign-out and cannot be shared "
    "across browsers or devices."
)

CSRF_PROTECTION = (
    "All state-changing requests (create, update, delete, sign-in, sign-out) "
    "require a CSRF token to prevent cross-site request forgery attacks. "
    "The token is regenerated on each session and validated server-side."
)

DATA_SECURITY = (
    "Lead data is stored in a PostgreSQL database with row-level access control — "
    "each user can only access their own records. "
    "The database connection uses TLS in production."
)

GENERAL = (
    "LeadFlow enforces HTTPS in production, sets strict security headers "
    "(Content-Security-Policy, X-Frame-Options, Referrer-Policy, Permissions-Policy), "
    "and rate-limits authentication and sensitive API endpoints to limit abuse."
)
