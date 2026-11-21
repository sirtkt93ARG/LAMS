# Repository working agreements

## Project scope
LAMS is an educational assessment and learning platform. Preserve its separation between the assessment engine, API, identity/LTI integration, persistence, and web client. Treat student data, school boundaries, consent, item security, and assessment validity as high-risk concerns.

## General engineering rules
- Inspect the existing implementation, tests, migrations, and deployment assumptions before changing behavior.
- Prefer small, reviewable changes with regression tests. Do not claim a feature is complete until relevant CI checks pass.
- Preserve tenant isolation, pseudonymization, consent requirements, and least-privilege authorization. Never weaken these to make a workflow easier.
- Database changes must include a forward migration for existing installations and tests for fresh and upgraded databases where practical.
- Do not put secrets, real student identifiers, or production data in source control, logs, fixtures, or screenshots.
- Keep documentation and examples aligned with the actual implementation. Mark unverified production assumptions explicitly.
- Avoid introducing dependencies unless they solve a demonstrated need.

## Frontend standard: Google Chrome Modern Web Guidance
The frontend must follow [GoogleChrome/modern-web-guidance](https://github.com/GoogleChrome/modern-web-guidance). Its agent instructions are in `platform/web/AGENTS.md`. For every HTML, CSS, browser API, accessibility, responsive UI, forms, or client-side JavaScript task, consult the relevant current guidance before implementation and verify the result against it.

Reference snapshot consulted for this project: `GoogleChrome/modern-web-guidance` commit `64a6d708f5a43f2cd3fde5d4d7db3905ba1bdf65`. Prefer the current upstream guidance when working; do not blindly copy experimental examples or remove compatibility fallbacks.
