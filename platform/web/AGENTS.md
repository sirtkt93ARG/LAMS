# Frontend engineering instructions

## Required reference
Follow [GoogleChrome/modern-web-guidance](https://github.com/GoogleChrome/modern-web-guidance) for all frontend work. Consult its `skills/modern-web-guidance/SKILL.md` before implementation. Reference snapshot initially adopted: commit `64a6d708f5a43f2cd3fde5d4d7db3905ba1bdf65`; check upstream for updates.

## Required workflow for UI/browser work
1. Before changing HTML, CSS, browser APIs, accessibility, forms, responsive layouts, performance, security, or client-side JS, search the guidance for each distinct capability using a focused 2–5 word action-oriented query.
2. Retrieve the matching guide(s), plus applicable discipline guides (accessibility, forms, CSS, performance, security). Do not invent guide IDs or rely on remembered rules.
3. Adapt vanilla platform guidance to this Next.js 14 / React 18 application. Check browser support and use the guide's graceful fallbacks for features that are not Baseline Widely Available. Do not add experimental APIs just for novelty.
4. Implement semantic HTML first. Prefer native controls and platform behavior over custom JS when that improves usability and compatibility.
5. Verify keyboard operation, visible focus, accessible names/descriptions, labels, error announcements, contrast, reduced motion, text zoom/reflow, and mobile layouts where relevant.
6. Add or update tests for behavior and accessibility-critical logic. Run `npm run typecheck`, `npm run test:lib`, and `npm run build` in `platform/web`.
7. For broad frontend modernization audits, run `npx -y modern-web-guidance@latest legacy-scan platform/web --json`, review each finding against its keep/drop criteria, and distinguish verified issues from false positives. The scan covers only a subset of the guidance corpus; it is not a complete accessibility or quality audit.

## LAMS-specific frontend constraints
- Preserve the Spanish (Argentina) experience and plain-language educational vocabulary.
- Keep student views free of answer keys, internal item tags, calibration parameters, and other assessment-authoring data.
- Never expose individual student identities or records in teacher/network dashboards; use only authorized aggregates and preserve minimum-cell suppression.
- Treat school network membership as opt-in: pending invitations must not contribute data to network aggregates.
- Keep role checks enforced by the API. Client-side route hiding is usability only, never authorization.
- Keep forms labeled, keyboard-operable, and explicit about validation and submission outcomes. Use real `form`, `label`, `button`, `select`, and `fieldset/legend` semantics where appropriate.
- Keep data tables semantic and usable at narrow widths; provide an accessible name and keyboard access for any scrollable table region.
- Use logical CSS properties and responsive/container-driven layouts where supported; avoid fixed-width assumptions.
- Respect `prefers-reduced-motion`, user text scaling, and visible `:focus-visible` states.
- Avoid loading non-critical media or code eagerly. Do not lazy-load above-the-fold LCP content.

## Current stack
Next.js 14, React 18, TypeScript 5, native CSS, and the existing small dependency set. Do not introduce a UI framework or a large component library without a concrete, documented need.
