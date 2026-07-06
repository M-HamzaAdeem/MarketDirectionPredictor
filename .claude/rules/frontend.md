---
description: Frontend (TypeScript / React / Vue) conventions
pack: frontend
paths:
  - "**/*.ts"
  - "**/*.tsx"
  - "**/*.js"
  - "**/*.jsx"
  - "**/*.vue"
---

# Frontend rules

Auto-applies when editing frontend code. Extends [CLAUDE.md](../../CLAUDE.md). Use the project's framework and tooling (see [project/context.md](../project/context.md)); the `react-developer` / `vue-developer` agents carry deeper, framework-specific guidance.

## Language & naming
- **TypeScript strict** — type props/state/returns; avoid `any`; prefer discriminated unions over boolean flags.
- **camelCase** variables/functions; **PascalCase** components/types; **kebab-case** CSS classes and element ids.

## Components & state
- Small, single-purpose components; extract reusable logic (hooks / composables). One-way data flow — never mutate props.
- State: local first; use the project's store; keep **server state** in a data-fetching lib (React Query / SWR / TanStack Query) rather than hand-rolled effects.
- Derive, don't duplicate, state; correct effect dependencies; clean up subscriptions/timers.

## Quality
- **Accessibility:** semantic HTML, labels, keyboard navigation, focus management — target WCAG AA.
- **Security:** never render untrusted input as raw HTML (`dangerouslySetInnerHTML` / `v-html`); no secrets in client code.
- **Performance:** measure first; code-split; memoize/virtualize **only after a profiler/measurement shows the hotspot** (cite it); stable list keys.
- **Tests:** behavior over implementation with the project's runner (Vitest/Jest + Testing Library); cover interaction and edge/error states.

Applicable gates: [code-review.md](code-review.md).
