---
description: Web/application security rules — always apply
---

# Security rules

Extends [CLAUDE.md](../../CLAUDE.md) Security. Apply to all request handling, configuration, and I/O code.

## Trust & input
- Never trust client-supplied fields that affect authority — `role`, `ownerId`, `userId`, `isAdmin`, prices, redirect targets. Derive them server-side from the authenticated principal.
- Bind only expected fields; guard against mass assignment / over-posting.
- Escape/encode all HTML output; never render untrusted input as raw HTML (XSS).
- Parameterized queries only — never concatenate SQL.

## HTTP edge
- **CORS:** allow only explicit, configured origins. Never `*` together with credentials.
- **Security headers:** `Content-Security-Policy`, `X-Content-Type-Options: nosniff`, `X-Frame-Options` / frame-ancestors, `Referrer-Policy`, HSTS.
- **CSRF:** require anti-forgery tokens for state-changing requests when using cookie-based auth.
- **Redirects:** allow only internal / allow-listed targets — no open redirects from user input.

## File uploads
- Reject path traversal (`../`); never build storage paths from client file names.
- Validate MIME/content type and extension against an allow-list; enforce a max size.
- Store outside the web root.

## Secrets, dependencies, errors
- Secrets only via environment/configuration providers — never hard-coded or logged.
- Keep dependencies patched; remediate high/critical advisories promptly.
- Return generic errors to clients; log details server-side with no PII/secrets (via the global error-handling middleware).
