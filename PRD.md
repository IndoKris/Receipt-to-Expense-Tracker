# PRD — Receipt-to-Expense Tracker (MVP)

Version 1.0 · Scope source: `features.md` §3 (MVP-1 … MVP-10). Anything not listed here is out of scope until approved per `features.md` §6.

---

## 1. Summary

An iPhone app that turns a photo of a paper receipt or a UPI/payment screenshot into a reviewed, saved expense, and shows simple, trustworthy spending totals. AI (Gemma 4 via the Gemini API) **suggests** values; the user **confirms** them. All totals are computed from saved records.

**Primary users:** students and young professionals in India (INR default) who want minimal manual entry.

**Problem:** tracking everyday spending is tedious; receipts and UPI screenshots pile up unused. Fully manual entry gets abandoned; fully automatic AI entry can't be trusted with money.

**Core promise:** *Scan → check → save.* Never silently wrong.

## 2. Goals and non-goals

### Goals
- G1. Capture an expense from a photo or screenshot in under ~30 seconds including review.
- G2. Make extraction errors easy to spot and fix before saving.
- G3. Show correct, explainable monthly totals, category totals, and budget progress.
- G4. Keep data on the device; keep API secrets off the device; be honest about privacy.

### Non-goals (MVP)
Everything in `features.md` §5: duplicate detection, CSV, share sheet, widgets, custom categories, itemized extraction, multi-currency conversion, cloud sync/accounts, bank integrations, assistants/forecasts/insights beyond totals, biometric lock, Android, web. Also no manual-bulk import, no recurring expenses, no export.

## 3. Product principles (from features.md §8)

1. AI values are suggestions until the user confirms.
2. Unknown stays unknown. Never invent merchant, amount, date, reference, or status.
3. Totals are deterministic code, not LLM output.
4. A screenshot is not proof of payment. Status shown as "Screenshot shows: …" with an "unverified" label.
5. Receipt text is untrusted input.
6. Ask only for permissions needed for the feature in use, at the moment of use.

## 4. User journeys

**J1 — Scan a paper receipt.** Scan tab → Camera or Photos → preview → "Use this photo" → processing → review form pre-filled (uncertain fields highlighted) → user edits → Save → success → expense appears in Transactions and Home.

**J2 — Import a UPI screenshot.** Scan tab → "Payment screenshot" → pick from Photos → preview → processing → review form shows recipient, amount, date, reference, and a status banner ("Screenshot shows: Success — not independently verified") → user confirms or edits → Save.

**J3 — Extraction fails.** Unreadable/blurry/unsupported/offline/server error → clear message → actions: Retry, Choose another image, Enter manually (image stays attached). Nothing is saved automatically.

**J4 — Review history.** Transactions tab → newest first → search merchant → filter by date range and category → open a row → detail with receipt image → Edit or Delete (confirm).

**J5 — Understand spending.** Home shows month total, budget progress, recent expenses. Insights shows category totals for the selected month; tapping a category opens Transactions filtered to it.

**J6 — Set a budget.** Settings (or Home budget card) → set monthly budget and thresholds → Home shows spent / remaining / % used and warnings at thresholds.

**J7 — Remove data.** Delete an expense → confirm → expense and its stored image are removed.

**J8 — Recover unsaved input.** Network failure or app interruption during review does not lose the user's in-progress input (draft resume).

## 5. Functional requirements

IDs map to `features.md`. "Done when" lines are the acceptance tests.

### FR-1 App foundation (MVP-1)
- FR-1.1 Five tabs: Home, Transactions, Scan, Insights, Settings.
- FR-1.2 Layout works on iPhone SE (small) through Pro Max (large); no clipped primary actions.
- FR-1.3 Every data screen has loading, empty, error, and (for actions) success states.
- FR-1.4 Dynamic Type: text scales with system font size (no fixed-height text containers; layouts tolerate up to the largest accessibility size without losing actions).
- FR-1.5 VoiceOver: every button/icon/tab/input has an `accessibilityLabel` (and `accessibilityHint` where the result isn't obvious); touch targets ≥ 44×44 pt; status is never conveyed by color alone.
- **Done when:** app launches and navigates without crash; core screens usable on small and large phones; each primary action gives visible feedback (toast/banner/state change).

### FR-2 Image import (MVP-2)
- FR-2.1 Capture with camera; request camera permission only when the user taps Camera. Denied → explain and offer Photos.
- FR-2.2 Pick from photo library (single image). Accept JPEG, PNG, HEIC/HEIF (converted to JPEG before upload), WebP if the picker returns it.
- FR-2.3 Preview screen with **Use this photo**, **Retake/Choose another**, **Cancel**.
- FR-2.4 Image normalized before upload: EXIF rotation applied, longest side ≤ 1600 px, JPEG ~0.8 quality, target ≤ 2 MB.
- FR-2.5 Unreadable/blurry/unsupported images produce a friendly error with retry options, never a crash or a silent save.
- **Done when:** user can capture or select an image and reach the review screen; failed processing leaves zero new expenses.

### FR-3 AI extraction (MVP-3)
Fields (each may be unknown): merchant, total amount, date, currency, suggested category, payment method (only if shown in the source), tax, discount.
- FR-3.1 Extraction runs on the backend behind a replaceable provider interface (Gemma 4 first).
- FR-3.2 Output validated against a schema; invalid output handled safely (one retry, then error state with manual entry).
- FR-3.3 Missing/uncertain fields are visibly flagged ("Check this") in the review form.
- FR-3.4 Each field is tagged **AI-suggested** until the user edits it, then **Edited**. Manual entries are tagged **Manual**.
- FR-3.5 Embedded instructions in a receipt never alter behavior (see TRD §6.5).
- **Done when:** extracted fields appear in an editable form; malformed/partial output doesn't crash or produce a saved expense; extracted vs edited values are distinguishable.

### FR-4 UPI / payment screenshot import (MVP-4)
- FR-4.1 Import from Photos only. The app never reads other apps' data automatically.
- FR-4.2 Extract amount, recipient/merchant, date, transaction reference, and visible status (success / pending / failed / unknown).
- FR-4.3 Missing/uncertain values flagged.
- FR-4.4 Saving always requires explicit user confirmation on the review screen.
- FR-4.5 Status is stored as "what the screenshot shows" and displayed as such, with an "Unverified" label. Pending/failed/unknown show a prominent warning banner ("This payment may not have completed") and the Save button copy becomes "Save anyway".
- **Done when:** user can import a screenshot, review, correct, save; unclear/failed status is never shown as confirmed success.

### FR-5 Review and save (MVP-5)
- FR-5.1 Review form: merchant (text), amount (decimal), currency (picker), date (date picker), category (picker), payment method (picker, optional), plus read-only extracted tax/discount/reference/status when present (tax/discount/reference editable as optional text/number fields).
- FR-5.2 Validation: merchant non-empty (≤ 80 chars); amount > 0 and ≤ 1,000,000,000; date valid, not in the future beyond tomorrow, not before 2000-01-01; currency from list.
- FR-5.3 **Save** is disabled until valid and while saving (prevents double-tap duplicates).
- FR-5.4 **Cancel** asks "Discard this expense?" if the form has data; cancelling creates no expense and deletes the draft image.
- FR-5.5 Save stores the final confirmed values plus the image reference, then shows a success state and offers "Scan another" / "View".
- FR-5.6 Manual entry path: "Enter manually" opens the same form blank.
- **Done when:** corrections are possible before save; saved values equal the final confirmed values; cancel creates nothing.

### FR-6 History and management (MVP-6)
- FR-6.1 Transactions list: newest first (date desc, then created desc). Row: merchant, date, category, amount (with currency if not base).
- FR-6.2 Detail: all fields, provenance tags, receipt image (tap to enlarge) when present, status label for screenshots.
- FR-6.3 Edit using the review form in edit mode. Changed fields become **Edited**.
- FR-6.4 Delete with confirmation; removes row and image file; list/totals refresh.
- FR-6.5 Search by merchant text (case-insensitive, substring).
- FR-6.6 Filters: date range (from/to, either optional) and category (single). Active filters shown as chips with a Clear action.
- **Done when:** created/edited values are consistent everywhere; deletion is deliberate and UI refreshes; search/filter return expected records.

### FR-7 Categories and dashboard (MVP-7)
- FR-7.1 Default categories: Food, Groceries, Transport, Shopping, Bills, Health, Education, Other.
- FR-7.2 Month selector (prev/next, defaults to current month) shared by Home and Insights.
- FR-7.3 Home: month total, budget card (FR-8), recent 5 expenses, "Resume draft" card if a draft exists.
- FR-7.4 Insights: category totals for the month (amount, % of month total, bar), sorted by amount desc; tapping a category opens Transactions filtered to that category **and** that month.
- FR-7.5 Every totals surface shows: "Totals include only expenses recorded in this app."
- FR-7.6 Totals sum only expenses whose currency equals the **base currency** (default INR). If other-currency expenses exist in the period, show "N expense(s) in other currencies not included". (No conversion in MVP.)
- FR-7.7 Empty states explain how to add the first expense and link to Scan.
- **Done when:** totals come from stored records; update after add/edit/delete; empty states work.

### FR-8 Budget (MVP-8)
- FR-8.1 One monthly budget amount (base currency), applied to every calendar month. Set, change, or remove.
- FR-8.2 Show spent, remaining (or "Over by X"), and % used for the selected month.
- FR-8.3 Warning thresholds configurable, default 80% and 100%. State: OK (<80), "Approaching" (≥80 and <100), "Over budget" (≥100). Banner on Home; not color-only.
- FR-8.4 Text: "Based on expenses recorded in this app."
- FR-8.5 Optional local notifications: off by default; enabling asks for iOS notification permission; if denied, the toggle reverts and explains. Each threshold notifies at most once per month, and only after a save.
- **Done when:** calculations are deterministic and unit-tested; changing/removing the budget updates the dashboard; no notification is sent without permission.

### FR-9 Storage and privacy (MVP-9)
- FR-9.1 Expenses persist in on-device SQLite; images in the app's document directory.
- FR-9.2 No API keys in the app bundle; the app talks only to our backend.
- FR-9.3 No accounts in MVP (single local user) → no cross-user access path exists. If this changes, per-user access control is required first.
- FR-9.4 In-app **Privacy notice** (Settings): what is sent, to whom, what is stored where, how to delete (copy in §7).
- FR-9.5 Network or processing failure never discards in-progress input (draft is kept on-device; Resume available).
- FR-9.6 Deleting an expense deletes its image file.
- **Done when:** data survives restarts; secrets stay on the backend; deletion tested and documented.

### FR-10 Testing and delivery (MVP-10)
Covered by `TRD.md` §10 and `plan.md` M9. Deliverables: automated tests, manual test checklist results, README (setup/config/run), `KNOWN_LIMITATIONS.md`, MVP completion report.

## 6. Screens

| Screen | Purpose | Key states |
|---|---|---|
| Home | month total, budget card, recent, resume-draft | loading, empty, error |
| Transactions | list, search, filters | loading, empty, no-results, error |
| Expense detail | view fields + image, Edit/Delete | loading, not-found, deleting |
| Scan | choose source: Camera / Photos / Payment screenshot / Enter manually | permission-denied |
| Image preview | confirm or change image | — |
| Processing | spinner, Cancel | cancelled, error (typed) |
| Review / Edit form | confirm values | validation errors, saving, saved |
| Insights | category totals + drill-down | loading, empty |
| Settings | budget, thresholds, notifications, base currency, Privacy notice, About/limitations | permission-denied |

Error copy (typed): offline → "You're offline. Your photo is kept — retry when connected or enter manually." · timeout → "That took too long." · unreadable → "We couldn't read this image. Try a clearer, flatter, well-lit photo." · unsupported → "This file type isn't supported." · rate limited → "Too many scans. Wait a minute and try again." · server/model error → "The scanning service had a problem."  Each offers Retry / Choose another / Enter manually as applicable.

## 7. Copy: privacy notice (Settings → Privacy)

> **What happens to your receipts**
> • When you scan or import an image, the app sends it over an encrypted connection to this app's server, which forwards it to Google's Gemini API (running the Gemma 4 model) to read the text. The server does not save your image or the extracted data.
> • Google processes the image under its Gemini API terms. Don't scan documents you wouldn't want processed this way.
> • Your expenses and saved images are stored only on this iPhone. Deleting an expense deletes its image. Deleting the app deletes all data.
> • AI reads can be wrong. Always check amounts and dates before saving. Totals only include expenses you've saved here.
> • The app does not connect to your bank or payment apps.

(Developer note: verify the current Gemini API data-use terms for the tier used and keep this notice accurate.)

## 8. Success criteria

**MVP complete** = every box in `features.md` §4 is true. For the hackathon demo specifically: J1 and J2 run live on a real iPhone, the review screen visibly catches/flags an uncertain field, dashboard totals update immediately, and a deliberately injected "ignore instructions" receipt is shown to be harmless.

## 9. Assumptions and decisions (flag if you disagree)

| # | Decision | Why |
|---|---|---|
| D1 | **Expo / React Native (TypeScript)** instead of native Swift | Developer is on Windows; Xcode needs macOS. Expo runs on a real iPhone via Expo Go; still iOS-first. |
| D2 | Local-first, **no accounts** | Smallest privacy surface; satisfies MVP-9 without per-user backend auth. |
| D3 | Backend is **stateless proxy** (no image/data storage) | Keeps API key off device; nothing to leak. |
| D4 | Date is **required** in MVP (no unknown-date state) | features.md allows this; keeps month totals correct. |
| D5 | Base currency INR; other currencies stored but **excluded from totals** | Avoids silent wrong sums without building multi-currency (D4 in backlog). |
| D6 | Manual entry exists as a fallback | Needed so failed extraction never blocks the user. |
| D7 | Draft resume uses a single on-device draft | Meets "don't lose unsaved input" without extra screens. |
| D8 | No line items in MVP | Itemized extraction is backlog C1. |
