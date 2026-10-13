# Progress Tracker — Receipt-to-Expense Tracker (MVP)

> Auto-updated as development progresses. Source plan: `plan.md`

---

## Overall Status

| Field | Value |
|---|---|
| **Current Phase** | M0 — Repo and tooling |
| **Started** | 2026-10-13 |
| **MVP Status** | 🟡 In Progress |
| **Last Milestone Completed** | None |
| **Known Blockers** | Need GEMINI_API_KEY and GEMMA_MODEL from user |

---

## Milestone Progress

| Milestone | Description | Status | Est. | Notes |
|---|---|---|---|---|
| M0 | Repo + tooling + config | 🟡 In Progress | 0:30 | |
| M1 | Backend extraction service | ⬜ Not Started | 1:15 | |
| M2 | Mobile foundation (MVP-1) | ⬜ Not Started | 0:50 | |
| M3 | Image import + processing | ⬜ Not Started | 0:50 | |
| M4 | Review + save + draft | ⬜ Not Started | 1:00 | |
| M5 | History + management | ⬜ Not Started | 0:50 | |
| M6 | Categories + dashboard | ⬜ Not Started | 0:40 | |
| M7 | Budget | ⬜ Not Started | 0:30 | |
| M8 | Privacy + storage hardening | ⬜ Not Started | 0:20 | |
| M9 | Testing + delivery | ⬜ Not Started | 0:55 | |

---

## Task Checklist

### M0 — Repo and tooling
- [ ] T0.1 Create repo layout, .gitignore, LICENSE, docs
- [ ] T0.2 Backend skeleton with /healthz
- [ ] T0.3 Mobile Expo app with tabs
- [ ] T0.4 Confirm Gemini API key and model

### M1 — Backend extraction
- [ ] T1.1 schemas.py
- [ ] T1.2 images.py + tests
- [ ] T1.3 verifier.py + tests
- [ ] T1.4 prompt.py
- [ ] T1.5 providers (base, fake, gemma)
- [ ] T1.6 main.py /v1/extract + tests
- [ ] T1.7 make_fixtures.py
- [ ] T1.8 Live smoke test

### M2 — Mobile foundation
- [ ] T2.1 Theme + base components
- [ ] T2.2 Tab navigation
- [ ] T2.3 DB + migrations + settings repo
- [ ] T2.4 domain/money.ts + types + tests

### M3 — Image import + processing
- [ ] T3.1 Scan screen
- [ ] T3.2 imageStore.ts pipeline
- [ ] T3.3 preview.tsx
- [ ] T3.4 Extraction service + contract test
- [ ] T3.5 processing.tsx with errors

### M4 — Review, save, draft
- [ ] T4.1 validation.ts + provenance.ts + tests
- [ ] T4.2 expensesRepo.ts + tests
- [ ] T4.3 review.tsx form
- [ ] T4.4 draftRepo.ts + Resume draft
- [ ] T4.5 Save flow + success state

### M5 — History + management
- [ ] T5.1 filters.ts + tests
- [ ] T5.2 Transactions screen
- [ ] T5.3 Expense detail + edit/delete

### M6 — Categories + dashboard
- [ ] T6.1 totals.ts + tests
- [ ] T6.2 AppProvider (month + refresh)
- [ ] T6.3 Home screen
- [ ] T6.4 Insights screen
- [ ] T6.5 Base currency setting

### M7 — Budget
- [ ] T7.1 budget.ts + tests
- [ ] T7.2 Settings: budget + thresholds
- [ ] T7.3 Home budget card
- [ ] T7.4 Notifications service

### M8 — Privacy + storage
- [ ] T8.1 privacy.tsx
- [ ] T8.2 Security audit
- [ ] T8.3 Persistence + deletion verification

### M9 — Testing + delivery
- [ ] T9.1 Live fixture evaluation
- [ ] T9.2 Manual iPhone checklist
- [ ] T9.3 Release-blocking bug fixes
- [ ] T9.4 README + KNOWN_LIMITATIONS
- [ ] T9.5 MVP completion report

---

## Change Log

| Date | Change | Details |
|---|---|---|
| 2026-10-13 | Project started | Created progress.md, beginning M0 |
